# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta, time as dtime
from typing import Optional, Tuple, Dict

from odoo import api, fields, models, _
from odoo.exceptions import UserError


# =========================
# Keywords thiết bị (giữ nguyên, thêm vài biến thể)
# =========================
_DEVICE_KEYWORDS = [
    (r"\b(máy\s*chiếu|may\s*chieu|projector)\b", "may_chieu"),
    (r"\b(mic|micro|microphone)\b", "micro"),
    (r"\b(loa|speaker|am\s*ly|âm\s*ly)\b", "loa"),
    (r"\b(điều\s*hòa|dieu\s*hoa|air\s*con|aircon)\b", "dieu_hoa"),
    (r"\b(máy\s*tính|may\s*tinh|laptop|notebook|pc)\b", "may_tinh"),
    (r"\b(tivi|tv|television)\b", "khac"),
]

# =========================
# Helpers normalize
# =========================
_VI_NUM = {
    "một": 1, "mot": 1,
    "hai": 2,
    "ba": 3,
    "bốn": 4, "bon": 4,
    "năm": 5, "nam": 5,
    "sáu": 6, "sau": 6,
    "bảy": 7, "bay": 7,
    "tám": 8, "tam": 8,
    "chín": 9, "chin": 9,
    "mười": 10, "muoi": 10,
    "mười một": 11, "muoi mot": 11,
    "mười hai": 12, "muoi hai": 12,
    "mười lăm": 15, "muoi lam": 15,
    "hai mươi": 20, "hai muoi": 20,
}

_TIME_OF_DAY_HINTS = {
    "sáng": "morning",
    "sang": "morning",
    "trưa": "noon",
    "trua": "noon",
    "chiều": "afternoon",
    "chieu": "afternoon",
    "tối": "evening",
    "toi": "evening",
    "đêm": "night",
    "dem": "night",
}

# phục vụ parse số lượng bằng chữ trước keyword thiết bị
_VI_NUM_KEYS_SORTED = sorted(_VI_NUM.keys(), key=lambda x: len(x), reverse=True)
_VI_NUM_ALT = "|".join([re.escape(k) for k in _VI_NUM_KEYS_SORTED])


def _normalize_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("–", "-").replace("→", "-").replace("->", "-")
    s = re.sub(r"[,\.;]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


# =========================
# Parse attendees: số + "người/nguoi"
# - hỗ trợ "10 người", "khoảng 10 người", "10nguoi", "mười người"
# =========================
def _parse_attendees(text: str) -> int:
    # 10 người / khoảng 10 người / tầm 10 người / 10nguoi
    m = re.search(r"\b(?:khoảng|khoang|tầm|tam)?\s*(\d{1,3})\s*(người|nguoi)\b", text)
    if m:
        return int(m.group(1))

    # "mười người", "muoi nguoi"... (cho phép các chữ + khoảng trắng)
    m = re.search(
        r"\b([a-zàáạảãâầấậẩẫăằắặẳẵđèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹ\s]+)\s*(người|nguoi)\b",
        text
    )
    if m:
        phrase = re.sub(r"\s+", " ", m.group(1).strip())
        return _VI_NUM.get(phrase, 0)

    return 0


# =========================
# Date parsing nâng cao
# - hôm nay/mai/ngày kia
# - dd/mm(/yyyy), dd-mm(/yyyy)
# - "ngày 3 tháng 2", "mùng 3"
# - "thứ 2", ... "cn"
# =========================
def _parse_date(text: str):
    today = fields.Date.today()

    if re.search(r"\b(hôm\s*nay|hom\s*nay)\b", text):
        return today
    if re.search(r"\b(ngày\s*mai|mai)\b", text):
        return today + timedelta(days=1)
    if re.search(r"\b(ngày\s*kia|kia)\b", text):
        return today + timedelta(days=2)

    # dd/mm(/yyyy) or dd-mm(/yyyy)
    m = re.search(r"\b(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{4}))?\b", text)
    if m:
        d = int(m.group(1))
        mo = int(m.group(2))
        y = int(m.group(3)) if m.group(3) else datetime.now().year
        try:
            return datetime(y, mo, d).date()
        except Exception:
            pass

    # "ngày 3 tháng 2" / "ngay 3 thang 2"
    m = re.search(r"\b(ngày|ngay)\s*(\d{1,2})\s*(tháng|thang)\s*(\d{1,2})(?:\s*(năm|nam)\s*(\d{4}))?\b", text)
    if m:
        d = int(m.group(2))
        mo = int(m.group(4))
        y = int(m.group(6)) if m.group(6) else datetime.now().year
        try:
            return datetime(y, mo, d).date()
        except Exception:
            pass

    # "mùng 3" / "mung 3" => hiểu là ngày 3 tháng hiện tại
    m = re.search(r"\b(mùng|mung)\s*(\d{1,2})\b", text)
    if m:
        d = int(m.group(2))
        now = datetime.now()
        try:
            return datetime(now.year, now.month, d).date()
        except Exception:
            pass

    # "thứ 2/3/4/5/6/7" hoặc "cn"
    m = re.search(r"\b(thứ|thu)\s*([2-7])\b|\b(cn|chủ\s*nhật|chu\s*nhat)\b", text)
    if m:
        # python weekday: Mon=0..Sun=6
        if m.group(3):  # CN
            target = 6
        else:
            target = int(m.group(2)) - 2  # thứ 2 => 0
        delta = (target - today.weekday()) % 7
        # Nếu người dùng nói "thứ X" mà hôm nay đúng thứ X, thường họ muốn tuần tới => +7
        if delta == 0:
            delta = 7
        return today + timedelta(days=delta)

    return None


def _detect_time_of_day_hint(text: str) -> Optional[str]:
    for k, v in _TIME_OF_DAY_HINTS.items():
        if re.search(rf"\b{k}\b", text):
            return v
    return None


# =========================
# Parse 1 mốc thời gian an toàn hơn:
# - "9h", "9:30", "9h30", "9 rưỡi", "3 chiều", "chiều 3"
# return (hour, minute, hint)
# =========================
def _parse_single_time(text: str) -> Optional[Tuple[int, int, Optional[str]]]:
    hint = _detect_time_of_day_hint(text)

    # 1) "9 rưỡi"
    m = re.search(r"\b(\d{1,2})\s*(rưỡi|ruoi)\b", text)
    if m:
        h = int(m.group(1))
        return h, 30, hint

    # 2) "3 chiều" / "chiều 3" (cho phép không có h/:/giờ)
    #    Chỉ kích hoạt khi có hint từ thời điểm trong câu
    if hint:
        m = re.search(r"\b(\d{1,2})\s*(?:giờ|gio)?\s*(sáng|sang|trưa|trua|chiều|chieu|tối|toi|đêm|dem)\b", text)
        if m:
            h = int(m.group(1))
            return h, 0, hint
        m = re.search(r"\b(sáng|sang|trưa|trua|chiều|chieu|tối|toi|đêm|dem)\s*(\d{1,2})\b", text)
        if m:
            h = int(m.group(2))
            return h, 0, hint

    # 3) "09:30"
    m = re.search(r"\b(\d{1,2})\s*:\s*(\d{1,2})\b", text)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return h, mi, hint

    # 4) "9h30" / "9h" / "9h 30"
    m = re.search(r"\b(\d{1,2})\s*h\s*(\d{1,2})?\b", text)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2)) if m.group(2) else 0
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return h, mi, hint

    # 5) "9 giờ" / "9 gio"
    m = re.search(r"\b(\d{1,2})\s*(giờ|gio)\b", text)
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23:
            return h, 0, hint

    return None


def _apply_time_of_day_hint(h: int, hint: Optional[str]) -> int:
    """
    Nếu user viết "3 chiều" => 15:00, "8 tối" => 20:00.
    Quy ước:
    - morning: giữ nguyên (0-11)
    - noon: nếu h=12 giữ; nếu h in 1..11 => +12
    - afternoon/evening/night: nếu h in 1..11 => +12
    """
    if hint is None:
        return h
    if hint == "noon":
        if h == 12:
            return 12
        if 1 <= h <= 11:
            return h + 12
        return h
    if hint in ("afternoon", "evening", "night"):
        if 1 <= h <= 11:
            return h + 12
        return h
    return h  # morning


# =========================
# Parse time range nâng cao (an toàn hơn)
# - "9h-11h", "9h30-11h", "09:00-11:00"
# - "từ 9 đến 11", "9 đến 11", "9h đến 11h"
# - chỉ 1 mốc "9h" => default duration
# =========================
def _parse_time_range(text: str, default_duration_minutes: int = 60):
    text = _normalize_text(text)
    hint = _detect_time_of_day_hint(text)

    # Helper: validate & build time
    def _mk(h: int, mi: int) -> dtime:
        return dtime(hour=h, minute=mi)

    # 1) range với "-" (chỉ nhận nếu match string có dấu hiệu thời gian: ':' hoặc 'h' hoặc 'giờ/gio')
    m = re.search(
        r"\b(\d{1,2})(?:\s*[:h]\s*(\d{1,2}))?\s*(?:giờ|gio)?\s*-\s*(\d{1,2})(?:\s*[:h]\s*(\d{1,2}))?\s*(?:giờ|gio)?\b",
        text
    )
    if m:
        matched = m.group(0)
        if re.search(r"[:h]|giờ|gio", matched):
            h1 = int(m.group(1))
            mi1 = int(m.group(2)) if m.group(2) else 0
            h2 = int(m.group(3))
            mi2 = int(m.group(4)) if m.group(4) else 0
            if 0 <= h1 <= 23 and 0 <= h2 <= 23 and 0 <= mi1 <= 59 and 0 <= mi2 <= 59:
                h1 = _apply_time_of_day_hint(h1, hint)
                h2 = _apply_time_of_day_hint(h2, hint)
                return _mk(h1, mi1), _mk(h2, mi2)

    # 2) range với "đến/den/to" (từ ... đến ...)
    m = re.search(
        r"\b(?:từ|tu)?\s*(\d{1,2})(?:\s*[:h]\s*(\d{1,2}))?\s*(?:giờ|gio)?\s*(?:đến|den|to)\s*(\d{1,2})(?:\s*[:h]\s*(\d{1,2}))?\s*(?:giờ|gio)?\b",
        text
    )
    if m:
        matched = m.group(0)
        # chỉ nhận nếu trong chuỗi match có dấu hiệu thời gian, hoặc có "từ/đến" + hint (giảm bắt nhầm ngày)
        if re.search(r"[:h]|giờ|gio", matched) or (hint is not None and re.search(r"\b(đến|den|to)\b", matched)):
            h1 = int(m.group(1))
            mi1 = int(m.group(2)) if m.group(2) else 0
            h2 = int(m.group(3))
            mi2 = int(m.group(4)) if m.group(4) else 0
            if 0 <= h1 <= 23 and 0 <= h2 <= 23 and 0 <= mi1 <= 59 and 0 <= mi2 <= 59:
                h1 = _apply_time_of_day_hint(h1, hint)
                h2 = _apply_time_of_day_hint(h2, hint)
                return _mk(h1, mi1), _mk(h2, mi2)

    # 3) single time
    single = _parse_single_time(text)
    if single:
        h, mi, hint2 = single
        h = _apply_time_of_day_hint(h, hint2)
        if not (0 <= h <= 23 and 0 <= mi <= 59):
            return None, None

        t_from = _mk(h, mi)

        dt0 = datetime(2000, 1, 1, h, mi)
        dt1 = dt0 + timedelta(minutes=default_duration_minutes)
        t_to = _mk(dt1.hour, dt1.minute)
        return t_from, t_to

    return None, None


def _parse_device_qty(text: str) -> Dict[str, int]:
    """
    Hỗ trợ:
    - "2 mic", "3 loa", "1 máy chiếu"
    - "hai mic", "mười mic" (tối giản theo _VI_NUM)
    - Nếu chỉ nói "mic" => 1
    Trả về dict {loai_thiet_bi: qty}
    """
    result: Dict[str, int] = {}
    for pat, code in _DEVICE_KEYWORDS:
        if re.search(pat, text):
            qty = 1

            # 1) số dạng digit: "2 mic", "2 cái mic", "2 con mic"
            m = re.search(r"\b(\d{1,2})\s*(?:cái|con)?\s*" + pat, text)
            if m:
                qty = int(m.group(1))
            else:
                # 2) số dạng chữ: "hai mic", "mười mic"
                m2 = re.search(r"\b(" + _VI_NUM_ALT + r")\s*(?:cái|con)?\s*" + pat, text)
                if m2:
                    phrase = re.sub(r"\s+", " ", m2.group(1).strip())
                    qty = _VI_NUM.get(phrase, 1)

            result[code] = max(qty, result.get(code, 0))
    return result


class PhongHopAIWizard(models.TransientModel):
    _name = "phong_hop.ai_wizard"
    _description = "Trợ lý AI đặt phòng"

    nguoi_muon_id = fields.Many2one("nhan_vien", string="Người mượn", required=True)
    request_text = fields.Text(string="Yêu cầu (ngôn ngữ tự nhiên)", required=True)

    ngay = fields.Date(string="Ngày", readonly=True)
    thoi_gian_muon_du_kien = fields.Datetime(string="Từ", readonly=True)
    thoi_gian_tra_du_kien = fields.Datetime(string="Đến", readonly=True)

    so_nguoi = fields.Integer(string="Số người", readonly=True)

    # yêu cầu thiết bị
    yeu_cau_loai_thiet_bi = fields.Char(string="Thiết bị yêu cầu (loại)", readonly=True)
    yeu_cau_so_luong_tb = fields.Char(string="Số lượng thiết bị yêu cầu", readonly=True)

    phong_goi_y_ids = fields.Many2many(
        "quan_ly_phong_hop",
        "phong_hop_ai_wizard_room_rel",
        "wizard_id", "phong_id",
        string="Phòng gợi ý",
        readonly=True,
    )
    phong_de_xuat_id = fields.Many2one("quan_ly_phong_hop", string="Phòng được chọn", readonly=True)

    thiet_bi_goi_y_ids = fields.Many2many(
        "thiet_bi",
        "phong_hop_ai_wizard_tb_rel",
        "wizard_id", "thiet_bi_id",
        string="Thiết bị cần mượn từ kho",
        readonly=True,
    )

    tom_tat_goi_y = fields.Text(string="Tóm tắt gợi ý", readonly=True)
    goi_y_slot = fields.Text(string="Gợi ý khung giờ", readonly=True)

    # config
    max_lech_phut = fields.Integer(string="Tối đa lệch (phút)", default=120)

    # NEW: gợi ý toàn bộ thời gian trong ngày (theo step)
    gio_quan_sat_tu = fields.Integer(string="Giờ quét từ", default=0)     # 0..23
    gio_quan_sat_den = fields.Integer(string="Giờ quét đến", default=23)  # 0..23
    buoc_phut = fields.Integer(string="Bước (phút)", default=30)

    # ========
    # INTERNAL
    # ========
    def _extract_requirements(self):
        self.ensure_one()
        text = _normalize_text(self.request_text)

        so_nguoi = _parse_attendees(text)
        ngay = _parse_date(text) or fields.Date.today()

        t_from, t_to = _parse_time_range(text)
        if not t_from or not t_to:
            # Không tự ý fallback 8-9 gây đặt nhầm: báo lỗi rõ ràng
            raise UserError(_("Không nhận diện được thời gian. Ví dụ hợp lệ: '9h-11h', 'từ 9 đến 11', '3 chiều', '09:30-11:00'."))

        dt_from = datetime.combine(ngay, t_from)
        dt_to = datetime.combine(ngay, t_to)

        # hỗ trợ qua ngày nếu end < start (vd 23h-1h hoặc single default duration qua 00:xx)
        if dt_to < dt_from:
            dt_to += timedelta(days=1)

        if dt_from >= dt_to:
            raise UserError(_("Khoảng thời gian không hợp lệ (Từ < Đến)."))

        req_qty_map = _parse_device_qty(text)
        loai_tb = list(req_qty_map.keys())

        self.ngay = ngay
        self.so_nguoi = so_nguoi or 0
        self.yeu_cau_loai_thiet_bi = ",".join(loai_tb) if loai_tb else ""
        self.yeu_cau_so_luong_tb = ", ".join([f"{k}:{v}" for k, v in req_qty_map.items()]) if req_qty_map else ""
        self.thoi_gian_muon_du_kien = fields.Datetime.to_string(dt_from)
        self.thoi_gian_tra_du_kien = fields.Datetime.to_string(dt_to)

        return req_qty_map

    def _busy_room_ids(self, dt_from_str, dt_to_str):
        DatPhong = self.env["dat_phong"].sudo()
        conflict = DatPhong.search([
            ("trang_thai", "in", ["đã_duyệt", "đang_sử_dụng"]),
            ("thoi_gian_muon_du_kien", "<", dt_to_str),
            ("thoi_gian_tra_du_kien", ">", dt_from_str),
            ("phong_id", "!=", False),
        ])
        return set(conflict.mapped("phong_id").ids)

    def _room_builtin_qty(self, room):
        """
        Thiết bị BUILT-IN trong phòng = thiet_bi_ids đang 'Trong phòng'
        Lưu ý: các thiết bị này KHÔNG được đưa vào dat_phong.thiet_bi_ids
        """
        have = {}
        for tb in room.thiet_bi_ids:
            if tb.vi_tri_hien_tai != "phong":
                continue
            have[tb.loai_thiet_bi] = have.get(tb.loai_thiet_bi, 0) + 1
        return have

    def _room_missing_map(self, room, req_qty_map):
        have = self._room_builtin_qty(room)
        missing_map = {k: max(0, need - have.get(k, 0)) for k, need in req_qty_map.items()}
        return {k: v for k, v in missing_map.items() if v > 0}

    def _room_missing_cnt(self, room, req_qty_map):
        mm = self._room_missing_map(room, req_qty_map)
        return sum(mm.values())

    def _room_score(self, room, so_nguoi, req_qty_map):
        # score thấp hơn = tốt hơn
        waste = (room.suc_chua - so_nguoi) if so_nguoi else 0
        missing_cnt = self._room_missing_cnt(room, req_qty_map)
        # thiếu thiết bị nặng nhất
        return (missing_cnt * 100) + max(waste, 0)

    def _search_free_rooms_ranked(self, dt_from_str, dt_to_str, so_nguoi, req_qty_map):
        Phong = self.env["quan_ly_phong_hop"].sudo()

        busy_ids = self._busy_room_ids(dt_from_str, dt_to_str)
        domain = [("active", "=", True), ("id", "not in", list(busy_ids))]

        if so_nguoi:
            domain.append(("suc_chua", ">=", so_nguoi))

        rooms = Phong.search(domain, limit=200)
        if rooms:
            rooms = rooms.sorted(lambda r: (self._room_score(r, so_nguoi, req_qty_map), r.suc_chua, r.id))
        return rooms

    def _suggest_devices_from_kho(self, dt_from_str, dt_to_str, req_qty_map, chosen_room):
        """
        Chỉ lấy thiết bị ở KHO và SẴN SÀNG.
        Số lượng = phần thiếu so với built-in trong phòng.
        """
        ThietBi = self.env["thiet_bi"].sudo()
        DatPhong = self.env["dat_phong"].sudo()

        if not req_qty_map:
            return ThietBi.browse([]), {}, {}

        missing_map = self._room_missing_map(chosen_room, req_qty_map) if chosen_room else dict(req_qty_map)
        if not missing_map:
            return ThietBi.browse([]), {}, {}

        candidates = ThietBi.search([
            ("vi_tri_hien_tai", "=", "kho"),
            ("trang_thai", "=", "san_sang"),
            ("loai_thiet_bi", "in", list(missing_map.keys())),
        ], limit=800)

        if not candidates:
            # không có ứng viên nào trong kho
            return ThietBi.browse([]), missing_map, {k: 0 for k in missing_map.keys()}

        busy_bookings = DatPhong.search([
            ("trang_thai", "in", ["chờ_duyệt", "đã_duyệt", "đang_sử_dụng"]),
            ("thoi_gian_muon_du_kien", "<", dt_to_str),
            ("thoi_gian_tra_du_kien", ">", dt_from_str),
            ("thiet_bi_ids", "in", candidates.ids),
        ])
        busy_ids = set(busy_bookings.mapped("thiet_bi_ids").ids)
        free_tb = candidates.filtered(lambda tb: tb.id not in busy_ids)

        result = ThietBi.browse([])
        got_map = {k: 0 for k in missing_map.keys()}

        for k, need in missing_map.items():
            take = free_tb.filtered(lambda x: x.loai_thiet_bi == k)[:need]
            result |= take
            got_map[k] = len(take)

        return result, missing_map, got_map

    # ===== NEW: gợi ý toàn bộ khung giờ trong ngày =====
    def _suggest_all_day_slots(self, date_, duration_minutes, so_nguoi, req_qty_map):
        """
        Quét toàn bộ ngày theo bước buoc_phut.
        Chỉ trả về các slot có ít nhất 1 phòng rảnh.
        Sort ưu tiên: score tăng dần, rồi start time tăng dần.
        """
        step = max(5, int(self.buoc_phut or 30))
        start_h = min(23, max(0, int(self.gio_quan_sat_tu or 0)))
        end_h = min(23, max(0, int(self.gio_quan_sat_den or 23)))

        # đảm bảo end >= start
        if end_h < start_h:
            start_h, end_h = end_h, start_h

        day_start = datetime.combine(date_, dtime(start_h, 0))
        # kết thúc tại (end_h:59) để không bỏ lỡ các slot cuối ngày
        day_end = datetime.combine(date_, dtime(end_h, 59))

        slots = []
        cursor = day_start

        while cursor <= day_end:
            cand_from = cursor
            cand_to = cand_from + timedelta(minutes=duration_minutes)

            cand_from_str = fields.Datetime.to_string(cand_from)
            cand_to_str = fields.Datetime.to_string(cand_to)

            rooms = self._search_free_rooms_ranked(cand_from_str, cand_to_str, so_nguoi, req_qty_map)
            if rooms:
                best_room = rooms[0]
                score = self._room_score(best_room, so_nguoi, req_qty_map)
                slots.append((score, cand_from_str, cand_to_str, rooms))
            cursor += timedelta(minutes=step)

        slots.sort(key=lambda x: (x[0], x[1]))
        return slots

    # =========
    # ACTIONS
    # =========
    def action_goi_y(self):
        self.ensure_one()
        req_qty_map = self._extract_requirements()

        dt_from_str = self.thoi_gian_muon_du_kien
        dt_to_str = self.thoi_gian_tra_du_kien

        free_rooms = self._search_free_rooms_ranked(dt_from_str, dt_to_str, self.so_nguoi, req_qty_map)

        # chọn phòng đề xuất trong đúng giờ (nếu có)
        chosen_room = free_rooms[0] if free_rooms else False

        # set phòng gợi ý + phòng đề xuất
        self.phong_goi_y_ids = [(6, 0, free_rooms[:5].ids)] if free_rooms else [(6, 0, [])]
        self.phong_de_xuat_id = chosen_room.id if chosen_room else False

        # gợi ý thiết bị mượn kho theo phòng đề xuất
        tb_goi_y, missing_map, got_map = self._suggest_devices_from_kho(dt_from_str, dt_to_str, req_qty_map, chosen_room)
        self.thiet_bi_goi_y_ids = [(6, 0, tb_goi_y.ids)] if tb_goi_y else [(6, 0, [])]

        # ===== GỢI Ý TOÀN BỘ THỜI GIAN TRONG NGÀY =====
        base_from = fields.Datetime.from_string(dt_from_str)
        base_to = fields.Datetime.from_string(dt_to_str)
        duration_minutes = int((base_to - base_from).total_seconds() // 60)
        if duration_minutes <= 0:
            raise UserError(_("Khoảng thời lượng không hợp lệ."))

        all_slots = self._suggest_all_day_slots(self.ngay, duration_minutes, self.so_nguoi, req_qty_map)

        slot_lines = []
        if all_slots:
            slot_lines.append(
                f"Tổng số khung giờ có phòng rảnh (bước {int(self.buoc_phut or 30)} phút): {len(all_slots)}"
            )
            slot_lines.append(f"Khung giờ bạn yêu cầu: {dt_from_str} → {dt_to_str}")
            slot_lines.append("Danh sách khung giờ rảnh (ưu tiên theo score):")

            for (score, a, b, rooms) in all_slots:
                top = rooms[:3]
                room_names = ", ".join([f"{r.name}(sc:{r.suc_chua})" for r in top])
                mark = " [YÊU CẦU]" if (a == dt_from_str and b == dt_to_str) else ""
                slot_lines.append(f"- {a} → {b}{mark}: {room_names} | score={score}")
        else:
            slot_lines.append("Không tìm thấy khung giờ nào có phòng rảnh trong khoảng quét của ngày.")

        self.goi_y_slot = "\n".join(slot_lines)

        # ===== tóm tắt “xịn” =====
        lines = []
        if self.so_nguoi:
            lines.append(f"- Số người: {self.so_nguoi}")
        lines.append(f"- Thời gian: {dt_from_str} → {dt_to_str}")
        if req_qty_map:
            lines.append("- Thiết bị yêu cầu: " + ", ".join([f"{k} x{v}" for k, v in req_qty_map.items()]))

        if chosen_room:
            lines.append(f"- Phòng đề xuất: {chosen_room.name} (sức chứa {chosen_room.suc_chua})")

            miss_map_room = self._room_missing_map(chosen_room, req_qty_map) if req_qty_map else {}
            if not miss_map_room:
                lines.append("- Thiết bị trong phòng: đã đáp ứng đủ (không cần mượn kho).")
            else:
                # nêu thiếu & mức đáp ứng từ kho
                need_parts = []
                shortage_parts = []
                for k, need in miss_map_room.items():
                    got = got_map.get(k, 0)
                    need_parts.append(f"{k} x{need}")
                    if got < need:
                        shortage_parts.append(f"{k} thiếu {need - got}")

                lines.append("- Thiết bị trong phòng: còn thiếu, cần mượn kho: " + ", ".join(need_parts))
                if shortage_parts:
                    lines.append("- Lưu ý: kho không đủ thiết bị rảnh: " + ", ".join(shortage_parts))
        else:
            lines.append("- Không có phòng phù hợp đúng khung giờ này.")
            if req_qty_map:
                lines.append("- Bạn có thể xem phần 'Gợi ý khung giờ' để chọn khung giờ khác trong ngày.")

        self.tom_tat_goi_y = "\n".join(lines)

        return {
            "type": "ir.actions.act_window",
            "res_model": "phong_hop.ai_wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_tao_dang_ky(self):
        self.ensure_one()

        if not self.nguoi_muon_id:
            raise UserError(_("Bạn chưa chọn Người mượn."))

        if not self.thoi_gian_muon_du_kien or not self.thoi_gian_tra_du_kien:
            raise UserError(_("Bạn cần bấm 'Gợi ý' trước."))

        phong = self.phong_de_xuat_id or self.phong_goi_y_ids[:1]
        if not phong:
            raise UserError(_("Không có phòng gợi ý để tạo đăng ký."))

        vals = {
            "phong_id": phong.id,
            "nguoi_muon_id": self.nguoi_muon_id.id,
            "thoi_gian_muon_du_kien": self.thoi_gian_muon_du_kien,
            "thoi_gian_tra_du_kien": self.thoi_gian_tra_du_kien,
            "trang_thai": "chờ_duyệt",
        }

        # chỉ gán thiết bị KHO (đúng constraint của bạn)
        if self.thiet_bi_goi_y_ids:
            vals["thiet_bi_ids"] = [(6, 0, self.thiet_bi_goi_y_ids.ids)]

        rec = self.env["dat_phong"].sudo().create(vals)

        return {
            "type": "ir.actions.act_window",
            "res_model": "dat_phong",
            "res_id": rec.id,
            "view_mode": "form",
            "target": "current",
        }

# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class PhieuLuong(models.Model):
    _name = "phieu_luong"
    _description = "Phiếu lương"
    _order = "ngay_tu desc, id desc"

    nhan_vien_id = fields.Many2one(
        "nhan_vien",
        string="Nhân viên",
        required=True,
        ondelete="cascade",
    )

    ngay_tu = fields.Date(string="Từ ngày", required=True)
    ngay_den = fields.Date(string="Đến ngày", required=True)

    trang_thai = fields.Selection(
        [
            ("nhap", "Nháp"),
            ("da_tinh", "Đã tính"),
            ("da_chot", "Đã chốt"),
            ("da_tra", "Đã trả"),
        ],
        string="Trạng thái",
        default="nhap",
        required=True,
    )

    # Snapshot hợp đồng (để chốt lương không bị đổi khi sửa hợp đồng)
    hop_dong_id = fields.Many2one("hop_dong", string="Hợp đồng áp dụng", ondelete="set null", readonly=True)

    luong_cung_thang = fields.Float(string="Lương cứng/tháng", readonly=True)
    so_ngay_cong_chuan = fields.Integer(string="Ngày công chuẩn", readonly=True)
    so_gio_mot_ngay = fields.Float(string="Giờ/1 ngày", readonly=True)

    # Tổng hợp chấm công / nghỉ / OT
    tong_gio_thieu = fields.Float(string="Tổng giờ thiếu", readonly=True)
    tong_gio_ot = fields.Float(string="Tổng giờ OT", readonly=True)
    so_ngay_nghi_co_luong = fields.Float(string="Ngày nghỉ có lương", readonly=True)
    so_ngay_nghi_khong_luong = fields.Float(string="Ngày nghỉ không lương", readonly=True)

    # Đơn giá
    don_gia_gio = fields.Float(string="Đơn giá 1 giờ", readonly=True)

    # Các khoản tiền
    luong_co_ban = fields.Float(string="Lương cơ bản", readonly=True)
    tong_phu_cap = fields.Float(string="Tổng phụ cấp", readonly=True)
    tien_tang_ca = fields.Float(string="Tiền tăng ca", readonly=True)
    tru_thieu_gio = fields.Float(string="Trừ thiếu giờ", readonly=True)
    tru_bao_hiem = fields.Float(string="Trừ bảo hiểm", readonly=True)

    thuc_nhan = fields.Float(string="Thực nhận", readonly=True)

    dong_ids = fields.One2many("dong_phieu_luong", "phieu_luong_id", string="Chi tiết")

    ghi_chu = fields.Text(string="Ghi chú")

    _sql_constraints = [
        ("uniq_nv_ky",
         "unique(nhan_vien_id, ngay_tu, ngay_den)",
         "Nhân viên đã có phiếu lương cho kỳ này!"),
    ]

    @api.constrains("ngay_tu", "ngay_den")
    def _check_dates(self):
        for r in self:
            if r.ngay_tu and r.ngay_den and r.ngay_den < r.ngay_tu:
                raise ValidationError("Đến ngày không được nhỏ hơn Từ ngày!")

    # ---------------------------
    # Helpers
    # ---------------------------
    def _find_hop_dong_in_ky(self):
        """Tìm hợp đồng hiệu lực giao với kỳ lương."""
        self.ensure_one()
        if not (self.nhan_vien_id and self.ngay_tu and self.ngay_den):
            return False

        start = fields.Date.from_string(self.ngay_tu)
        end = fields.Date.from_string(self.ngay_den)

        domain = [
            ("nhan_vien_id", "=", self.nhan_vien_id.id),
            ("trang_thai", "=", "hieu_luc"),
            ("ngay_bat_dau", "<=", end),
            "|",
            ("ngay_ket_thuc", "=", False),
            ("ngay_ket_thuc", ">=", start),
        ]
        # ưu tiên hợp đồng bắt đầu gần nhất
        return self.env["hop_dong"].search(domain, order="ngay_bat_dau desc, id desc", limit=1)

    def _sum_phu_cap_hop_dong(self, hop_dong):
        return sum(hop_dong.phu_cap_ids.mapped("so_tien")) if hop_dong else 0.0

    def _tinh_don_gia_gio(self, hop_dong):
        if not hop_dong:
            return 0.0
        wage = hop_dong.luong_cung_thang or 0.0
        days = hop_dong.so_ngay_cong_chuan or 0
        hours = hop_dong.so_gio_mot_ngay or 0.0
        if days <= 0 or hours <= 0:
            return 0.0
        return wage / (days * hours)

    def _tong_gio_thieu_tu_cham_cong(self, start: date, end: date):
        """Tổng giờ thiếu từ chấm công (dựa trên so_gio_thieu đã compute)."""
        domain = [
            ("nhan_vien_id", "=", self.nhan_vien_id.id),
            ("ngay", ">=", start),
            ("ngay", "<=", end),
        ]
        recs = self.env["cham_cong"].search(domain)
        return sum(recs.mapped("so_gio_thieu")) if recs else 0.0

    def _tong_ot_da_duyet(self, start: date, end: date):
        domain = [
            ("nhan_vien_id", "=", self.nhan_vien_id.id),
            ("trang_thai", "=", "da_duyet"),
            ("ngay", ">=", start),
            ("ngay", "<=", end),
        ]
        recs = self.env["don_tang_ca"].search(domain)
        tong_gio = sum(recs.mapped("so_gio_ot")) if recs else 0.0
        # hệ số: nếu bạn muốn gom theo từng đơn có hệ số khác nhau,
        # thì xử lý ở bước tiền_tang_ca thay vì chỉ trả tổng giờ.
        return tong_gio

    def _tinh_tien_ot(self, start: date, end: date, don_gia_gio: float):
        domain = [
            ("nhan_vien_id", "=", self.nhan_vien_id.id),
            ("trang_thai", "=", "da_duyet"),
            ("ngay", ">=", start),
            ("ngay", "<=", end),
        ]
        recs = self.env["don_tang_ca"].search(domain)
        tien = 0.0
        for r in recs:
            he_so = r.he_so or 2.0
            tien += (r.so_gio_ot or 0.0) * don_gia_gio * he_so
        return tien

    def _tinh_nghi_phep_da_duyet(self, start: date, end: date):
        """Tính số ngày nghỉ có lương/không lương trong kỳ."""
        domain = [
            ("nhan_vien_id", "=", self.nhan_vien_id.id),
            ("trang_thai", "=", "da_duyet"),
            ("ngay_tu", "<=", end),
            ("ngay_den", ">=", start),
        ]
        recs = self.env["don_nghi_phep"].search(domain)
        co_luong = 0.0
        khong_luong = 0.0
        for r in recs:
            d1 = max(fields.Date.from_string(r.ngay_tu), start)
            d2 = min(fields.Date.from_string(r.ngay_den), end)
            days = float((d2 - d1).days + 1)
            if r.loai_nghi == "co_luong":
                co_luong += days
            else:
                khong_luong += days
        return co_luong, khong_luong

    def _dem_ngay_co_mat_du_8h(self, start: date, end: date):
        """
        Đếm số ngày có mặt đủ giờ chuẩn (>= 8h).
        (Ở đây dùng hardcode 8h; nếu muốn theo hợp đồng thì truyền so_gio_mot_ngay vào)
        """
        domain = [
            ("nhan_vien_id", "=", self.nhan_vien_id.id),
            ("ngay", ">=", start),
            ("ngay", "<=", end),
        ]
        recs = self.env["cham_cong"].search(domain)
        return sum(1 for r in recs if (r.so_gio_lam or 0.0) >= 8.0)

    # ---------------------------
    # Main action: tính lương
    # ---------------------------
    def action_tinh_luong(self):
        for slip in self:
            if slip.trang_thai in ("da_chot", "da_tra"):
                raise ValidationError("Phiếu lương đã chốt/đã trả, không thể tính lại!")

            if not (slip.ngay_tu and slip.ngay_den):
                raise ValidationError("Vui lòng chọn kỳ lương (Từ ngày / Đến ngày)!")

            start = fields.Date.from_string(slip.ngay_tu)
            end = fields.Date.from_string(slip.ngay_den)

            hop_dong = slip._find_hop_dong_in_ky()
            if not hop_dong:
                raise ValidationError("Không tìm thấy hợp đồng hiệu lực cho nhân viên trong kỳ lương!")

            # snapshot
            slip.hop_dong_id = hop_dong.id
            slip.luong_cung_thang = hop_dong.luong_cung_thang
            slip.so_ngay_cong_chuan = hop_dong.so_ngay_cong_chuan
            slip.so_gio_mot_ngay = hop_dong.so_gio_mot_ngay

            don_gia = slip._tinh_don_gia_gio(hop_dong)
            slip.don_gia_gio = don_gia

            # dữ liệu kỳ
            tong_gio_thieu = slip._tong_gio_thieu_tu_cham_cong(start, end)
            co_luong, khong_luong = slip._tinh_nghi_phep_da_duyet(start, end)
            tong_gio_ot = slip._tong_ot_da_duyet(start, end)

            # ngày đủ chuẩn (>=8h) + ngày nghỉ có lương
            ngay_du_8h = slip._dem_ngay_co_mat_du_8h(start, end)
            paid_days = ngay_du_8h + co_luong

            # lương cơ bản theo giờ: paid_days * hours/day * don_gia
            luong_co_ban = (paid_days * (hop_dong.so_gio_mot_ngay or 8.0)) * don_gia

            # phụ cấp cố định
            tong_phu_cap = slip._sum_phu_cap_hop_dong(hop_dong)

            # OT pay: sum theo từng đơn (để lấy hệ số)
            tien_tang_ca = slip._tinh_tien_ot(start, end, don_gia)

            # trừ thiếu giờ
            tru_thieu_gio = (tong_gio_thieu or 0.0) * don_gia

            # bảo hiểm: để 0.0 trước, sau bạn bổ sung rule
            tru_bao_hiem = slip.tru_bao_hiem or 0.0

            thuc_nhan = luong_co_ban + tong_phu_cap + tien_tang_ca - tru_thieu_gio - tru_bao_hiem

            # ghi tổng
            slip.tong_gio_thieu = tong_gio_thieu
            slip.tong_gio_ot = tong_gio_ot
            slip.so_ngay_nghi_co_luong = co_luong
            slip.so_ngay_nghi_khong_luong = khong_luong

            slip.luong_co_ban = luong_co_ban
            slip.tong_phu_cap = tong_phu_cap
            slip.tien_tang_ca = tien_tang_ca
            slip.tru_thieu_gio = tru_thieu_gio
            slip.tru_bao_hiem = tru_bao_hiem
            slip.thuc_nhan = thuc_nhan

            # làm chi tiết line cho dễ hiểu
            slip.dong_ids.unlink()
            lines = [
                (0, 0, {"sequence": 10, "ma": "LUONGCB", "ten": "Lương cơ bản", "so_tien": luong_co_ban}),
                (0, 0, {"sequence": 20, "ma": "PHUCAP", "ten": "Phụ cấp", "so_tien": tong_phu_cap}),
                (0, 0, {"sequence": 30, "ma": "OT", "ten": "Tiền tăng ca", "so_tien": tien_tang_ca}),
                (0, 0, {"sequence": 40, "ma": "TRUTHIEU", "ten": "Trừ thiếu giờ", "so_tien": -tru_thieu_gio}),
                (0, 0, {"sequence": 50, "ma": "BH", "ten": "Trừ bảo hiểm", "so_tien": -tru_bao_hiem}),
                (0, 0, {"sequence": 60, "ma": "THUCNHAN", "ten": "Thực nhận", "so_tien": thuc_nhan}),
            ]
            slip.write({"dong_ids": lines, "trang_thai": "da_tinh"})

    def action_chot(self):
        for r in self:
            if r.trang_thai != "da_tinh":
                raise ValidationError("Chỉ được chốt khi phiếu lương ở trạng thái 'Đã tính'!")
            r.trang_thai = "da_chot"

    def action_da_tra(self):
        for r in self:
            if r.trang_thai != "da_chot":
                raise ValidationError("Chỉ được chuyển 'Đã trả' khi phiếu lương đã chốt!")
            r.trang_thai = "da_tra"

    def action_ve_nhap(self):
        for r in self:
            if r.trang_thai in ("da_chot", "da_tra"):
                raise ValidationError("Phiếu lương đã chốt/đã trả không được về nháp!")
            r.trang_thai = "nhap"

# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class DonNghiPhep(models.Model):
    _name = "don_nghi_phep"
    _description = "Đơn nghỉ phép"
    _order = "ngay_tu desc, id desc"

    nhan_vien_id = fields.Many2one(
        "nhan_vien",
        string="Nhân viên",
        required=True,
        ondelete="cascade",
    )

    loai_nghi = fields.Selection(
        [
            ("co_luong", "Nghỉ có lương"),
            ("khong_luong", "Nghỉ không lương"),
        ],
        string="Loại nghỉ",
        required=True,
        default="co_luong",
    )

    ngay_tu = fields.Date(string="Từ ngày", required=True)
    ngay_den = fields.Date(string="Đến ngày", required=True)

    so_ngay = fields.Float(
        string="Số ngày nghỉ",
        compute="_compute_so_ngay",
        store=True,
        readonly=True,
    )

    ly_do = fields.Char(string="Lý do")
    ghi_chu = fields.Text(string="Ghi chú")

    trang_thai = fields.Selection(
        [
            ("nhap", "Nháp"),
            ("gui_duyet", "Gửi duyệt"),
            ("da_duyet", "Đã duyệt"),
            ("tu_choi", "Từ chối"),
            ("huy", "Hủy"),
        ],
        string="Trạng thái",
        default="nhap",
        required=True,
    )

    nguoi_duyet_id = fields.Many2one(
        "res.users",
        string="Người duyệt",
        ondelete="set null",
    )
    ngay_duyet = fields.Datetime(string="Ngày duyệt", readonly=True)

    @api.depends("ngay_tu", "ngay_den")
    def _compute_so_ngay(self):
        for r in self:
            if r.ngay_tu and r.ngay_den:
                d1 = fields.Date.from_string(r.ngay_tu)
                d2 = fields.Date.from_string(r.ngay_den)
                if d2 >= d1:
                    r.so_ngay = float((d2 - d1).days + 1)
                else:
                    r.so_ngay = 0.0
            else:
                r.so_ngay = 0.0

    @api.constrains("ngay_tu", "ngay_den")
    def _check_dates(self):
        for r in self:
            if r.ngay_tu and r.ngay_den and r.ngay_den < r.ngay_tu:
                raise ValidationError("Đến ngày không được nhỏ hơn Từ ngày!")

    # ---------------------------
    # Helpers: tính quota 1 ngày/tháng
    # ---------------------------
    def _month_start(self, d: date) -> date:
        return date(d.year, d.month, 1)

    def _next_month_start(self, d: date) -> date:
        if d.month == 12:
            return date(d.year + 1, 1, 1)
        return date(d.year, d.month + 1, 1)

    def _iter_month_ranges(self, start: date, end: date):
        """
        Trả về list các đoạn (month_start, month_end, days_in_that_month_segment)
        """
        cur = self._month_start(start)
        while cur <= end:
            nm = self._next_month_start(cur)
            month_end = nm - timedelta(days=1)

            seg_start = max(start, cur)
            seg_end = min(end, month_end)
            days = (seg_end - seg_start).days + 1
            yield (cur, month_end, days)

            cur = nm

    def _check_quota_nghi_co_luong_1_ngay_thang(self):
        """
        Rule nghiệp vụ: nghỉ có lương tối đa 1 ngày/tháng.
        Áp dụng khi DUYỆT.
        """
        for r in self:
            if r.loai_nghi != "co_luong":
                continue
            if not r.nhan_vien_id or not r.ngay_tu or not r.ngay_den:
                continue

            start = fields.Date.from_string(r.ngay_tu)
            end = fields.Date.from_string(r.ngay_den)

            # Với từng tháng mà đơn này chạm vào, kiểm tra tổng ngày co_luong đã duyệt
            for month_start, month_end, req_days in r._iter_month_ranges(start, end):
                # Tổng ngày co_luong đã duyệt trong tháng đó (không tính bản ghi hiện tại)
                domain = [
                    ("id", "!=", r.id),
                    ("nhan_vien_id", "=", r.nhan_vien_id.id),
                    ("loai_nghi", "=", "co_luong"),
                    ("trang_thai", "=", "da_duyet"),
                    ("ngay_tu", "<=", month_end),
                    ("ngay_den", ">=", month_start),
                ]
                others = self.search(domain)

                used = 0.0
                for o in others:
                    o_start = fields.Date.from_string(o.ngay_tu)
                    o_end = fields.Date.from_string(o.ngay_den)
                    # phần giao với tháng
                    seg_start = max(o_start, month_start)
                    seg_end = min(o_end, month_end)
                    used += float((seg_end - seg_start).days + 1)

                if used + req_days > 1.0:
                    raise ValidationError(
                        f"Vượt quota nghỉ có lương 1 ngày/tháng!\n"
                        f"Tháng {month_start.month}/{month_start.year}: đã dùng {used} ngày, "
                        f"đơn này yêu cầu {req_days} ngày."
                    )

    # ---------------------------
    # Actions workflow
    # ---------------------------
    def action_gui_duyet(self):
        for r in self:
            if r.trang_thai != "nhap":
                continue
            r.trang_thai = "gui_duyet"

    def action_duyet(self):
        for r in self:
            if r.trang_thai != "gui_duyet":
                continue

            # ✅ Check quota nghỉ có lương 1 ngày/tháng
            r._check_quota_nghi_co_luong_1_ngay_thang()

            r.trang_thai = "da_duyet"
            r.nguoi_duyet_id = self.env.user.id
            r.ngay_duyet = fields.Datetime.now()

    def action_tu_choi(self):
        for r in self:
            if r.trang_thai not in ("gui_duyet",):
                continue
            r.trang_thai = "tu_choi"
            r.nguoi_duyet_id = self.env.user.id
            r.ngay_duyet = fields.Datetime.now()

    def action_huy(self):
        for r in self:
            if r.trang_thai in ("da_duyet",):
                raise ValidationError("Đơn đã duyệt không thể hủy (nếu muốn, hãy tạo đơn khác/hoặc xử lý quy trình).")
            r.trang_thai = "huy"

    def action_ve_nhap(self):
        for r in self:
            if r.trang_thai not in ("gui_duyet", "tu_choi"):
                continue
            r.trang_thai = "nhap"
            r.nguoi_duyet_id = False
            r.ngay_duyet = False

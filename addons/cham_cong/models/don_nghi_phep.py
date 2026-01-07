# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DonNghiPhep(models.Model):
    _name = "don_nghi_phep"
    _description = "Đơn nghỉ phép"
    _order = "ngay_tu desc, id desc"

    nhan_vien_id = fields.Many2one(
        "nhan_vien",
        string="Nhân viên",
        required=True,
        ondelete="cascade",
        index=True,
    )

    loai_nghi = fields.Selection(
        [
            ("co_luong", "Nghỉ có lương"),
            ("khong_luong", "Nghỉ không lương"),
            ("khac", "Khác"),
        ],
        string="Loại nghỉ",
        required=True,
        default="co_luong",
        index=True,
    )

    ngay_tu = fields.Date(string="Từ ngày", required=True)
    ngay_den = fields.Date(string="Đến ngày", required=True)

    so_ngay = fields.Float(string="Số ngày", compute="_compute_so_ngay", store=True, readonly=True)

    ly_do = fields.Text(string="Lý do")
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
        index=True,
    )

    nguoi_duyet_id = fields.Many2one("res.users", string="Người duyệt", readonly=True)
    ngay_duyet = fields.Datetime(string="Ngày duyệt", readonly=True)

    _sql_constraints = [
        ("check_dates", "CHECK(ngay_den >= ngay_tu)", "Ngày đến không được nhỏ hơn ngày từ!"),
    ]

    @api.depends("ngay_tu", "ngay_den")
    def _compute_so_ngay(self):
        for r in self:
            if r.ngay_tu and r.ngay_den and r.ngay_den >= r.ngay_tu:
                # +1 vì tính cả ngày bắt đầu
                r.so_ngay = (r.ngay_den - r.ngay_tu).days + 1
            else:
                r.so_ngay = 0.0

    @api.constrains("ngay_tu", "ngay_den")
    def _check_dates(self):
        for r in self:
            if r.ngay_tu and r.ngay_den and r.ngay_den < r.ngay_tu:
                raise ValidationError("Ngày đến không được nhỏ hơn ngày từ!")

    # ===== ACTION BUTTONS =====
    def action_gui_duyet(self):
        for r in self:
            if r.trang_thai != "nhap":
                continue
            r.trang_thai = "gui_duyet"

    def action_duyet(self):
        for r in self:
            if r.trang_thai != "gui_duyet":
                continue
            r.write({
                "trang_thai": "da_duyet",
                "nguoi_duyet_id": self.env.user.id,
                "ngay_duyet": fields.Datetime.now(),
            })

    def action_tu_choi(self):
        for r in self:
            if r.trang_thai != "gui_duyet":
                continue
            r.write({
                "trang_thai": "tu_choi",
                "nguoi_duyet_id": self.env.user.id,
                "ngay_duyet": fields.Datetime.now(),
            })

    def action_huy(self):
        for r in self:
            if r.trang_thai in ("da_duyet", "huy"):
                continue
            r.trang_thai = "huy"

    def action_ve_nhap(self):
        for r in self:
            if r.trang_thai not in ("gui_duyet", "tu_choi"):
                continue
            r.write({
                "trang_thai": "nhap",
                "nguoi_duyet_id": False,
                "ngay_duyet": False,
            })

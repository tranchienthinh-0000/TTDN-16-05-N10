# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class KhauHao(models.Model):
    _name = "khau_hao"
    _description = "Khấu hao (cơ bản)"
    _order = "ngay_tinh desc, id desc"

    tai_san_id = fields.Many2one(
        "quan_ly_ho_so_tai_san",
        string="Tài sản",
        required=True,
        ondelete="cascade"
    )

    ngay_tinh = fields.Date(string="Ngày tính", required=True, default=fields.Date.today)

    so_thang_khau_hao = fields.Integer(string="Số tháng khấu hao", default=36)
    ngay_bat_dau = fields.Date(string="Ngày bắt đầu khấu hao")

    nguyen_gia = fields.Float(
        string="Nguyên giá",
        related="tai_san_id.nguyen_gia",
        store=False,
        readonly=True
    )

    gia_tri_con_lai = fields.Float(
        string="Giá trị còn lại",
        compute="_compute_con_lai",
        store=False,
        readonly=True
    )

    ghi_chu = fields.Text(string="Ghi chú")

    @api.constrains("so_thang_khau_hao")
    def _check_months(self):
        for r in self:
            if r.so_thang_khau_hao <= 0:
                raise ValidationError("Số tháng khấu hao phải > 0!")

    @api.constrains("ngay_bat_dau", "ngay_tinh")
    def _check_dates(self):
        for r in self:
            if r.ngay_bat_dau and r.ngay_tinh and r.ngay_tinh < r.ngay_bat_dau:
                raise ValidationError("Ngày tính không được nhỏ hơn ngày bắt đầu khấu hao!")

    @api.depends("tai_san_id.nguyen_gia", "so_thang_khau_hao", "ngay_bat_dau", "ngay_tinh")
    def _compute_con_lai(self):
        for r in self:
            if not r.ngay_bat_dau or not r.ngay_tinh or r.so_thang_khau_hao <= 0:
                r.gia_tri_con_lai = r.nguyen_gia
                continue

            # số tháng đã dùng (tính theo chênh lệch năm/tháng)
            months_used = (r.ngay_tinh.year - r.ngay_bat_dau.year) * 12 + (r.ngay_tinh.month - r.ngay_bat_dau.month)
            months_used = max(months_used, 0)

            per_month = r.nguyen_gia / r.so_thang_khau_hao
            r.gia_tri_con_lai = max(r.nguyen_gia - per_month * months_used, 0.0)

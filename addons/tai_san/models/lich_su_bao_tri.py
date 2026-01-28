# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LichSuBaoTri(models.Model):
    _name = "lich_su_bao_tri"
    _description = "Bảng chứa thông tin lịch sử bảo trì"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "ma_lich_su_bao_tri desc"

    _sql_constraints = [
        ("ma_lich_su_bao_tri_unique", "unique(ma_lich_su_bao_tri)", "Mã lịch sử bảo trì phải là duy nhất!"),
    ]

    ma_lich_su_bao_tri = fields.Char(
        string="Mã lịch sử bảo trì",
        required=True,
        copy=False,
        readonly=True,
        default="New",
        tracking=True,
    )

    # Nếu bạn chỉ cần Date thì giữ Date. Nếu muốn giờ phút, đổi sang Datetime ở cả model + view.
    ngay_bao_tri = fields.Date(string="Thời gian bảo trì", required=True, tracking=True)
    ngay_tra = fields.Date(string="Thời gian trả")
    ghi_chu = fields.Html(string="Ghi chú")

    currency_id = fields.Many2one(
        "res.currency",
        string="Tiền tệ",
        default=lambda self: self.env.company.currency_id.id,
        required=True,
    )
    chi_phi = fields.Monetary(string="Chi phí", currency_field="currency_id", required=True, tracking=True)

    tai_san_id = fields.Many2one(
        comodel_name="tai_san",
        string="Tài sản",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    @api.constrains("ngay_bao_tri", "ngay_tra")
    def _check_dates(self):
        for r in self:
            if r.ngay_bao_tri and r.ngay_tra and r.ngay_tra < r.ngay_bao_tri:
                raise ValidationError("Ngày trả phải lớn hơn hoặc bằng ngày bảo trì.")

    @api.constrains("chi_phi")
    def _check_cost(self):
        for r in self:
            if r.chi_phi is not None and r.chi_phi < 0:
                raise ValidationError("Chi phí không được âm.")

    @api.model
    def create(self, vals):
        if vals.get("ma_lich_su_bao_tri", "New") == "New":
            vals["ma_lich_su_bao_tri"] = self.env["ir.sequence"].next_by_code("lich_su_bao_tri") or "New"
        return super().create(vals)

# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LichSuSuDung(models.Model):
    _name = "lich_su_su_dung"
    _description = "Bảng chứa thông tin lịch sử sử dụng"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "ma_lich_su_su_dung desc"

    _sql_constraints = [
        ("ma_lich_su_su_dung_unique", "unique(ma_lich_su_su_dung)", "Mã lịch sử sử dụng phải là duy nhất!"),
    ]

    ma_lich_su_su_dung = fields.Char(
        string="Mã lịch sử sử dụng",
        required=True,
        copy=False,
        readonly=True,
        default="New",
        tracking=True,
    )

    ngay_muon = fields.Datetime(string="Thời gian mượn", required=True, tracking=True)
    ngay_tra = fields.Datetime(string="Thời gian trả", required=True, tracking=True)
    ghi_chu = fields.Char(string="Ghi chú")

    nhan_vien_id = fields.Many2one(
        "nhan_vien",
        string="Nhân sự",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    tai_san_id = fields.Many2one(
        "tai_san",
        string="Tài sản",
        required=True,
        ondelete="restrict",
        tracking=True,
        index=True,
    )

    @api.constrains("ngay_muon", "ngay_tra")
    def _check_dates(self):
        for r in self:
            if r.ngay_muon and r.ngay_tra and r.ngay_tra < r.ngay_muon:
                raise ValidationError(_("Thời gian trả phải lớn hơn hoặc bằng thời gian mượn."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("ma_lich_su_su_dung", "New") in (False, "", "New"):
                vals["ma_lich_su_su_dung"] = self.env["ir.sequence"].next_by_code("lich_su_su_dung") or "New"
        return super().create(vals_list)

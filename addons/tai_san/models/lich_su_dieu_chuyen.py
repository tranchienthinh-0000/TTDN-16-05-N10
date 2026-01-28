# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LichSuDiChuyen(models.Model):
    _name = "lich_su_dieu_chuyen"
    _description = "Lịch sử điều chuyển tài sản"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "ngay_di_chuyen desc"

    tai_san_id = fields.Many2one(
        comodel_name="tai_san",
        string="Tài sản",
        required=True,
        ondelete="cascade",
        tracking=True,
    )

    vi_tri_chuyen_id = fields.Many2one(
        comodel_name="vi_tri",
        string="Vị trí chuyển",
        required=True,
        tracking=True,
    )

    vi_tri_den_id = fields.Many2one(
        comodel_name="vi_tri",
        string="Vị trí đến",
        required=True,
        tracking=True,
    )

    ngay_di_chuyen = fields.Datetime(
        string="Thời gian điều chuyển",
        default=fields.Datetime.now,  # FIX: đúng kiểu Datetime
        required=True,
        tracking=True,
    )

    ghi_chu = fields.Char(string="Ghi chú")

    is_current_location = fields.Boolean(
        string="Vị trí hiện tại",
        compute="_compute_is_current_location",
        store=True,
    )

    @api.depends("tai_san_id.vi_tri_hien_tai_id", "vi_tri_den_id")
    def _compute_is_current_location(self):
        for record in self:
            record.is_current_location = record.vi_tri_den_id == record.tai_san_id.vi_tri_hien_tai_id

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        # đồng bộ vị trí hiện tại của tài sản theo vị trí đến
        if rec.tai_san_id and rec.vi_tri_den_id:
            rec.tai_san_id.write({"vi_tri_hien_tai_id": rec.vi_tri_den_id.id})
        return rec

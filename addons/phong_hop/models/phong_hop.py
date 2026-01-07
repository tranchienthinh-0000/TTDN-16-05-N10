# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PhongHop(models.Model):
    _name = "phong_hop"
    _description = "Phòng họp"
    _rec_name = "ten"
    _order = "ten asc, id desc"

    ten = fields.Char(string="Tên phòng", required=True)
    suc_chua = fields.Integer(string="Sức chứa", default=0)
    vi_tri = fields.Char(string="Vị trí")

    # Tiện ích đi kèm
    co_may_chieu = fields.Boolean(string="Máy chiếu")
    co_bang_trang = fields.Boolean(string="Bảng trắng")
    co_am_thanh = fields.Boolean(string="Âm thanh")

    ghi_chu = fields.Text(string="Ghi chú")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("uniq_ten_phong", "unique(ten)", "Tên phòng đã tồn tại!"),
    ]

    @api.constrains("suc_chua")
    def _check_suc_chua(self):
        for r in self:
            if r.suc_chua < 0:
                raise ValidationError("Sức chứa không được âm!")

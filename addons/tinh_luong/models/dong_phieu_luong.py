# -*- coding: utf-8 -*-
from odoo import models, fields

class DongPhieuLuong(models.Model):
    _name = "dong_phieu_luong"
    _description = "Dòng phiếu lương"
    _order = "sequence asc, id asc"

    phieu_luong_id = fields.Many2one("phieu_luong", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    ma = fields.Char(string="Mã", required=True)
    ten = fields.Char(string="Tên", required=True)
    so_tien = fields.Float(string="Số tiền", default=0.0)
    ghi_chu = fields.Text(string="Ghi chú")

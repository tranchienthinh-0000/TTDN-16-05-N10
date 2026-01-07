# -*- coding: utf-8 -*-
from odoo import models, fields


class NhanVienInherit(models.Model):
    _inherit = "nhan_vien"

    lich_hop_chu_tri_ids = fields.One2many(
        "dat_phong",
        "nguoi_chu_tri_id",
        string="Lịch họp chủ trì",
    )

    lich_hop_tham_du_ids = fields.Many2many(
        "dat_phong",
        "dat_phong_nhan_vien_rel",
        "nhan_vien_id",
        "dat_phong_id",
        string="Lịch họp tham dự",
    )

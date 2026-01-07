# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PhuCapHopDong(models.Model):
    _name = "phu_cap_hop_dong"
    _description = "Phụ cấp hợp đồng"
    _order = "hop_dong_id desc, id desc"

    hop_dong_id = fields.Many2one(
        "hop_dong",
        string="Hợp đồng",
        required=True,
        ondelete="cascade",
    )

    loai_phu_cap_id = fields.Many2one(
        "loai_phu_cap",
        string="Loại phụ cấp",
        required=True,
        ondelete="restrict",
    )

    so_tien = fields.Float(string="Số tiền", default=0.0)
    ghi_chu = fields.Text(string="Ghi chú")

    _sql_constraints = [
        ("uniq_pc_hop_dong", "unique(hop_dong_id, loai_phu_cap_id)", "Phụ cấp này đã tồn tại trong hợp đồng!"),
    ]

    @api.constrains("so_tien")
    def _check_so_tien(self):
        for r in self:
            if r.so_tien < 0:
                raise ValidationError("Số tiền phụ cấp không được âm!")

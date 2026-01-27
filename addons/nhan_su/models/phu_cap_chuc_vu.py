# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PhuCapChucVu(models.Model):
    _name = "phu_cap_chuc_vu"
    _description = "Phụ cấp theo chức vụ"
    _order = "chuc_vu_id asc, id desc"

    chuc_vu_id = fields.Many2one(
        "chuc_vu",
        string="Chức vụ",
        required=True,
        ondelete="cascade"
    )
    loai_phu_cap_id = fields.Many2one(
        "loai_phu_cap",
        string="Loại phụ cấp",
        required=True,
        ondelete="restrict"
    )
    so_tien = fields.Float(string="Số tiền", default=0.0)
    ghi_chu = fields.Text(string="Ghi chú")

    _sql_constraints = [
        ("uniq_pc_chucvu", "unique(chuc_vu_id, loai_phu_cap_id)", "Phụ cấp này đã tồn tại cho chức vụ!"),
    ]

    @api.constrains("so_tien")
    def _check_so_tien(self):
        for r in self:
            if r.so_tien < 0:
                raise ValidationError("Số tiền phụ cấp không được âm!")

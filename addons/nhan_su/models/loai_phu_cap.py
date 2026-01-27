# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LoaiPhuCap(models.Model):
    _name = "loai_phu_cap"
    _description = "Loại phụ cấp"
    _rec_name = "ten"
    _order = "ma asc, ten asc"

    ma = fields.Char(string="Mã", required=True, index=True)
    ten = fields.Char(string="Tên", required=True)
    ghi_chu = fields.Text(string="Ghi chú")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("uniq_ma_loai_phu_cap", "unique(ma)", "Mã loại phụ cấp đã tồn tại!"),
    ]

    @api.constrains("ma", "ten")
    def _check_ma_ten(self):
        for r in self:
            if r.ma and not r.ma.strip():
                raise ValidationError("Mã loại phụ cấp không được để trống hoặc chỉ chứa khoảng trắng!")
            if r.ten and not r.ten.strip():
                raise ValidationError("Tên loại phụ cấp không được để trống hoặc chỉ chứa khoảng trắng!")

    def _strip_vals(self, vals, keys):
        for k in keys:
            if vals.get(k) and isinstance(vals.get(k), str):
                vals[k] = vals[k].strip()
        return vals

    @api.model
    def create(self, vals):
        vals = self._strip_vals(vals, ["ma", "ten"])
        return super().create(vals)

    def write(self, vals):
        vals = self._strip_vals(vals, ["ma", "ten"])
        return super().write(vals)

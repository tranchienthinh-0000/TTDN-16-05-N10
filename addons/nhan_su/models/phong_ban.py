# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PhongBan(models.Model):
    _name = "phong_ban"
    _description = "Phòng ban"
    _rec_name = "ten_phong"
    _order = "ma_phong asc, ten_phong asc"

    ma_phong = fields.Char(string="Mã phòng", required=True)
    ten_phong = fields.Char(string="Tên phòng", required=True)
    mo_ta = fields.Text(string="Mô tả")

    nhan_vien_ids = fields.One2many(
        "nhan_vien",
        "phong_ban_id",
        string="Danh sách nhân viên"
    )

    _sql_constraints = [
        ("ma_phong_unique", "unique(ma_phong)", "Mã phòng đã tồn tại!"),
    ]

    @api.constrains("ma_phong", "ten_phong")
    def _check_ma_ten(self):
        for r in self:
            if r.ma_phong and not r.ma_phong.strip():
                raise ValidationError("Mã phòng không được để trống hoặc chỉ chứa khoảng trắng!")
            if r.ten_phong and not r.ten_phong.strip():
                raise ValidationError("Tên phòng không được để trống hoặc chỉ chứa khoảng trắng!")

    @api.model
    def create(self, vals):
        if vals.get("ma_phong"):
            vals["ma_phong"] = vals["ma_phong"].strip()
        if vals.get("ten_phong"):
            vals["ten_phong"] = vals["ten_phong"].strip()
        return super().create(vals)

    def write(self, vals):
        if vals.get("ma_phong"):
            vals["ma_phong"] = vals["ma_phong"].strip()
        if vals.get("ten_phong"):
            vals["ten_phong"] = vals["ten_phong"].strip()
        return super().write(vals)

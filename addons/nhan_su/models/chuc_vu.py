# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ChucVu(models.Model):
    _name = "chuc_vu"
    _description = "Chức vụ"
    _rec_name = "ten"
    _order = "ma asc, ten asc"

    ma = fields.Char(string="Mã chức vụ", required=True, index=True)
    ten = fields.Char(string="Tên chức vụ", required=True)

    phong_ban_id = fields.Many2one(
        "phong_ban",
        string="Phòng ban",
        ondelete="set null"
    )

    # ✅ JD / mô tả công việc
    jd = fields.Html(string="Mô tả công việc (JD)")

    # ✅ Khung lương chuẩn theo chức vụ (trần/sàn)
    luong_cung = fields.Float(string="Lương cứng", default=0.0)
    tro_cap = fields.Float(string="Trợ cấp", default=0.0)

    # ✅ Phụ cấp mặc định theo chức vụ (tham chiếu tới model bạn đã tạo)
    phu_cap_mac_dinh_ids = fields.One2many(
        "phu_cap_chuc_vu",
        "chuc_vu_id",
        string="Phụ cấp mặc định"
    )

    ghi_chu = fields.Text(string="Ghi chú")

    _sql_constraints = [
        ("ma_unique", "unique(ma)", "Mã chức vụ đã tồn tại!"),
    ]

    @api.constrains("ma", "ten")
    def _check_ma_ten(self):
        for r in self:
            if r.ma and not r.ma.strip():
                raise ValidationError("Mã chức vụ không được để trống hoặc chỉ chứa khoảng trắng!")
            if r.ten and not r.ten.strip():
                raise ValidationError("Tên chức vụ không được để trống hoặc chỉ chứa khoảng trắng!")

    @api.constrains("luong_cung", "tro_cap")
    def _check_khung_luong(self):
        for r in self:
            if r.luong_cung < 0:
                raise ValidationError("Lương cứng không được âm!")
            if r.tro_cap < 0:
                raise ValidationError("Trợ cấp không được âm!")

    @api.model
    def create(self, vals):
        # chuẩn hoá input: trim khoảng trắng
        if vals.get("ma"):
            vals["ma"] = vals["ma"].strip()
        if vals.get("ten"):
            vals["ten"] = vals["ten"].strip()
        return super().create(vals)

    def write(self, vals):
        # chuẩn hoá input: trim khoảng trắng
        if vals.get("ma"):
            vals["ma"] = vals["ma"].strip()
        if vals.get("ten"):
            vals["ten"] = vals["ten"].strip()
        return super().write(vals)

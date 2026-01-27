# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ChungChi(models.Model):
    _name = "chung_chi"
    _description = "Chứng chỉ"
    _order = "ngay_cap desc, id desc"

    nhan_vien_id = fields.Many2one("nhan_vien", string="Nhân viên", required=True, ondelete="cascade")

    ma_chung_chi = fields.Char(string="Mã chứng chỉ", required=True, index=True)
    ten_chung_chi = fields.Char(string="Tên chứng chỉ", required=True)

    don_vi_cap = fields.Char(string="Đơn vị cấp")
    ngay_cap = fields.Date(string="Ngày cấp", required=True)
    ngay_het_han = fields.Date(string="Ngày hết hạn")

    trang_thai = fields.Selection(
        [("con_han", "Còn hạn"), ("het_han", "Hết hạn")],
        string="Trạng thái",
        compute="_compute_trang_thai",
        store=True,
        readonly=True,
    )

    ghi_chu = fields.Text(string="Ghi chú")

    _sql_constraints = [
        ("ma_chung_chi_unique", "unique(ma_chung_chi)", "Mã chứng chỉ đã tồn tại!"),
        ("check_ngay", "CHECK(ngay_het_han IS NULL OR ngay_het_han >= ngay_cap)", "Ngày hết hạn không được nhỏ hơn ngày cấp!"),
    ]

    @api.depends("ngay_cap", "ngay_het_han")
    def _compute_trang_thai(self):
        today = fields.Date.today()
        for r in self:
            if r.ngay_het_han and r.ngay_het_han < today:
                r.trang_thai = "het_han"
            else:
                r.trang_thai = "con_han"

    @api.constrains("ma_chung_chi", "ten_chung_chi")
    def _check_ma_ten(self):
        for r in self:
            if r.ma_chung_chi and not r.ma_chung_chi.strip():
                raise ValidationError("Mã chứng chỉ không được để trống hoặc chỉ chứa khoảng trắng!")
            if r.ten_chung_chi and not r.ten_chung_chi.strip():
                raise ValidationError("Tên chứng chỉ không được để trống hoặc chỉ chứa khoảng trắng!")

    def _strip_vals(self, vals, keys):
        for k in keys:
            if vals.get(k) and isinstance(vals.get(k), str):
                vals[k] = vals[k].strip()
        return vals

    @api.model
    def create(self, vals):
        vals = self._strip_vals(vals, ["ma_chung_chi", "ten_chung_chi", "don_vi_cap"])
        return super().create(vals)

    def write(self, vals):
        vals = self._strip_vals(vals, ["ma_chung_chi", "ten_chung_chi", "don_vi_cap"])
        return super().write(vals)

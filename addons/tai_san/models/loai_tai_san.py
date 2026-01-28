# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LoaiTaiSan(models.Model):
    _name = "loai_tai_san"
    _description = "Bảng chứa thông tin loại tài sản"
    _rec_name = "ten_loai_tai_san"
    _order = "ma_loai_tai_san"

    _sql_constraints = [
        ("ma_loai_tai_san_unique", "unique(ma_loai_tai_san)", "Mã loại tài sản phải là duy nhất!"),
    ]

    ma_loai_tai_san = fields.Char("Mã loại tài sản", required=True)
    ten_loai_tai_san = fields.Char("Tên loại tài sản", required=True)
    mo_ta = fields.Text("Mô tả")

    tai_san_ids = fields.One2many(
        comodel_name="tai_san",
        inverse_name="loai_tai_san_id",
        string="Tài sản",
    )

    tong_so_luong = fields.Integer("Tổng số lượng", compute="_compute_thong_ke_trang_thai", store=False)
    luu_tru_count = fields.Integer("Số lượng lưu trữ", compute="_compute_thong_ke_trang_thai", store=False)
    muon_count = fields.Integer("Số lượng mượn", compute="_compute_thong_ke_trang_thai", store=False)
    bao_tri_count = fields.Integer("Số lượng bảo trì", compute="_compute_thong_ke_trang_thai", store=False)
    hong_count = fields.Integer("Số lượng hỏng", compute="_compute_thong_ke_trang_thai", store=False)

    @api.depends("tai_san_ids", "tai_san_ids.trang_thai")
    def _compute_thong_ke_trang_thai(self):
        for record in self:
            tai_sans = record.tai_san_ids
            record.tong_so_luong = len(tai_sans)
            record.luu_tru_count = len(tai_sans.filtered(lambda t: t.trang_thai == "CatGiu"))
            record.muon_count = len(tai_sans.filtered(lambda t: t.trang_thai == "Muon"))
            record.bao_tri_count = len(tai_sans.filtered(lambda t: t.trang_thai == "BaoTri"))
            record.hong_count = len(tai_sans.filtered(lambda t: t.trang_thai in ["Hong", "HuHong"]))

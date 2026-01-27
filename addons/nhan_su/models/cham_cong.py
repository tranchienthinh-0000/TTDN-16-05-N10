# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ChamCong(models.Model):
    _name = "cham_cong"
    _description = "Chấm công"
    _order = "ngay desc, id desc"

    nhan_vien_id = fields.Many2one(
        "nhan_vien",
        string="Nhân viên",
        required=True,
        ondelete="cascade",
    )
    ngay = fields.Date(string="Ngày", required=True)

    gio_vao = fields.Datetime(string="Giờ vào")
    gio_ra = fields.Datetime(string="Giờ ra")

    gio_nghi_trua = fields.Float(string="Giờ nghỉ trưa", default=1.0)

    so_gio_lam = fields.Float(
        string="Số giờ làm (thực tế)",
        compute="_compute_so_gio",
        store=True,
        readonly=True,
    )

    so_gio_thieu = fields.Float(
        string="Số giờ thiếu so với 8h",
        compute="_compute_so_gio",
        store=True,
        readonly=True,
    )

    trang_thai = fields.Selection(
        [
            ("co_mat", "Có mặt"),
            ("vang", "Vắng"),
            ("di_muon", "Đi muộn"),
            ("ve_som", "Về sớm"),
        ],
        string="Trạng thái",
        default="co_mat",
        required=True,
    )

    ghi_chu = fields.Text(string="Ghi chú")

    _sql_constraints = [
        ("unique_nhan_vien_ngay", "unique(nhan_vien_id, ngay)", "Nhân viên đã có chấm công ngày này!"),
    ]

    @api.depends("gio_vao", "gio_ra", "gio_nghi_trua", "trang_thai")
    def _compute_so_gio(self):
        for r in self:
            # Vắng: coi như 0h và thiếu 8h
            if r.trang_thai == "vang":
                r.so_gio_lam = 0.0
                r.so_gio_thieu = 8.0
                continue

            if r.gio_vao and r.gio_ra:
                delta = (r.gio_ra - r.gio_vao).total_seconds() / 3600.0
                thuc_te = max(delta - (r.gio_nghi_trua or 0.0), 0.0)
                r.so_gio_lam = thuc_te
                r.so_gio_thieu = max(8.0 - thuc_te, 0.0)
            else:
                # Không có giờ vào/ra => coi như thiếu 8h
                r.so_gio_lam = 0.0
                r.so_gio_thieu = 8.0

    @api.constrains("gio_vao", "gio_ra")
    def _check_time(self):
        for r in self:
            if r.gio_vao and r.gio_ra and r.gio_ra < r.gio_vao:
                raise ValidationError("Giờ ra không được nhỏ hơn giờ vào!")

    @api.constrains("gio_nghi_trua")
    def _check_gio_nghi_trua(self):
        for r in self:
            if r.gio_nghi_trua < 0:
                raise ValidationError("Giờ nghỉ trưa không được âm!")
            if r.gio_nghi_trua > 4:
                raise ValidationError("Giờ nghỉ trưa quá lớn (vui lòng kiểm tra lại)!")

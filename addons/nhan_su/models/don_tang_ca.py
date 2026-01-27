# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DonTangCa(models.Model):
    _name = "don_tang_ca"
    _description = "Đơn tăng ca"
    _order = "gio_bat_dau desc, id desc"

    nhan_vien_id = fields.Many2one(
        "nhan_vien",
        string="Nhân viên",
        required=True,
        ondelete="cascade",
    )

    ngay = fields.Date(string="Ngày", required=True)

    gio_bat_dau = fields.Datetime(string="Giờ bắt đầu", required=True)
    gio_ket_thuc = fields.Datetime(string="Giờ kết thúc", required=True)

    so_gio_ot = fields.Float(
        string="Số giờ OT",
        compute="_compute_so_gio_ot",
        store=True,
        readonly=True,
    )

    he_so = fields.Float(string="Hệ số OT", default=2.0)

    ly_do = fields.Char(string="Lý do")
    ghi_chu = fields.Text(string="Ghi chú")

    trang_thai = fields.Selection(
        [
            ("nhap", "Nháp"),
            ("gui_duyet", "Gửi duyệt"),
            ("da_duyet", "Đã duyệt"),
            ("tu_choi", "Từ chối"),
            ("huy", "Hủy"),
        ],
        string="Trạng thái",
        default="nhap",
        required=True,
    )

    nguoi_duyet_id = fields.Many2one(
        "res.users",
        string="Người duyệt",
        ondelete="set null",
    )
    ngay_duyet = fields.Datetime(string="Ngày duyệt", readonly=True)

    _sql_constraints = [
        ("uniq_ot_nv_ngay_gio",
         "unique(nhan_vien_id, gio_bat_dau, gio_ket_thuc)",
         "Đơn OT này đã tồn tại (trùng nhân viên & thời gian)!"),
    ]

    @api.depends("gio_bat_dau", "gio_ket_thuc")
    def _compute_so_gio_ot(self):
        for r in self:
            if r.gio_bat_dau and r.gio_ket_thuc and r.gio_ket_thuc > r.gio_bat_dau:
                delta = (r.gio_ket_thuc - r.gio_bat_dau).total_seconds() / 3600.0
                r.so_gio_ot = max(delta, 0.0)
            else:
                r.so_gio_ot = 0.0

    @api.constrains("gio_bat_dau", "gio_ket_thuc")
    def _check_time(self):
        for r in self:
            if r.gio_bat_dau and r.gio_ket_thuc and r.gio_ket_thuc <= r.gio_bat_dau:
                raise ValidationError("Giờ kết thúc phải lớn hơn giờ bắt đầu!")

    @api.constrains("he_so")
    def _check_he_so(self):
        for r in self:
            if r.he_so <= 0:
                raise ValidationError("Hệ số OT phải > 0!")

    @api.constrains("ngay", "gio_bat_dau", "gio_ket_thuc")
    def _check_same_day(self):
        """
        Optional: ép OT nằm trong đúng 'ngày' đã chọn.
        Bạn có thể bỏ nếu muốn OT qua 0h.
        """
        for r in self:
            if not (r.ngay and r.gio_bat_dau and r.gio_ket_thuc):
                continue
            if r.gio_bat_dau.date() != r.ngay or r.gio_ket_thuc.date() != r.ngay:
                raise ValidationError("Giờ bắt đầu/kết thúc phải thuộc đúng ngày OT đã chọn!")

    # ---------------------------
    # Actions workflow
    # ---------------------------
    def action_gui_duyet(self):
        for r in self:
            if r.trang_thai != "nhap":
                continue
            r.trang_thai = "gui_duyet"

    def action_duyet(self):
        for r in self:
            if r.trang_thai != "gui_duyet":
                continue
            r.trang_thai = "da_duyet"
            r.nguoi_duyet_id = self.env.user.id
            r.ngay_duyet = fields.Datetime.now()

    def action_tu_choi(self):
        for r in self:
            if r.trang_thai != "gui_duyet":
                continue
            r.trang_thai = "tu_choi"
            r.nguoi_duyet_id = self.env.user.id
            r.ngay_duyet = fields.Datetime.now()

    def action_huy(self):
        for r in self:
            if r.trang_thai == "da_duyet":
                raise ValidationError("Đơn OT đã duyệt không thể hủy (nếu muốn, hãy xử lý theo quy trình).")
            r.trang_thai = "huy"

    def action_ve_nhap(self):
        for r in self:
            if r.trang_thai not in ("gui_duyet", "tu_choi"):
                continue
            r.trang_thai = "nhap"
            r.nguoi_duyet_id = False
            r.ngay_duyet = False

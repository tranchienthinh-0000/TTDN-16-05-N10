# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PhieuDieuChuyen(models.Model):
    _name = "phieu_dieu_chuyen"
    _description = "Phiếu Điều Chuyển Tài Sản"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # FIX: để dùng chatter
    _order = "ten_phieu desc"

    ten_phieu = fields.Char(
        string="Tên phiếu",
        required=True,
        copy=False,
        readonly=True,
        default="Mới",
        tracking=True,
    )
    tai_san = fields.Many2one(
        "tai_san",
        string="Tài sản",
        required=True,
        tracking=True,
    )

    vi_tri_hien_tai = fields.Many2one(
        "vi_tri",
        string="Vị trí hiện tại",
        related="tai_san.vi_tri_hien_tai_id",
        readonly=True,
        store=True,  # để kanban/search/group_by ổn định hơn
    )

    vi_tri_moi = fields.Many2one(
        "vi_tri",
        string="Vị trí mới",
        required=True,
        tracking=True,
    )

    # FIX: Datetime phải dùng fields.Datetime.now (fields.Date.context_today là date)
    ngay_dieu_chuyen = fields.Datetime(
        string="Ngày điều chuyển",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )

    trang_thai = fields.Selection(
        [
            ("nhap", "Nháp"),
            ("duyet", "Duyệt"),
            ("hoan_thanh", "Hoàn thành"),
            ("huy", "Hủy"),
        ],
        string="Trạng thái",
        default="nhap",
        tracking=True,
    )

    ghi_chu = fields.Text(string="Ghi chú")

    # Nếu bạn dùng sequence code = "phieu_dieu_chuyen" (như XML sequence bạn tạo)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("ten_phieu") in (False, "", "Mới", "New"):
                vals["ten_phieu"] = self.env["ir.sequence"].next_by_code("phieu_dieu_chuyen") or "Mới"
        return super().create(vals_list)

    def action_duyet(self):
        for rec in self:
            rec.write({"trang_thai": "duyet"})

    def action_hoan_thanh(self):
        for rec in self:
            if rec.trang_thai != "duyet":
                raise UserError(_("Chỉ có thể hoàn thành phiếu đã được duyệt."))

            self.env["lich_su_dieu_chuyen"].create(
                {
                    "tai_san_id": rec.tai_san.id,
                    "vi_tri_chuyen_id": rec.vi_tri_hien_tai.id,
                    "vi_tri_den_id": rec.vi_tri_moi.id,
                    "ngay_di_chuyen": rec.ngay_dieu_chuyen,
                    "ghi_chu": rec.ghi_chu,
                }
            )

            rec.tai_san.write({"vi_tri_hien_tai_id": rec.vi_tri_moi.id})
            rec.write({"trang_thai": "hoan_thanh"})

    def action_huy(self):
        for rec in self:
            if rec.trang_thai == "hoan_thanh":
                raise UserError(_("Không thể hủy phiếu đã hoàn thành."))
            rec.write({"trang_thai": "huy"})

    @api.constrains("vi_tri_moi", "tai_san")
    def _check_vi_tri(self):
        for rec in self:
            # tránh so sánh khi chưa chọn đủ
            if rec.vi_tri_moi and rec.vi_tri_hien_tai and rec.vi_tri_moi == rec.vi_tri_hien_tai:
                raise ValidationError(_("Vị trí mới phải khác vị trí hiện tại."))

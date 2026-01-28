# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PhieuBaoTri(models.Model):
    _name = "phieu_bao_tri"
    _description = "Phiếu bảo trì tài sản"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "ma_phieu_bao_tri desc"

    # ===== Core =====
    ma_phieu_bao_tri = fields.Char(
        string="Mã phiếu bảo trì",
        required=True,
        copy=False,
        readonly=True,
        default="New",
        tracking=True,
    )

    tai_san_id = fields.Many2one(
        comodel_name="tai_san",
        string="Tài sản",
        required=True,
        tracking=True,
        index=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Tiền tệ",
        default=lambda self: self.env.company.currency_id.id,
        required=True,
    )

    chi_phi = fields.Monetary(
        string="Chi phí",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )

    ghi_chu = fields.Text(string="Ghi chú")

    # ===== Dates =====
    ngay_bao_tri = fields.Datetime(string="Ngày bảo trì dự kiến", required=True, tracking=True)
    ngay_bao_tri_thuc_te = fields.Datetime(string="Ngày bảo trì thực tế", tracking=True)

    ngay_tra = fields.Datetime(string="Ngày trả dự kiến", required=True, tracking=True)
    ngay_tra_thuc_te = fields.Datetime(string="Ngày trả thực tế", tracking=True)

    # ===== State =====
    state = fields.Selection(
        [
            ("draft", "Nháp"),
            ("approved", "Đã duyệt"),
            ("done", "Hoàn thành"),
            ("cancel", "Hủy"),
        ],
        default="draft",
        string="Trạng thái",
        tracking=True,
        index=True,
    )

    # Link trực tiếp tới lịch sử (để update/unlink không cần search bằng nhiều điều kiện)
    lich_su_bao_tri_id = fields.Many2one(
        "lich_su_bao_tri",
        string="Dòng lịch sử bảo trì",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    # ===== Constraints =====
    @api.constrains("ngay_bao_tri", "ngay_tra")
    def _check_plan_dates(self):
        for r in self:
            if r.ngay_bao_tri and r.ngay_tra and r.ngay_tra < r.ngay_bao_tri:
                raise ValidationError(_("Ngày trả dự kiến phải lớn hơn hoặc bằng ngày bảo trì dự kiến."))

    @api.constrains("ngay_bao_tri_thuc_te", "ngay_tra_thuc_te")
    def _check_actual_dates(self):
        for r in self:
            if r.ngay_bao_tri_thuc_te and r.ngay_tra_thuc_te and r.ngay_tra_thuc_te < r.ngay_bao_tri_thuc_te:
                raise ValidationError(_("Ngày trả thực tế phải lớn hơn hoặc bằng ngày bảo trì thực tế."))

    # ===== Create sequence =====
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("ma_phieu_bao_tri", "New") in (False, "", "New"):
                vals["ma_phieu_bao_tri"] = self.env["ir.sequence"].next_by_code("phieu_bao_tri") or "New"
        return super().create(vals_list)

    # ===== Actions =====
    def action_approve(self):
        for r in self:
            if r.state != "draft":
                continue

            # tạo lịch sử bảo trì 1 lần và lưu link
            hist = self.env["lich_su_bao_tri"].create({
                "ma_lich_su_bao_tri": self.env["ir.sequence"].next_by_code("lich_su_bao_tri") or "New",
                "tai_san_id": r.tai_san_id.id,
                "ngay_bao_tri": r.ngay_bao_tri,
                "ngay_tra": r.ngay_tra,
                "chi_phi": r.chi_phi,
                "ghi_chu": r.ghi_chu,
            })

            r.write({
                "state": "approved",
                "lich_su_bao_tri_id": hist.id,
            })

    def action_done(self):
        for r in self:
            if r.state != "approved":
                continue

            if not r.ngay_bao_tri_thuc_te or not r.ngay_tra_thuc_te:
                raise UserError(_("Vui lòng nhập đầy đủ Ngày bảo trì thực tế và Ngày trả thực tế trước khi hoàn thành."))

            # cập nhật dòng lịch sử nếu có
            if r.lich_su_bao_tri_id:
                r.lich_su_bao_tri_id.write({
                    "ngay_bao_tri": r.ngay_bao_tri_thuc_te,
                    "ngay_tra": r.ngay_tra_thuc_te,
                    "chi_phi": r.chi_phi,
                    "ghi_chu": r.ghi_chu,
                })

            r.write({"state": "done"})

    def action_cancel(self):
        for r in self:
            if r.state not in ("draft", "approved"):
                continue

            # nếu đã tạo lịch sử lúc duyệt thì xóa lịch sử khi hủy (đúng theo logic bạn đang làm)
            if r.lich_su_bao_tri_id:
                r.lich_su_bao_tri_id.unlink()
                r.lich_su_bao_tri_id = False

            r.write({"state": "cancel"})

    def action_reset_to_draft(self):
        for r in self:
            if r.state in ("approved", "cancel"):
                r.write({"state": "draft"})

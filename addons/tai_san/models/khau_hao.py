# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class KhauHao(models.Model):
    _name = "khau_hao"
    _description = "Bảng chứa thông tin khấu hao"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "ma_khau_hao"

    _sql_constraints = [
        ("ma_khau_hao_unique", "unique(ma_khau_hao)", "Mã khấu hao phải là duy nhất!"),
    ]

    ma_khau_hao = fields.Char(
        string="Mã khấu hao",
        required=True,
        copy=False,
        readonly=True,
        default="New",
        tracking=True,
    )

    ngay_khau_hao = fields.Date(string="Ngày khấu hao", required=True, tracking=True)

    currency_id = fields.Many2one(
        "res.currency",
        string="Tiền tệ",
        default=lambda self: self.env.company.currency_id.id,
        required=True,
    )

    gia_tri_khau_hao = fields.Monetary(
        string="Giá trị khấu hao",
        required=True,
        currency_field="currency_id",
        tracking=True,
    )

    ghi_chu = fields.Char(string="Ghi chú")

    tai_san_id = fields.Many2one(
        comodel_name="tai_san",
        string="Tài sản",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    # -----------------------------
    # Helpers
    # -----------------------------
    def _get_gia_tri_hien_tai(self, tai_san):
        return tai_san.gia_tri_hien_tai or tai_san.gia_tien_mua or 0

    def _apply_khau_hao(self, tai_san, amount):
        """Trừ khấu hao vào tài sản."""
        if amount <= 0:
            raise ValidationError("Giá trị khấu hao phải lớn hơn 0!")
        gia_tri_hien_tai = self._get_gia_tri_hien_tai(tai_san)
        if amount > gia_tri_hien_tai:
            raise ValidationError("Giá trị khấu hao không thể lớn hơn giá trị hiện tại của tài sản!")
        tai_san.write({"gia_tri_hien_tai": gia_tri_hien_tai - amount})

    def _rollback_khau_hao(self, tai_san, amount):
        """Hoàn khấu hao (khi sửa/xóa)."""
        if amount and amount > 0:
            gia_tri_hien_tai = self._get_gia_tri_hien_tai(tai_san)
            tai_san.write({"gia_tri_hien_tai": gia_tri_hien_tai + amount})

    # -----------------------------
    # ORM overrides
    # -----------------------------
    @api.model
    def create(self, vals):
        if vals.get("ma_khau_hao", "New") == "New":
            vals["ma_khau_hao"] = self.env["ir.sequence"].next_by_code("khau_hao") or "New"

        rec = super().create(vals)

        # Apply depreciation to asset after record created
        if rec.tai_san_id:
            rec._apply_khau_hao(rec.tai_san_id, rec.gia_tri_khau_hao)

        return rec

    def write(self, vals):
        """
        Nếu sửa gia_tri_khau_hao hoặc đổi tai_san_id:
        - hoàn lại giá trị cũ
        - áp giá trị mới
        """
        for rec in self:
            old_tai_san = rec.tai_san_id
            old_amount = rec.gia_tri_khau_hao

            res = super(KhauHao, rec).write(vals)

            new_tai_san = rec.tai_san_id
            new_amount = rec.gia_tri_khau_hao

            # rollback old
            if old_tai_san:
                rec._rollback_khau_hao(old_tai_san, old_amount)

            # apply new
            if new_tai_san:
                rec._apply_khau_hao(new_tai_san, new_amount)

        return True

    def unlink(self):
        # rollback before delete
        for rec in self:
            if rec.tai_san_id:
                rec._rollback_khau_hao(rec.tai_san_id, rec.gia_tri_khau_hao)
        return super().unlink()

    # -----------------------------
    # Constraints
    # -----------------------------
    @api.constrains("gia_tri_khau_hao", "tai_san_id")
    def _check_gia_tri_khau_hao(self):
        for record in self:
            if record.gia_tri_khau_hao <= 0:
                raise ValidationError("Giá trị khấu hao phải lớn hơn 0!")
            if record.tai_san_id:
                gia_tri_hien_tai = record._get_gia_tri_hien_tai(record.tai_san_id)
                if record.gia_tri_khau_hao > gia_tri_hien_tai:
                    raise ValidationError("Giá trị khấu hao không thể lớn hơn giá trị hiện tại của tài sản!")

# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CapPhatThuHoi(models.Model):
    _name = "cap_phat_thu_hoi"
    _description = "Cấp phát / Thu hồi"
    _order = "ngay_ban_giao desc, id desc"

    tai_san_id = fields.Many2one(
        "quan_ly_ho_so_tai_san", string="Tài sản", required=True, ondelete="cascade"
    )
    nhan_vien_id = fields.Many2one(
        "nhan_vien", string="Nhân viên nhận", required=True, ondelete="restrict"
    )

    ngay_ban_giao = fields.Date(string="Ngày bàn giao", required=True, default=fields.Date.today)
    nguoi_ban_giao_id = fields.Many2one(
        "res.users", string="Người bàn giao", default=lambda self: self.env.user
    )

    ngay_thu_hoi = fields.Date(string="Ngày thu hồi")
    nguoi_thu_hoi_id = fields.Many2one("res.users", string="Người thu hồi")

    trang_thai = fields.Selection(
        [
            ("dang_giu", "Đang giữ"),
            ("da_thu_hoi", "Đã thu hồi"),
        ],
        string="Trạng thái",
        default="dang_giu",
        required=True,
        index=True,
    )

    ghi_chu = fields.Text(string="Ghi chú")

    @api.constrains("ngay_thu_hoi", "ngay_ban_giao")
    def _check_dates(self):
        for r in self:
            if r.ngay_thu_hoi and r.ngay_ban_giao and r.ngay_thu_hoi < r.ngay_ban_giao:
                raise ValidationError("Ngày thu hồi không được nhỏ hơn ngày bàn giao!")

    @api.constrains("tai_san_id", "trang_thai")
    def _check_one_active_allocation(self):
        for r in self:
            if r.trang_thai == "dang_giu" and r.tai_san_id:
                dup = self.search([
                    ("id", "!=", r.id),
                    ("tai_san_id", "=", r.tai_san_id.id),
                    ("trang_thai", "=", "dang_giu"),
                ], limit=1)
                if dup:
                    raise ValidationError("Tài sản này đang được cấp phát cho người khác (chưa thu hồi)!")

    def _dong_bo_trang_thai_tai_san(self):
        """Đồng bộ trạng thái hồ sơ tài sản theo tình trạng cấp phát."""
        for r in self:
            if not r.tai_san_id:
                continue

            if r.trang_thai == "dang_giu":
                # đang giữ => tài sản đang sử dụng
                r.tai_san_id.write({"trang_thai": "dang_su_dung"})
            elif r.trang_thai == "da_thu_hoi":
                # đã thu hồi => nếu tài sản đang sử dụng thì về tồn kho
                if r.tai_san_id.trang_thai == "dang_su_dung":
                    r.tai_san_id.write({"trang_thai": "ton_kho"})

    @api.model
    def create(self, vals):
        rec = super().create(vals)

        # Nếu tạo bản ghi đang giữ => update trạng thái tài sản
        if rec.trang_thai == "dang_giu":
            rec._dong_bo_trang_thai_tai_san()

        # Nếu tạo bản ghi đã thu hồi (hiếm) => tự set người/ngày thu hồi nếu chưa có
        if rec.trang_thai == "da_thu_hoi":
            if not rec.ngay_thu_hoi:
                rec.ngay_thu_hoi = fields.Date.today()
            if not rec.nguoi_thu_hoi_id:
                rec.nguoi_thu_hoi_id = self.env.user.id
            rec._dong_bo_trang_thai_tai_san()

        return rec

    def write(self, vals):
        res = super().write(vals)

        # Nếu chuyển sang đã thu hồi mà chưa set ngày/người thì tự set
        if vals.get("trang_thai") == "da_thu_hoi":
            for r in self:
                update = {}
                if not r.ngay_thu_hoi:
                    update["ngay_thu_hoi"] = fields.Date.today()
                if not r.nguoi_thu_hoi_id:
                    update["nguoi_thu_hoi_id"] = self.env.user.id
                if update:
                    super(CapPhatThuHoi, r).write(update)

        # Đồng bộ trạng thái tài sản nếu có thay đổi liên quan
        if set(vals.keys()) & {"trang_thai", "tai_san_id"}:
            for r in self:
                r._dong_bo_trang_thai_tai_san()

        return res

    def action_thu_hoi(self):
        for r in self:
            if r.trang_thai != "dang_giu":
                continue
            r.write({
                "trang_thai": "da_thu_hoi",
                "ngay_thu_hoi": fields.Date.today(),
                "nguoi_thu_hoi_id": self.env.user.id,
            })
        return True


class NhanVienInherit(models.Model):
    _inherit = "nhan_vien"

    tai_san_dang_giu_ids = fields.One2many(
        "cap_phat_thu_hoi",
        "nhan_vien_id",
        string="Tài sản cấp phát"
    )

    def write(self, vals):
        # Chặn nghỉ việc nếu còn đang giữ tài sản
        if vals.get("trang_thai") == "da_nghi":
            for nv in self:
                con = self.env["cap_phat_thu_hoi"].search_count([
                    ("nhan_vien_id", "=", nv.id),
                    ("trang_thai", "=", "dang_giu"),
                ])
                if con:
                    raise ValidationError("Nhân viên chưa trả hết tài sản. Vui lòng thu hồi trước khi nghỉ việc!")
        return super().write(vals)

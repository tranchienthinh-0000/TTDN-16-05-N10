# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class TaiSan(models.Model):
    _name = "tai_san"
    _description = "Tài sản"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "ma_tai_san desc"
    _rec_name = "ten_tai_san"

    _sql_constraints = [
        ("ma_tai_san_unique", "unique(ma_tai_san)", "Mã tài sản phải là duy nhất!"),
        ("so_serial_unique", "unique(so_serial)", "Serial phải là duy nhất!"),
    ]

    # =========================================================
    # BASIC: ARCHIVE
    # =========================================================
    active = fields.Boolean(default=True, tracking=True)

    # =========================================================
    # FIELDS
    # =========================================================
    currency_id = fields.Many2one(
        "res.currency",
        string="Tiền tệ",
        default=lambda self: self.env.company.currency_id.id,
        required=True,
    )

    ma_tai_san = fields.Char(
        string="Mã tài sản",
        required=True,
        copy=False,
        default="New",
        index=True,
        tracking=True,
    )
    so_serial = fields.Char(
        string="Serial",
        required=True,
        copy=False,
        default="New",
        index=True,
        tracking=True,
    )
    ten_tai_san = fields.Char(string="Tên tài sản", required=True, index=True, tracking=True)

    ngay_mua = fields.Date(string="Ngày mua", tracking=True)
    ngay_het_han_bao_hanh = fields.Date(string="Ngày hết hạn bảo hành", tracking=True)

    gia_tien_mua = fields.Monetary(string="Giá mua", currency_field="currency_id", tracking=True)
    gia_tri_hien_tai = fields.Monetary(string="Giá trị hiện tại", currency_field="currency_id", tracking=True)

    TRANG_THAI = [
        ("CatGiu", "Lưu trữ"),
        ("Muon", "Đang mượn"),
        ("BaoTri", "Bảo trì"),
        ("DaThanhLy", "Đã thanh lý"),
    ]
    trang_thai = fields.Selection(
        selection=TRANG_THAI,
        string="Trạng thái",
        default="CatGiu",
        required=True,
        index=True,
        tracking=True,
    )

    loai_tai_san_id = fields.Many2one("loai_tai_san", string="Loại tài sản", required=True, tracking=True)
    vi_tri_hien_tai_id = fields.Many2one("vi_tri", string="Vị trí hiện tại", tracking=True)
    nha_cung_cap_id = fields.Many2one("nha_cung_cap", string="Nhà cung cấp", tracking=True)

    nguoi_su_dung_id = fields.Many2one("nhan_vien", string="Người đang sử dụng", tracking=True)

    thanh_ly_id = fields.Many2one("thanh_ly", string="Phiếu thanh lý", readonly=True, tracking=True)

    # History relations
    lich_su_su_dung_ids = fields.One2many("lich_su_su_dung", "tai_san_id", string="Lịch sử sử dụng", readonly=True)
    lich_su_bao_tri_ids = fields.One2many("lich_su_bao_tri", "tai_san_id", string="Lịch sử bảo trì", readonly=True)
    khau_hao_ids = fields.One2many("khau_hao", "tai_san_id", string="Khấu hao", readonly=True)
    lich_su_dieu_chuyen_ids = fields.One2many("lich_su_dieu_chuyen", "tai_san_id", string="Lịch sử điều chuyển", readonly=True)

    # =========================================================
    # CREATE: SEQUENCE + DEFAULT CURRENT VALUE
    # =========================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("ma_tai_san", "New") in (False, "", "New"):
                vals["ma_tai_san"] = self.env["ir.sequence"].next_by_code("tai_san") or "New"

            if vals.get("so_serial", "New") in (False, "", "New"):
                vals["so_serial"] = self.env["ir.sequence"].next_by_code("tai_san_serial") or "New"

            if not vals.get("gia_tri_hien_tai") and vals.get("gia_tien_mua"):
                vals["gia_tri_hien_tai"] = vals["gia_tien_mua"]

        return super().create(vals_list)

    # =========================================================
    # BUSINESS CONSTRAINTS
    # =========================================================
    @api.constrains("trang_thai", "nguoi_su_dung_id")
    def _check_muon_phai_co_nguoi(self):
        for r in self:
            if r.trang_thai == "Muon" and not r.nguoi_su_dung_id:
                raise ValidationError(_("Tài sản đang 'Đang mượn' nhưng chưa có 'Người đang sử dụng'."))

            if r.trang_thai in ("CatGiu", "BaoTri", "DaThanhLy") and r.nguoi_su_dung_id:
                raise ValidationError(_("Tài sản không ở trạng thái 'Đang mượn' nên không được gắn người sử dụng."))

    @api.constrains("trang_thai", "thanh_ly_id")
    def _check_thanh_ly_state(self):
        for r in self:
            if r.trang_thai == "DaThanhLy" and not r.thanh_ly_id:
                raise ValidationError(_("Tài sản 'Đã thanh lý' nhưng chưa có 'Phiếu thanh lý'."))

            if r.thanh_ly_id and r.trang_thai != "DaThanhLy":
                raise ValidationError(_("Tài sản đã có phiếu thanh lý thì trạng thái phải là 'Đã thanh lý'."))

    # =========================================================
    # DELETE POLICY: NEVER HARD DELETE IF HAS HISTORY
    # =========================================================
    def unlink(self):
        for r in self:
            # Nếu đã có lịch sử dùng/bảo trì/điều chuyển/khấu hao thì cấm xóa cứng
            if r.lich_su_su_dung_ids or r.lich_su_bao_tri_ids or r.lich_su_dieu_chuyen_ids or r.khau_hao_ids:
                raise UserError(_(
                    "Không thể xóa Tài sản vì đã phát sinh lịch sử.\n"
                    "Bạn hãy dùng 'Lưu trữ (Archive)' để ẩn tài sản thay vì xóa."
                ))
        return super().unlink()

    # =========================================================
    # ACTIONS
    # =========================================================
    def action_open_thanh_ly(self):
        self.ensure_one()
        return {
            "name": _("Phiếu thanh lý"),
            "type": "ir.actions.act_window",
            "res_model": "thanh_ly",
            "view_mode": "tree,form",
            "domain": [("tai_san_id", "=", self.id)],
            "context": {"default_tai_san_id": self.id},
        }

    def action_dieu_chuyen_tai_san(self):
        self.ensure_one()
        return {
            "name": _("Điều chuyển tài sản"),
            "type": "ir.actions.act_window",
            "res_model": "lich_su_dieu_chuyen",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_tai_san_id": self.id,
                "default_vi_tri_chuyen_id": self.vi_tri_hien_tai_id.id,
            },
        }

    def action_set_cat_giu(self):
        for r in self:
            r.write({"trang_thai": "CatGiu", "nguoi_su_dung_id": False})

    def action_set_bao_tri(self):
        for r in self:
            r.write({"trang_thai": "BaoTri", "nguoi_su_dung_id": False})

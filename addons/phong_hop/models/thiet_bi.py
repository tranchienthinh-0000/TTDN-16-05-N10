# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError


class ThietBi(models.Model):
    _name = "thiet_bi"
    _description = "Quản lý thiết bị phòng họp"
    _order = "vi_tri_hien_tai asc, phong_id asc, trang_thai asc, name asc"

    name = fields.Char(string="Tên thiết bị", required=True)

    loai_thiet_bi = fields.Selection([
        ('may_chieu', 'Máy chiếu'),
        ('micro', 'Micro'),
        ('loa', 'Loa'),
        ('dieu_hoa', 'Điều hòa'),
        ('may_tinh', 'Máy tính'),
        ('khac', 'Khác'),
    ], string="Loại thiết bị", required=True)

    vi_tri_hien_tai = fields.Selection([
        ("kho", "Kho"),
        ("phong", "Trong phòng"),
    ], string="Vị trí hiện tại", default="kho", required=True)

    phong_hien_tai_id = fields.Many2one(
        "quan_ly_phong_hop",
        string="Phòng hiện tại",
        ondelete="set null",
    )

    # Tương thích ngược cho One2many inverse_name='phong_id'
    phong_id = fields.Many2one(
        "quan_ly_phong_hop",
        string="Phòng (tương thích)",
        related="phong_hien_tai_id",
        store=True,
        readonly=True,
    )

    trang_thai = fields.Selection([
        ('dang_su_dung', 'Đang sử dụng'),
        ('san_sang', 'Sẵn sàng'),
        ('can_bao_tri', 'Cần bảo trì'),
        ('hong', 'Hỏng'),
    ], string="Trạng thái", default="san_sang", required=True)

    mo_ta = fields.Text(string="Mô tả")

    # =========================
    # LIÊN KẾT TÀI SẢN
    # =========================
    tai_san_id = fields.Many2one(
        "tai_san",
        string="Tài sản liên kết",
        ondelete="set null",
        domain="[('active','=',True), ('trang_thai','!=','DaThanhLy')]",
    )

    # Hiển thị thêm thông tin lấy từ tài sản (readonly)
    loai_tai_san_id = fields.Many2one(
        "loai_tai_san",
        string="Loại tài sản",
        related="tai_san_id.loai_tai_san_id",
        store=True,
        readonly=True,
    )

    ma_tai_san = fields.Char(string="Mã tài sản", related="tai_san_id.ma_tai_san", store=True, readonly=True)
    so_serial = fields.Char(string="Serial", related="tai_san_id.so_serial", store=True, readonly=True)
    trang_thai_tai_san = fields.Selection(string="Trạng thái tài sản", related="tai_san_id.trang_thai", store=True, readonly=True)

    # =========================
    # VALIDATION
    # =========================
    @api.constrains("vi_tri_hien_tai", "phong_hien_tai_id")
    def _check_location(self):
        for r in self:
            if r.vi_tri_hien_tai == "kho" and r.phong_hien_tai_id:
                raise ValidationError(_("Thiết bị ở Kho thì không được gắn Phòng hiện tại."))
            if r.vi_tri_hien_tai == "phong" and not r.phong_hien_tai_id:
                raise ValidationError(_("Thiết bị ở Trong phòng thì phải có Phòng hiện tại."))

    @api.constrains("tai_san_id")
    def _check_unique_tai_san(self):
        """
        Không cho 1 tài sản gán cho nhiều thiết bị phòng họp.
        (Dùng python constraint để tránh lỗi unique NULL/đa bản ghi)
        """
        for r in self:
            if not r.tai_san_id:
                continue
            other = self.search([
                ("id", "!=", r.id),
                ("tai_san_id", "=", r.tai_san_id.id),
            ], limit=1)
            if other:
                raise ValidationError(_(
                    "Tài sản này đã được liên kết với thiết bị khác:\n"
                    "- Thiết bị: %s\n"
                    "- Tài sản: %s"
                ) % (other.display_name, r.tai_san_id.display_name))

    # =========================
    # SERVICE METHODS
    # =========================
    @api.model
    def dua_ve_kho(self, thiet_bi_records):
        if not thiet_bi_records:
            return True
        thiet_bi_records.write({
            "vi_tri_hien_tai": "kho",
            "phong_hien_tai_id": False,
            "trang_thai": "san_sang",
        })
        return True

    @api.model
    def dua_vao_phong(self, thiet_bi_records, phong_id):
        if not thiet_bi_records:
            return True
        thiet_bi_records.write({
            "vi_tri_hien_tai": "phong",
            "phong_hien_tai_id": phong_id,
            "trang_thai": "dang_su_dung",
        })
        return True

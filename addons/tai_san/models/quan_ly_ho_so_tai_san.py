# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class QuanLyHoSoTaiSan(models.Model):
    _name = "quan_ly_ho_so_tai_san"
    _description = "Quản lý hồ sơ tài sản"
    _rec_name = "ten"
    _order = "ma_tai_san desc, id desc"

    ma_tai_san = fields.Char(
        string="Mã tài sản",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default="/",
    )
    ten = fields.Char(string="Tên tài sản", required=True)

    phan_loai = fields.Selection(
        [
            ("may_tinh", "Máy tính"),
            ("noi_that", "Nội thất"),
            ("xe_co", "Xe cộ"),
            ("thiet_bi_vp", "Thiết bị văn phòng"),
        ],
        string="Phân loại",
        required=True,
        default="may_tinh",
        index=True,
    )

    barcode_qr = fields.Char(string="Mã Barcode/QR", index=True)
    serial_number = fields.Char(string="Serial Number", index=True)

    ngay_mua = fields.Date(string="Ngày mua")
    nguyen_gia = fields.Float(string="Giá trị nguyên giá", default=0.0)
    nha_cung_cap = fields.Char(string="Nhà cung cấp")

    trang_thai = fields.Selection(
        [
            ("ton_kho", "Tồn kho"),
            ("dang_su_dung", "Đang sử dụng"),
            ("bao_tri", "Đang sửa chữa"),
            ("thanh_ly", "Thanh lý"),
        ],
        string="Trạng thái",
        default="ton_kho",
        required=True,
        index=True,
    )

    cap_phat_ids = fields.One2many(
        "cap_phat_thu_hoi",
        "tai_san_id",
        string="Lịch sử cấp phát/thu hồi"
    )

    nhan_vien_dang_giu_id = fields.Many2one(
        "nhan_vien",
        string="Nhân viên đang giữ",
        compute="_compute_nhan_vien_dang_giu",
        store=False,
        readonly=True,
    )
    bao_tri_ids = fields.One2many(
        "bao_tri_sua_chua",
        "tai_san_id",
        string="Bảo trì / Sửa chữa"
    )

    khau_hao_ids = fields.One2many(
        "khau_hao",
        "tai_san_id",
        string="Khấu hao"
    )


    ghi_chu = fields.Text(string="Ghi chú")

    _sql_constraints = [
        ("uniq_ma_tai_san", "unique(ma_tai_san)", "Mã tài sản đã tồn tại!"),
    ]

    # ✅ BỎ cap_phat_ids.id (Odoo cấm depends vào id)
    @api.depends("cap_phat_ids.trang_thai", "cap_phat_ids.ngay_ban_giao")
    def _compute_nhan_vien_dang_giu(self):
        for ts in self:
            dang_giu = ts.cap_phat_ids.filtered(lambda r: r.trang_thai == "dang_giu")
            if dang_giu:
                # lấy dòng mới nhất: ưu tiên ngày_ban_giao, nếu trùng/thiếu thì dùng id để ổn định
                dong_moi_nhat = dang_giu.sorted(
                    key=lambda r: (r.ngay_ban_giao or fields.Date.from_string("1900-01-01"), r.id),
                    reverse=True
                )[:1]
                ts.nhan_vien_dang_giu_id = dong_moi_nhat.nhan_vien_id.id
            else:
                ts.nhan_vien_dang_giu_id = False

    @api.constrains("nguyen_gia")
    def _check_nguyen_gia(self):
        for r in self:
            if r.nguyen_gia < 0:
                raise ValidationError("Giá trị nguyên giá không được âm!")

    def _strip_vals(self, vals, keys):
        for k in keys:
            if vals.get(k) and isinstance(vals.get(k), str):
                vals[k] = vals[k].strip()
        return vals

    @api.model
    def create(self, vals):
        vals = self._strip_vals(vals, ["ten", "barcode_qr", "serial_number", "nha_cung_cap"])
        if vals.get("ma_tai_san", "/") == "/":
            vals["ma_tai_san"] = self.env["ir.sequence"].next_by_code("tai_san") or "/"
        return super().create(vals)

    def write(self, vals):
        vals = self._strip_vals(vals, ["ten", "barcode_qr", "serial_number", "nha_cung_cap"])
        return super().write(vals)

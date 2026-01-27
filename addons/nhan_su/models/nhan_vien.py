# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class NhanVien(models.Model):
    _name = "nhan_vien"
    _description = "Nhân viên"
    _rec_name = "ma_dinh_danh"
    _order = "ma_dinh_danh asc, ngay_sinh asc"

    # Thông tin cơ bản
    ma_dinh_danh = fields.Char(string="Mã định danh", required=True, index=True)
    ho_ten = fields.Char(string="Họ tên", required=True)

    ngay_sinh = fields.Date(string="Ngày sinh")
    que_quan = fields.Char(string="Quê quán")
    dia_chi = fields.Char(string="Địa chỉ")
    email = fields.Char(string="Email")
    so_dien_thoai = fields.Char(string="Số điện thoại")
    so_bhxh = fields.Char(string="Số BHXH")

    # Trạng thái nhân viên
    active = fields.Boolean(default=True)
    trang_thai = fields.Selection(
        [("dang_lam", "Đang làm"), ("da_nghi", "Đã nghỉ")],
        string="Trạng thái",
        default="dang_lam",
        required=True,
    )
    ngay_nghi_viec = fields.Date(string="Ngày nghỉ việc")

    # Quản lý trực tiếp
    quan_ly_id = fields.Many2one(
        "nhan_vien",
        string="Quản lý trực tiếp",
        ondelete="set null"
    )

    # Phòng ban / Chức vụ
    phong_ban_id = fields.Many2one("phong_ban", string="Phòng ban", ondelete="set null")
    chuc_vu_id = fields.Many2one("chuc_vu", string="Chức vụ", ondelete="set null")

    # Quan hệ phụ
    lich_su_cong_tac_ids = fields.One2many("lich_su_cong_tac", "nhan_vien_id", string="Lịch sử công tác")
    chung_chi_ids = fields.One2many("chung_chi", "nhan_vien_id", string="Chứng chỉ")
    cham_cong_ids = fields.One2many("cham_cong", "nhan_vien_id", string="Chấm công")

    # Hợp đồng
    hop_dong_ids = fields.One2many("hop_dong", "nhan_vien_id", string="Hợp đồng")

    hop_dong_hien_hanh_id = fields.Many2one(
        "hop_dong",
        string="Hợp đồng hiện hành",
        compute="_compute_hop_dong_hien_hanh",
        store=False,
        readonly=True,
    )

    # Lương hiện hành (lấy từ hợp đồng hiện hành) - payroll sẽ dùng cái này
    luong = fields.Float(
        string="Lương (hiện hành)",
        compute="_compute_luong_hien_hanh",
        store=False,
        readonly=True,
    )

    _sql_constraints = [
        ("ma_dinh_danh_unique", "unique(ma_dinh_danh)", "Mã định danh đã tồn tại!"),
    ]

    # -----------------------------
    # Compute: hợp đồng hiện hành
    # -----------------------------
    @api.depends(
        "hop_dong_ids.trang_thai",
        "hop_dong_ids.ngay_bat_dau",
        "hop_dong_ids.ngay_ket_thuc",
        "hop_dong_ids.luong_cung_thang",  # ✅ thêm để đổi lương hợp đồng thì NV cập nhật
    )
    def _compute_hop_dong_hien_hanh(self):
        today = fields.Date.today()
        for nv in self:
            # lọc hợp đồng hiệu lực + nằm trong khoảng thời gian
            hds = nv.hop_dong_ids.filtered(lambda r:
                r.trang_thai == "hieu_luc"
                and r.ngay_bat_dau
                and r.ngay_bat_dau <= today
                and (not r.ngay_ket_thuc or r.ngay_ket_thuc >= today)
            )

            # ưu tiên hợp đồng có ngày bắt đầu gần nhất
            hds = hds.sorted(
                lambda r: (r.ngay_bat_dau or fields.Date.from_string("1900-01-01")),
                reverse=True
            )

            nv.hop_dong_hien_hanh_id = hds[:1].id if hds else False

    @api.depends("hop_dong_hien_hanh_id", "hop_dong_hien_hanh_id.luong_cung_thang")
    def _compute_luong_hien_hanh(self):
        for nv in self:
            nv.luong = nv.hop_dong_hien_hanh_id.luong_cung_thang if nv.hop_dong_hien_hanh_id else 0.0

    # -----------------------------
    # Validate dữ liệu
    # -----------------------------
    @api.constrains("ma_dinh_danh", "ho_ten")
    def _check_required_not_whitespace(self):
        for r in self:
            if r.ma_dinh_danh and not r.ma_dinh_danh.strip():
                raise ValidationError("Mã định danh không được để trống hoặc chỉ chứa khoảng trắng!")
            if r.ho_ten and not r.ho_ten.strip():
                raise ValidationError("Họ tên không được để trống hoặc chỉ chứa khoảng trắng!")

    @api.constrains("email")
    def _check_email(self):
        for r in self:
            if r.email:
                e = r.email.strip()
                if "@" not in e or " " in e:
                    raise ValidationError("Email không hợp lệ!")

    @api.constrains("so_dien_thoai")
    def _check_phone(self):
        for r in self:
            if r.so_dien_thoai:
                p = r.so_dien_thoai.strip()
                if " " in p or any(ch.isalpha() for ch in p):
                    raise ValidationError("Số điện thoại không hợp lệ!")

    @api.constrains("trang_thai", "ngay_nghi_viec")
    def _check_nghi_viec(self):
        for r in self:
            if r.trang_thai == "da_nghi" and not r.ngay_nghi_viec:
                raise ValidationError("Nhân viên đã nghỉ việc thì phải có 'Ngày nghỉ việc'!")
            if r.trang_thai == "dang_lam" and r.ngay_nghi_viec:
                raise ValidationError("Nhân viên đang làm thì không được có 'Ngày nghỉ việc'!")

    # -----------------------------
    # Chuẩn hoá input (strip)
    # -----------------------------
    def _strip_vals(self, vals, keys):
        for k in keys:
            if vals.get(k) and isinstance(vals.get(k), str):
                vals[k] = vals[k].strip()
        return vals

    @api.model
    def create(self, vals):
        vals = self._strip_vals(
            vals,
            ["ma_dinh_danh", "ho_ten", "email", "so_dien_thoai", "so_bhxh", "que_quan", "dia_chi"]
        )
        return super().create(vals)

    def write(self, vals):
        vals = self._strip_vals(
            vals,
            ["ma_dinh_danh", "ho_ten", "email", "so_dien_thoai", "so_bhxh", "que_quan", "dia_chi"]
        )
        return super().write(vals)

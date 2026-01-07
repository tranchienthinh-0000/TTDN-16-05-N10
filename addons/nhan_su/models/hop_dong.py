# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HopDong(models.Model):
    _name = "hop_dong"
    _description = "Hợp đồng"
    _order = "ngay_bat_dau desc, id desc"

    nhan_vien_id = fields.Many2one(
        "nhan_vien",
        string="Nhân viên",
        required=True,
        ondelete="cascade",
    )

    loai_hop_dong = fields.Selection(
        [
            ("thu_viec", "Thử việc"),
            ("chinh_thuc", "Chính thức"),
            ("thoi_vu", "Thời vụ"),
        ],
        string="Loại hợp đồng",
        required=True,
        default="thu_viec",
    )

    ngay_bat_dau = fields.Date(string="Ngày bắt đầu", required=True)
    ngay_ket_thuc = fields.Date(string="Ngày kết thúc")

    luong_cung_thang = fields.Float(string="Lương cứng/tháng", default=0.0)

    so_ngay_cong_chuan = fields.Integer(string="Số ngày công chuẩn/tháng", default=22)
    so_gio_mot_ngay = fields.Float(string="Số giờ/1 ngày", default=8.0)

    trang_thai = fields.Selection(
        [
            ("nhap", "Nháp"),
            ("hieu_luc", "Hiệu lực"),
            ("het_hieu_luc", "Hết hiệu lực"),
        ],
        string="Trạng thái",
        default="nhap",
        required=True,
    )

    ghi_chu = fields.Text(string="Ghi chú")

    phu_cap_ids = fields.One2many(
        "phu_cap_hop_dong",
        "hop_dong_id",
        string="Phụ cấp cố định",
    )

    _sql_constraints = [
        ("check_dates",
         "CHECK(ngay_ket_thuc IS NULL OR ngay_ket_thuc >= ngay_bat_dau)",
         "Ngày kết thúc không được nhỏ hơn ngày bắt đầu!"),
    ]

    @api.constrains("luong_cung_thang", "so_ngay_cong_chuan", "so_gio_mot_ngay")
    def _check_thong_so(self):
        for r in self:
            if r.luong_cung_thang < 0:
                raise ValidationError("Lương cứng/tháng không được âm!")
            if r.so_ngay_cong_chuan <= 0:
                raise ValidationError("Số ngày công chuẩn phải > 0!")
            if r.so_gio_mot_ngay <= 0:
                raise ValidationError("Số giờ/1 ngày phải > 0!")

    @api.constrains("nhan_vien_id", "ngay_bat_dau", "ngay_ket_thuc", "trang_thai")
    def _check_overlap_hieu_luc(self):
        """
        Không cho 2 hợp đồng 'hiệu lực' bị chồng thời gian cho cùng 1 nhân viên.
        (Bạn có thể nới rule này nếu muốn)
        """
        for r in self:
            if r.trang_thai != "hieu_luc" or not r.nhan_vien_id or not r.ngay_bat_dau:
                continue

            start = r.ngay_bat_dau
            end = r.ngay_ket_thuc or fields.Date.max

            domain = [
                ("id", "!=", r.id),
                ("nhan_vien_id", "=", r.nhan_vien_id.id),
                ("trang_thai", "=", "hieu_luc"),
                ("ngay_bat_dau", "<=", end),
                "|",
                ("ngay_ket_thuc", "=", False),
                ("ngay_ket_thuc", ">=", start),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError("Nhân viên đang có hợp đồng hiệu lực bị chồng thời gian!")

    def _tao_phu_cap_tu_chuc_vu(self):
        """
        Copy phụ cấp mặc định từ chức vụ của nhân viên vào hợp đồng (nếu hợp đồng chưa có line).
        """
        for r in self:
            if r.phu_cap_ids:
                continue
            if not r.nhan_vien_id or not r.nhan_vien_id.chuc_vu_id:
                continue

            lines = []
            for pc in r.nhan_vien_id.chuc_vu_id.phu_cap_mac_dinh_ids:
                lines.append((0, 0, {
                    "loai_phu_cap_id": pc.loai_phu_cap_id.id,
                    "so_tien": pc.so_tien,
                    "ghi_chu": pc.ghi_chu,
                }))
            if lines:
                r.write({"phu_cap_ids": lines})

    @api.onchange("nhan_vien_id")
    def _onchange_nhan_vien_id(self):
        """
        Khi chọn nhân viên trên form hợp đồng:
        - Auto copy phụ cấp theo chức vụ (nếu line đang trống).
        """
        for r in self:
            if not r.nhan_vien_id:
                continue
            if not r.phu_cap_ids:
                # chỉ fill khi đang trống để tránh overwrite user nhập
                r._tao_phu_cap_tu_chuc_vu()

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._tao_phu_cap_tu_chuc_vu()
        return rec

    def action_hieu_luc(self):
        for r in self:
            if r.trang_thai == "het_hieu_luc":
                raise ValidationError("Hợp đồng đã hết hiệu lực, không thể chuyển hiệu lực lại!")
            r.trang_thai = "hieu_luc"

    def action_het_hieu_luc(self):
        for r in self:
            r.trang_thai = "het_hieu_luc"

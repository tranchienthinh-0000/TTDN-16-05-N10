# -*- coding: utf-8 -*-
from odoo import models, fields


class LichSuThayDoi(models.Model):
    _name = "lich_su_thay_doi"
    _description = "Audit log - Lịch sử thao tác/đổi trạng thái đặt phòng"
    _order = "ngay_thay_doi desc, id desc"

    TRANG_THAI = [
        ("chờ_duyệt", "Chờ duyệt"),
        ("đã_duyệt", "Đã duyệt"),
        ("đang_sử_dụng", "Đang sử dụng"),
        ("đã_hủy", "Đã hủy"),
        ("đã_trả", "Đã trả"),
    ]

    HANH_DONG = [
        ("tao", "Tạo đăng ký"),
        ("duyet", "Duyệt"),
        ("huy", "Hủy"),
        ("huy_duyet", "Hủy duyệt"),
        ("bat_dau", "Bắt đầu sử dụng"),
        ("tra", "Trả phòng"),
        ("tu_dong_huy", "Tự động hủy do trùng lịch"),
        ("cap_nhat", "Cập nhật trực tiếp"),
    ]

    dat_phong_id = fields.Many2one("dat_phong", string="Mã đăng ký", required=True, ondelete="cascade")

    phong_id = fields.Many2one(
        "quan_ly_phong_hop", string="Phòng",
        related="dat_phong_id.phong_id", store=True, readonly=True
    )
    nguoi_muon_id = fields.Many2one(
        "nhan_vien", string="Người mượn",
        related="dat_phong_id.nguoi_muon_id", store=True, readonly=True
    )

    thoi_gian_muon_du_kien = fields.Datetime(
        string="Mượn dự kiến",
        related="dat_phong_id.thoi_gian_muon_du_kien", store=True, readonly=True
    )
    thoi_gian_tra_du_kien = fields.Datetime(
        string="Trả dự kiến",
        related="dat_phong_id.thoi_gian_tra_du_kien", store=True, readonly=True
    )

    hanh_dong = fields.Selection(HANH_DONG, string="Hành động", required=True)
    trang_thai_truoc = fields.Selection(TRANG_THAI, string="Trạng thái trước")
    trang_thai_sau = fields.Selection(TRANG_THAI, string="Trạng thái sau")

    nguoi_thuc_hien_user_id = fields.Many2one(
        "res.users", string="Người thực hiện",
        default=lambda self: self.env.user, readonly=True
    )
    ngay_thay_doi = fields.Datetime(string="Thời điểm", default=fields.Datetime.now, readonly=True)

    ghi_chu = fields.Text(string="Ghi chú")

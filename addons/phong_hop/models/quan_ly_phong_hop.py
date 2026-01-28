# -*- coding: utf-8 -*-
from odoo import models, fields, api


class QuanLyPhongHop(models.Model):
    _name = "quan_ly_phong_hop"
    _description = "Quản lý phòng họp, hội trường"

    active = fields.Boolean(string="Đang hoạt động", default=True)

    name = fields.Char(string="Tên phòng họp", required=True)
    loai_phong = fields.Selection([
        ("phong_hop", "Phòng họp"),
        ("hoi_truong", "Hội trường"),
    ], string="Loại phòng", required=True, default="phong_hop")
    suc_chua = fields.Integer(string="Sức chứa")

    trang_thai = fields.Selection([
        ("trong", "Trống"),
        ("da_muon", "Đã mượn"),
        ("dang_su_dung", "Đang sử dụng"),
    ], string="Trạng thái", compute="_compute_trang_thai", store=True)

    dat_phong_ids = fields.One2many("dat_phong", "phong_id", string="Tất cả lượt đặt/mượn")
    thiet_bi_ids = fields.One2many("thiet_bi", "phong_id", string="Thiết bị đang ở phòng")

    lich_dat_phong_ids = fields.One2many(
        "dat_phong", "phong_id",
        string="Lịch đặt phòng",
        domain=[("trang_thai", "in", ["đã_duyệt", "đang_sử_dụng", "da_duyet", "dang_su_dung"])]
    )

    # Audit log đúng nghĩa
    audit_ids = fields.One2many("lich_su_thay_doi", "phong_id", string="Audit log", readonly=True)

    # Tổng hợp mượn trả theo ngày/phòng
    lich_su_muon_tra_ids = fields.One2many("lich_su_muon_tra", "phong_id", string="Lịch sử mượn trả (theo ngày)", readonly=True)

    @api.depends("dat_phong_ids.trang_thai", "active")
    def _compute_trang_thai(self):
        for record in self:
            if not record.active:
                record.trang_thai = "trong"
                continue

            dang_sd = record.dat_phong_ids.filtered(lambda r: r.trang_thai in ["đang_sử_dụng", "dang_su_dung"])
            da_duyet_or_dang = record.dat_phong_ids.filtered(
                lambda r: r.trang_thai in ["đã_duyệt", "da_duyet", "đang_sử_dụng", "dang_su_dung"]
            )

            if dang_sd:
                record.trang_thai = "dang_su_dung"
            elif da_duyet_or_dang:
                record.trang_thai = "da_muon"
            else:
                record.trang_thai = "trong"

# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DatPhong(models.Model):
    _name = "dat_phong"
    _description = "Đặt phòng họp"
    _rec_name = "chu_de"
    _order = "bat_dau desc, id desc"

    phong_hop_id = fields.Many2one("phong_hop", string="Phòng họp", required=True, ondelete="restrict")
    chu_de = fields.Char(string="Chủ đề", required=True)

    bat_dau = fields.Datetime(string="Bắt đầu", required=True)
    ket_thuc = fields.Datetime(string="Kết thúc", required=True)

    # Chủ trì & tham dự lấy từ HR (nhan_vien)
    nguoi_chu_tri_id = fields.Many2one("nhan_vien", string="Người chủ trì", required=True, ondelete="restrict")
    thanh_phan_tham_du_ids = fields.Many2many(
        "nhan_vien",
        "dat_phong_nhan_vien_rel",
        "dat_phong_id",
        "nhan_vien_id",
        string="Thành phần tham dự",
    )

    trang_thai = fields.Selection(
        [
            ("nhap", "Nháp"),
            ("xac_nhan", "Đã xác nhận"),
            ("huy", "Hủy"),
        ],
        string="Trạng thái",
        default="nhap",
        required=True,
        index=True,
    )

    ghi_chu = fields.Text(string="Ghi chú")

    # --- Validate thời gian ---
    @api.constrains("bat_dau", "ket_thuc")
    def _check_time(self):
        for r in self:
            if r.bat_dau and r.ket_thuc and r.ket_thuc <= r.bat_dau:
                raise ValidationError("Thời gian kết thúc phải lớn hơn thời gian bắt đầu!")

    # --- BẮT BUỘC: Chặn xung đột cùng phòng ---
    @api.constrains("phong_hop_id", "bat_dau", "ket_thuc", "trang_thai")
    def _check_conflict(self):
        for r in self:
            if not r.phong_hop_id or not r.bat_dau or not r.ket_thuc:
                continue
            if r.trang_thai == "huy":
                continue

            # Overlap: start < other.end AND end > other.start
            conflict = self.search([
                ("id", "!=", r.id),
                ("phong_hop_id", "=", r.phong_hop_id.id),
                ("trang_thai", "!=", "huy"),
                ("bat_dau", "<", r.ket_thuc),
                ("ket_thuc", ">", r.bat_dau),
            ], limit=1)

            if conflict:
                raise ValidationError(
                    "Phòng họp đang bận trong khoảng thời gian này!\n"
                    f"Xung đột với lịch: {conflict.chu_de} ({conflict.bat_dau} - {conflict.ket_thuc})"
                )

    # Actions nút bấm
    def action_xac_nhan(self):
        for r in self:
            r.trang_thai = "xac_nhan"

    def action_huy(self):
        for r in self:
            r.trang_thai = "huy"

    def action_ve_nhap(self):
        for r in self:
            r.trang_thai = "nhap"

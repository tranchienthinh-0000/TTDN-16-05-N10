# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import datetime


class DatPhong(models.Model):
    _name = "dat_phong"
    _description = "Đăng ký mượn phòng"

    phong_id = fields.Many2one("quan_ly_phong_hop", string="Phòng họp", required=True)
    nguoi_muon_id = fields.Many2one("nhan_vien", string="Người mượn", required=True)

    # CẢI TIẾN: chọn thiết bị sử dụng cho lần đặt phòng
    thiet_bi_ids = fields.Many2many(
        comodel_name="thiet_bi",
        relation="dat_phong_thiet_bi_rel",
        column1="dat_phong_id",
        column2="thiet_bi_id",
        string="Thiết bị sử dụng",
    )

    thoi_gian_muon_du_kien = fields.Datetime(string="Thời gian mượn dự kiến", required=True)
    thoi_gian_muon_thuc_te = fields.Datetime(string="Thời gian mượn thực tế")
    thoi_gian_tra_du_kien = fields.Datetime(string="Thời gian trả dự kiến", required=True)
    thoi_gian_tra_thuc_te = fields.Datetime(string="Thời gian trả thực tế")

    trang_thai = fields.Selection([
        ("chờ_duyệt", "Chờ duyệt"),
        ("đã_duyệt", "Đã duyệt"),
        ("đang_sử_dụng", "Đang sử dụng"),
        ("đã_hủy", "Đã hủy"),
        ("đã_trả", "Đã trả")
    ], string="Trạng thái", default="chờ_duyệt")

    lich_su_ids = fields.One2many("lich_su_thay_doi", "dat_phong_id", string="Lịch sử mượn trả")

    # Giữ nguyên logic cũ (One2many theo phong_id)
    chi_tiet_su_dung_ids = fields.One2many(
        "dat_phong",
        "phong_id",
        string="Chi Tiết Sử Dụng",
        domain=[("trang_thai", "in", ["đang_sử_dụng", "đã_trả"])]
    )

    # ==========================
    # CẢI TIẾN: KHÔNG TRÙNG THIẾT BỊ THEO KHUNG GIỜ
    # ==========================
    def _kiem_tra_trung_thiet_bi(self):
        """
        Không cho trùng thiết bị theo khung giờ.
        Chặn với các đơn: chờ_duyệt / đã_duyệt / đang_sử_dụng.
        """
        for record in self:
            if not record.thiet_bi_ids:
                continue
            if not record.thoi_gian_muon_du_kien or not record.thoi_gian_tra_du_kien:
                continue
            if record.thoi_gian_muon_du_kien >= record.thoi_gian_tra_du_kien:
                raise exceptions.UserError("Thời gian trả dự kiến phải lớn hơn thời gian mượn dự kiến.")

            domain = [
                ("id", "!=", record.id),
                ("trang_thai", "in", ["chờ_duyệt", "đã_duyệt", "đang_sử_dụng"]),
                ("thoi_gian_muon_du_kien", "<", record.thoi_gian_tra_du_kien),
                ("thoi_gian_tra_du_kien", ">", record.thoi_gian_muon_du_kien),
                ("thiet_bi_ids", "in", record.thiet_bi_ids.ids),
            ]
            trung = self.search(domain, limit=1)
            if trung:
                tb_giao = record.thiet_bi_ids & trung.thiet_bi_ids
                raise exceptions.UserError(
                    "Thiết bị bị trùng lịch với một đơn đặt phòng khác.\n"
                    f"- Đơn trùng: {trung.display_name}\n"
                    f"- Thiết bị trùng: {', '.join(tb_giao.mapped('name'))}"
                )

    # Chặn “lách” bằng cách sửa trực tiếp record
    @api.constrains('thiet_bi_ids', 'thoi_gian_muon_du_kien', 'thoi_gian_tra_du_kien', 'trang_thai')
    def _constrains_trung_thiet_bi(self):
        for record in self:
            if record.trang_thai in ["chờ_duyệt", "đã_duyệt", "đang_sử_dụng"]:
                record._kiem_tra_trung_thiet_bi()

    def xac_nhan_duyet_phong(self):
        """Xác nhận duyệt phòng và tự động hủy các yêu cầu bị trùng thời gian."""
        for record in self:
            if record.trang_thai != "chờ_duyệt":
                raise exceptions.UserError("Chỉ có thể duyệt yêu cầu có trạng thái 'Chờ duyệt'.")

            # CẢI TIẾN: kiểm tra trùng thiết bị trước khi duyệt
            record._kiem_tra_trung_thiet_bi()

            # Duyệt yêu cầu hiện tại
            record.write({"trang_thai": "đã_duyệt"})
            record.lich_su(record)

            # Hủy các yêu cầu cùng phòng có thời gian trùng lặp
            cung_phong_trung_thoi_gian = [
                ("phong_id", "=", record.phong_id.id),
                ("id", "!=", record.id),
                ("trang_thai", "=", "chờ_duyệt"),
                ("thoi_gian_muon_du_kien", "<", record.thoi_gian_tra_du_kien),
                ("thoi_gian_tra_du_kien", ">", record.thoi_gian_muon_du_kien),
            ]
            xu_li_cung_phong = self.search(cung_phong_trung_thoi_gian)
            for other in xu_li_cung_phong:
                other.write({"trang_thai": "đã_hủy"})
                record.lich_su(other)

            # Hủy các yêu cầu khác phòng nhưng của cùng người mượn nếu bị trùng thời gian
            khac_phong_trung_thoi_gian = [
                ("nguoi_muon_id", "=", record.nguoi_muon_id.id),
                ("id", "!=", record.id),
                ("trang_thai", "=", "chờ_duyệt"),
                ("thoi_gian_muon_du_kien", "<", record.thoi_gian_tra_du_kien),
                ("thoi_gian_tra_du_kien", ">", record.thoi_gian_muon_du_kien),
            ]
            xu_li_khac_phong = self.search(khac_phong_trung_thoi_gian)
            for other in xu_li_khac_phong:
                other.write({"trang_thai": "đã_hủy"})
                record.lich_su(other)

    def huy_muon_phong(self):
        """Hủy đăng ký mượn phòng."""
        for record in self:
            if record.trang_thai != "chờ_duyệt":
                raise exceptions.UserError("Chỉ có thể hủy yêu cầu có trạng thái 'Chờ duyệt'.")
            record.write({"trang_thai": "đã_hủy"})
            record.lich_su(record)

    def huy_da_duyet(self):
        """Hủy yêu cầu đã duyệt."""
        for record in self:
            if record.trang_thai != "đã_duyệt":
                raise exceptions.UserError("Chỉ có thể hủy yêu cầu có trạng thái 'Đã duyệt'.")
            record.write({"trang_thai": "đã_hủy"})
            record.lich_su(record)

    def bat_dau_su_dung(self):
        """Bắt đầu sử dụng phòng - Cập nhật thời gian mượn thực tế."""
        for record in self:
            if record.trang_thai != "đã_duyệt":
                raise exceptions.UserError("Chỉ có thể bắt đầu sử dụng phòng có trạng thái 'Đã duyệt'.")

            # kiểm tra nếu đã có người đang sử dụng phòng này
            kiem_tra_phong = self.search([
                ("phong_id", "=", record.phong_id.id),
                ("trang_thai", "=", "đang_sử_dụng"),
                ("id", "!=", record.id),
            ], limit=1)
            if kiem_tra_phong:
                raise exceptions.UserError(
                    f"Phòng {record.phong_id.name} hiện đang được sử dụng. Vui lòng chờ đến khi phòng trống."
                )

            # CẢI TIẾN: kiểm tra trùng thiết bị ngay trước khi bắt đầu sử dụng
            record._kiem_tra_trung_thiet_bi()

            record.write({
                "trang_thai": "đang_sử_dụng",
                "thoi_gian_muon_thuc_te": datetime.now(),
            })
            record.lich_su(record)

            # (Khuyến nghị) Cập nhật trạng thái thiết bị
            if record.thiet_bi_ids:
                record.thiet_bi_ids.write({"trang_thai": "dang_su_dung"})

    def tra_phong(self):
        """Trả phòng - Cập nhật thời gian trả thực tế và đảm bảo thời gian mượn thực tế có giá trị."""
        for record in self:
            if record.trang_thai != "đang_sử_dụng":
                raise exceptions.UserError("Chỉ có thể trả phòng đang ở trạng thái 'Đang sử dụng'.")

            current_time = datetime.now()
            record.write({
                "trang_thai": "đã_trả",
                "thoi_gian_tra_thuc_te": current_time,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te or current_time,
            })
            record.lich_su(record)

            # (Khuyến nghị) Trả thiết bị về sẵn sàng
            if record.thiet_bi_ids:
                record.thiet_bi_ids.write({"trang_thai": "san_sang"})

    @api.model
    def lich_su(self, record):
        """Ghi vào lịch sử mượn trả."""
        self.env["lich_su_thay_doi"].create({
            "dat_phong_id": record.id,
            "nguoi_muon_id": record.nguoi_muon_id.id,
            "thoi_gian_muon_du_kien": record.thoi_gian_muon_du_kien,
            "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te,
            "thoi_gian_tra_du_kien": record.thoi_gian_tra_du_kien,
            "thoi_gian_tra_thuc_te": record.thoi_gian_tra_thuc_te,
            "trang_thai": record.trang_thai,
        })

# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from datetime import datetime


class DatPhong(models.Model):
    _name = "dat_phong"
    _description = "Đăng ký mượn phòng"
    _order = "thoi_gian_muon_du_kien desc, id desc"

    phong_id = fields.Many2one("quan_ly_phong_hop", string="Phòng họp", required=True)
    nguoi_muon_id = fields.Many2one("nhan_vien", string="Người mượn", required=True)

    thiet_bi_ids = fields.Many2many(
        "thiet_bi",
        "dat_phong_thiet_bi_rel",
        "dat_phong_id",
        "thiet_bi_id",
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
        ("đã_trả", "Đã trả"),
    ], string="Trạng thái", default="chờ_duyệt")

    lich_su_ids = fields.One2many("lich_su_thay_doi", "dat_phong_id", string="Lịch sử thay đổi (Audit)")

    # ✅ Thay One2many sai bằng Many2many compute để xem các lượt cùng phòng
    chi_tiet_su_dung_ids = fields.Many2many(
        "dat_phong",
        string="Chi tiết sử dụng (cùng phòng)",
        compute="_compute_chi_tiet_su_dung",
        store=False,
    )

    # ==========================================================
    # AUDIT
    # ==========================================================
    def _ghi_audit(self, record, hanh_dong, trang_thai_truoc, trang_thai_sau, ghi_chu=None):
        self.env["lich_su_thay_doi"].create({
            "dat_phong_id": record.id,
            "hanh_dong": hanh_dong,
            "trang_thai_truoc": trang_thai_truoc,
            "trang_thai_sau": trang_thai_sau,
            "ghi_chu": ghi_chu or "",
            "nguoi_thuc_hien_user_id": self.env.user.id,
        })

    # ==========================================================
    # VALIDATION TIME
    # ==========================================================
    def _validate_time(self):
        for r in self:
            if r.thoi_gian_muon_du_kien and r.thoi_gian_tra_du_kien:
                if r.thoi_gian_muon_du_kien >= r.thoi_gian_tra_du_kien:
                    raise exceptions.UserError("Thời gian trả dự kiến phải lớn hơn thời gian mượn dự kiến.")

    # ==========================================================
    # ✅ CHỐNG TRÙNG PHÒNG NGAY TỪ LÚC TẠO/CHỜ_DUYỆT
    # - Chỉ cần block nếu trùng với ĐƠN ĐÃ DUYỆT / ĐANG SỬ DỤNG
    # - Cho phép nhiều đơn CHỜ_DUYỆT trùng nhau (để admin chọn duyệt 1 đơn)
    # ==========================================================
    def _kiem_tra_trung_phong_voi_don_da_duyet_hoac_dang_sd(self):
        for r in self:
            if not r.phong_id or not r.thoi_gian_muon_du_kien or not r.thoi_gian_tra_du_kien:
                continue

            r._validate_time()

            domain = [
                ("id", "!=", r.id),
                ("phong_id", "=", r.phong_id.id),
                ("trang_thai", "in", ["đã_duyệt", "đang_sử_dụng"]),
                ("thoi_gian_muon_du_kien", "<", r.thoi_gian_tra_du_kien),
                ("thoi_gian_tra_du_kien", ">", r.thoi_gian_muon_du_kien),
            ]
            conflict = self.search(domain, limit=1)
            if conflict:
                raise exceptions.UserError(
                    "Phòng đã có lịch ĐÃ DUYỆT/ĐANG SỬ DỤNG trùng khung giờ.\n"
                    f"- Đơn trùng: {conflict.display_name}\n"
                    f"- Thời gian: {conflict.thoi_gian_muon_du_kien} → {conflict.thoi_gian_tra_du_kien}"
                )

    @api.constrains("phong_id", "thoi_gian_muon_du_kien", "thoi_gian_tra_du_kien", "trang_thai")
    def _constrains_khong_trung_phong(self):
        """
        Áp dụng cho đơn còn hiệu lực (chờ duyệt/đã duyệt/đang sử dụng).
        Mục tiêu: tạo 'chờ_duyệt' đã phải bị từ chối nếu đè lên đơn 'đã_duyệt' hoặc 'đang_sử_dụng'.
        """
        for r in self:
            if r.trang_thai in ["chờ_duyệt", "đã_duyệt", "đang_sử_dụng"]:
                r._kiem_tra_trung_phong_voi_don_da_duyet_hoac_dang_sd()

    # ==========================================================
    # TRÙNG THIẾT BỊ THEO KHUNG GIỜ (dự kiến)
    # ==========================================================
    def _kiem_tra_trung_thiet_bi(self):
        for record in self:
            if not record.thiet_bi_ids:
                continue
            if not record.thoi_gian_muon_du_kien or not record.thoi_gian_tra_du_kien:
                continue

            record._validate_time()

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
                    "Thiết bị bị trùng lịch.\n"
                    f"- Đơn trùng: {trung.display_name}\n"
                    f"- Thiết bị trùng: {', '.join(tb_giao.mapped('name'))}"
                )

    @api.constrains("thiet_bi_ids", "thoi_gian_muon_du_kien", "thoi_gian_tra_du_kien", "trang_thai")
    def _constrains_khong_trung_thiet_bi(self):
        for r in self:
            if r.trang_thai in ["chờ_duyệt", "đã_duyệt", "đang_sử_dụng"]:
                r._kiem_tra_trung_thiet_bi()

    # ==========================================================
    # THIẾT BỊ PHẢI Ở KHO + SẴN SÀNG
    # ==========================================================
    def _kiem_tra_thiet_bi_san_sang_trong_kho(self):
        for r in self:
            if r.trang_thai not in ["chờ_duyệt", "đã_duyệt", "đang_sử_dụng"]:
                continue
            if not r.thiet_bi_ids:
                continue

            tb_khong_hop_le = r.thiet_bi_ids.filtered(
                lambda tb: tb.trang_thai in ["hong", "can_bao_tri", "dang_su_dung"]
                or tb.vi_tri_hien_tai != "kho"
            )
            if tb_khong_hop_le:
                raise exceptions.UserError(
                    "Có thiết bị không hợp lệ (không ở kho / không sẵn sàng / đang hỏng-bảo trì-đang dùng):\n- "
                    + "\n- ".join(tb_khong_hop_le.mapped("name"))
                )

    @api.constrains("thiet_bi_ids", "trang_thai")
    def _constrains_thiet_bi_kho(self):
        self._kiem_tra_thiet_bi_san_sang_trong_kho()

    # ==========================================================
    # COMPUTE: chi_tiet_su_dung_ids
    # ==========================================================
    @api.depends("phong_id")
    def _compute_chi_tiet_su_dung(self):
        for r in self:
            if not r.phong_id:
                r.chi_tiet_su_dung_ids = [(6, 0, [])]
                continue
            bookings = self.search([
                ("phong_id", "=", r.phong_id.id),
                ("trang_thai", "in", ["đang_sử_dụng", "đã_trả"]),
            ], order="thoi_gian_muon_du_kien desc")
            r.chi_tiet_su_dung_ids = [(6, 0, bookings.ids)]

    # ==========================================================
    # CREATE/WRITE
    # ==========================================================
    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._ghi_audit(rec, "tao", False, rec.trang_thai, ghi_chu="Tạo đăng ký")
        return rec

    def write(self, vals):
        if self.env.context.get("skip_audit_write"):
            return super(DatPhong, self).write(vals)

        old_map = {r.id: r.trang_thai for r in self}
        res = super(DatPhong, self).write(vals)

        if "trang_thai" in vals:
            for r in self:
                truoc = old_map.get(r.id)
                sau = r.trang_thai
                if truoc != sau:
                    self._ghi_audit(r, "cap_nhat", truoc, sau, ghi_chu="Cập nhật trực tiếp (write)")

        need_rebuild = False
        if vals.get("trang_thai") == "đã_trả":
            need_rebuild = True
        if "thoi_gian_muon_thuc_te" in vals or "thoi_gian_tra_thuc_te" in vals:
            need_rebuild = True

        if need_rebuild and "lich_su_muon_tra" in self.env:
            try:
                self.env["lich_su_muon_tra"].update_lich_su_muon_tra()
            except Exception:
                pass

        return res

    # ==========================================================
    # NGHIỆP VỤ
    # ==========================================================
    def xac_nhan_duyet_phong(self):
        for record in self:
            if record.trang_thai != "chờ_duyệt":
                raise exceptions.UserError("Chỉ có thể duyệt yêu cầu có trạng thái 'Chờ duyệt'.")

            # ✅ check phòng trùng với đơn đã duyệt/đang dùng (lần nữa để chắc)
            record._kiem_tra_trung_phong_voi_don_da_duyet_hoac_dang_sd()

            record._kiem_tra_thiet_bi_san_sang_trong_kho()
            record._kiem_tra_trung_thiet_bi()

            truoc = record.trang_thai
            record.with_context(skip_audit_write=True).write({"trang_thai": "đã_duyệt"})
            record._ghi_audit(record, "duyet", truoc, record.trang_thai)

            # Hủy các yêu cầu cùng phòng trùng thời gian (chỉ chờ duyệt)
            cung_phong_trung = self.search([
                ("phong_id", "=", record.phong_id.id),
                ("id", "!=", record.id),
                ("trang_thai", "=", "chờ_duyệt"),
                ("thoi_gian_muon_du_kien", "<", record.thoi_gian_tra_du_kien),
                ("thoi_gian_tra_du_kien", ">", record.thoi_gian_muon_du_kien),
            ])
            for other in cung_phong_trung:
                t0 = other.trang_thai
                other.with_context(skip_audit_write=True).write({"trang_thai": "đã_hủy"})
                record._ghi_audit(
                    other, "tu_dong_huy", t0, other.trang_thai,
                    ghi_chu="Tự động hủy do trùng lịch (cùng phòng)"
                )

            # Hủy các yêu cầu khác phòng nhưng cùng người mượn trùng thời gian (chỉ chờ duyệt)
            khac_phong_trung = self.search([
                ("nguoi_muon_id", "=", record.nguoi_muon_id.id),
                ("id", "!=", record.id),
                ("trang_thai", "=", "chờ_duyệt"),
                ("thoi_gian_muon_du_kien", "<", record.thoi_gian_tra_du_kien),
                ("thoi_gian_tra_du_kien", ">", record.thoi_gian_muon_du_kien),
            ])
            for other in khac_phong_trung:
                t0 = other.trang_thai
                other.with_context(skip_audit_write=True).write({"trang_thai": "đã_hủy"})
                record._ghi_audit(
                    other, "tu_dong_huy", t0, other.trang_thai,
                    ghi_chu="Tự động hủy do trùng lịch (cùng người mượn)"
                )

    def huy_muon_phong(self):
        for record in self:
            if record.trang_thai != "chờ_duyệt":
                raise exceptions.UserError("Chỉ có thể hủy yêu cầu có trạng thái 'Chờ duyệt'.")
            truoc = record.trang_thai
            record.with_context(skip_audit_write=True).write({"trang_thai": "đã_hủy"})
            record._ghi_audit(record, "huy", truoc, record.trang_thai)

    def huy_da_duyet(self):
        for record in self:
            if record.trang_thai != "đã_duyệt":
                raise exceptions.UserError("Chỉ có thể hủy yêu cầu có trạng thái 'Đã duyệt'.")
            truoc = record.trang_thai
            record.with_context(skip_audit_write=True).write({"trang_thai": "đã_hủy"})
            record._ghi_audit(record, "huy_duyet", truoc, record.trang_thai)

    def bat_dau_su_dung(self):
        for record in self:
            if record.trang_thai != "đã_duyệt":
                raise exceptions.UserError("Chỉ có thể bắt đầu sử dụng phòng có trạng thái 'Đã duyệt'.")

            # vẫn giữ check phòng đang dùng (trạng thái realtime)
            dang_su_dung = self.search([
                ("phong_id", "=", record.phong_id.id),
                ("trang_thai", "=", "đang_sử_dụng"),
                ("id", "!=", record.id),
            ], limit=1)
            if dang_su_dung:
                raise exceptions.UserError(
                    f"Phòng {record.phong_id.name} hiện đang được sử dụng. Vui lòng chờ đến khi phòng trống."
                )

            record._kiem_tra_thiet_bi_san_sang_trong_kho()
            record._kiem_tra_trung_thiet_bi()

            truoc = record.trang_thai
            now = datetime.now()
            record.with_context(skip_audit_write=True).write({
                "trang_thai": "đang_sử_dụng",
                "thoi_gian_muon_thuc_te": now,
            })
            record._ghi_audit(record, "bat_dau", truoc, record.trang_thai)

            # Kho -> Phòng
            if record.thiet_bi_ids and hasattr(self.env["thiet_bi"], "dua_vao_phong"):
                self.env["thiet_bi"].dua_vao_phong(record.thiet_bi_ids, record.phong_id.id)
            elif record.thiet_bi_ids:
                record.thiet_bi_ids.write({
                    "trang_thai": "dang_su_dung",
                    "vi_tri_hien_tai": "phong",
                    "phong_hien_tai_id": record.phong_id.id,
                })

    def tra_phong(self):
        for record in self:
            if record.trang_thai != "đang_sử_dụng":
                raise exceptions.UserError("Chỉ có thể trả phòng đang ở trạng thái 'Đang sử dụng'.")

            truoc = record.trang_thai
            now = datetime.now()
            record.with_context(skip_audit_write=True).write({
                "trang_thai": "đã_trả",
                "thoi_gian_tra_thuc_te": now,
                "thoi_gian_muon_thuc_te": record.thoi_gian_muon_thuc_te or now,
            })
            record._ghi_audit(record, "tra", truoc, record.trang_thai)

            try:
                self.env["lich_su_muon_tra"].update_lich_su_muon_tra()
            except Exception:
                pass

            # Phòng -> Kho
            if record.thiet_bi_ids and hasattr(self.env["thiet_bi"], "dua_ve_kho"):
                self.env["thiet_bi"].dua_ve_kho(record.thiet_bi_ids)
            elif record.thiet_bi_ids:
                record.thiet_bi_ids.write({
                    "trang_thai": "san_sang",
                    "vi_tri_hien_tai": "kho",
                    "phong_hien_tai_id": False,
                })

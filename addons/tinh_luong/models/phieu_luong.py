# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PhieuLuong(models.Model):
    _name = "phieu_luong"
    _description = "Phiếu lương"
    _order = "ngay_tu desc, id desc"

    nhan_vien_id = fields.Many2one("nhan_vien", string="Nhân viên", required=True, ondelete="cascade")
    ngay_tu = fields.Date(string="Từ ngày", required=True)
    ngay_den = fields.Date(string="Đến ngày", required=True)

    trang_thai = fields.Selection(
        [
            ("nhap", "Nháp"),
            ("da_tinh", "Đã tính"),
            ("da_chot", "Đã chốt"),
            ("da_tra", "Đã trả"),
        ],
        default="nhap",
        required=True,
        string="Trạng thái",
    )

    hop_dong_id = fields.Many2one("hop_dong", string="Hợp đồng áp dụng", readonly=True)

    # tổng hợp giờ
    don_gia_gio = fields.Float(string="Đơn giá 1 giờ", readonly=True)
    tong_gio_thieu = fields.Float(string="Tổng giờ thiếu", readonly=True)
    tong_gio_ot = fields.Float(string="Tổng giờ OT", readonly=True)

    so_ngay_nghi_co_luong = fields.Float(string="Số ngày nghỉ có lương", readonly=True)
    so_ngay_nghi_khong_luong = fields.Float(string="Số ngày nghỉ không lương", readonly=True)

    # tiền
    luong_co_ban = fields.Float(string="Lương cơ bản", readonly=True)
    tong_phu_cap = fields.Float(string="Tổng phụ cấp", readonly=True)
    tien_tang_ca = fields.Float(string="Tiền tăng ca", readonly=True)
    tru_thieu_gio = fields.Float(string="Trừ thiếu giờ", readonly=True)
    tru_bao_hiem = fields.Float(string="Trừ bảo hiểm", default=0.0)
    thuc_nhan = fields.Float(string="Thực nhận", readonly=True)

    ghi_chu = fields.Text(string="Ghi chú")
    dong_ids = fields.One2many("dong_phieu_luong", "phieu_luong_id", string="Chi tiết")

    _sql_constraints = [
        ("uniq_nv_ky", "unique(nhan_vien_id, ngay_tu, ngay_den)", "Nhân viên đã có phiếu lương kỳ này!"),
    ]

    @api.constrains("ngay_tu", "ngay_den")
    def _check_dates(self):
        for r in self:
            if r.ngay_tu and r.ngay_den and r.ngay_den < r.ngay_tu:
                raise ValidationError("Ngày đến không được nhỏ hơn ngày từ!")

    def _get_hop_dong_hieu_luc(self):
        """Lấy hợp đồng hiệu lực trong kỳ (ưu tiên ngày bắt đầu mới nhất)."""
        self.ensure_one()
        today = fields.Date.today()
        hd = self.env["hop_dong"].search([
            ("nhan_vien_id", "=", self.nhan_vien_id.id),
            ("trang_thai", "=", "hieu_luc"),
            ("ngay_bat_dau", "<=", self.ngay_den),
            "|", ("ngay_ket_thuc", "=", False), ("ngay_ket_thuc", ">=", self.ngay_tu),
        ], order="ngay_bat_dau desc, id desc", limit=1)
        # fallback: nếu bạn không bắt buộc trang_thai, có thể nới điều kiện
        return hd

    def action_tinh_luong(self):
        for pl in self:
            if pl.trang_thai not in ("nhap", "da_tinh"):
                continue

            # 1) hợp đồng
            hd = pl._get_hop_dong_hieu_luc()
            if not hd:
                raise ValidationError("Không tìm thấy hợp đồng hiệu lực cho nhân viên trong kỳ này!")

            pl.hop_dong_id = hd.id

            so_ngay_chuan = hd.so_ngay_cong_chuan or 22.0
            so_gio_ngay = hd.so_gio_mot_ngay or 8.0
            gio_chuan_thang = so_ngay_chuan * so_gio_ngay

            luong_thang = hd.luong_cung_thang or 0.0
            don_gia_gio = (luong_thang / gio_chuan_thang) if gio_chuan_thang else 0.0

            # 2) chấm công trong kỳ
            cham = self.env["cham_cong"].search([
                ("nhan_vien_id", "=", pl.nhan_vien_id.id),
                ("ngay", ">=", pl.ngay_tu),
                ("ngay", "<=", pl.ngay_den),
            ])

            # thiếu giờ: trừ tất cả trừ ngày nghỉ phép có lương (trang_thai='nghi_phep')
            tong_gio_thieu = 0.0
            for cc in cham:
                if cc.trang_thai == "nghi_phep":
                    continue
                tong_gio_thieu += (cc.so_gio_thieu or 0.0)

            # 3) nghỉ phép (nếu module bạn có đơn nghỉ phép và phân loại)
            dnp = self.env["don_nghi_phep"].search([
                ("nhan_vien_id", "=", pl.nhan_vien_id.id),
                ("ngay_tu", "<=", pl.ngay_den),
                ("ngay_den", ">=", pl.ngay_tu),
                ("trang_thai", "=", "da_duyet"),
            ])
            # giả sử loai_nghi có: 'co_luong', 'khong_luong'
            so_ngay_nghi_co_luong = sum(x.so_ngay for x in dnp if x.loai_nghi == "co_luong")
            so_ngay_nghi_khong_luong = sum(x.so_ngay for x in dnp if x.loai_nghi == "khong_luong")

            # 4) tăng ca
            dtc = self.env["don_tang_ca"].search([
                ("nhan_vien_id", "=", pl.nhan_vien_id.id),
                ("ngay", ">=", pl.ngay_tu),
                ("ngay", "<=", pl.ngay_den),
                ("trang_thai", "=", "da_duyet"),
            ])
            tong_gio_ot = sum(x.so_gio_ot for x in dtc)
            tien_tang_ca = sum((x.so_gio_ot or 0.0) * don_gia_gio * (x.he_so or 2.0) for x in dtc)

            # 5) phụ cấp cố định từ hợp đồng
            tong_phu_cap = sum(hd.phu_cap_ids.mapped("so_tien")) if hasattr(hd, "phu_cap_ids") else 0.0

            # 6) công thức theo nghiệp vụ bạn đưa:
            luong_co_ban = luong_thang
            tru_thieu_gio = tong_gio_thieu * don_gia_gio
            thuc_nhan = luong_co_ban + tong_phu_cap + tien_tang_ca - tru_thieu_gio - (pl.tru_bao_hiem or 0.0)

            # ghi kết quả
            pl.write({
                "don_gia_gio": don_gia_gio,
                "tong_gio_thieu": tong_gio_thieu,
                "tong_gio_ot": tong_gio_ot,
                "so_ngay_nghi_co_luong": so_ngay_nghi_co_luong,
                "so_ngay_nghi_khong_luong": so_ngay_nghi_khong_luong,
                "luong_co_ban": luong_co_ban,
                "tong_phu_cap": tong_phu_cap,
                "tien_tang_ca": tien_tang_ca,
                "tru_thieu_gio": tru_thieu_gio,
                "thuc_nhan": thuc_nhan,
                "trang_thai": "da_tinh",
            })

            # 7) tạo dòng chi tiết (xoá cũ tạo mới)
            pl.dong_ids.unlink()
            lines = [
                (0, 0, {"sequence": 10, "ma": "BASIC", "ten": "Lương cơ bản", "so_tien": luong_co_ban}),
                (0, 0, {"sequence": 20, "ma": "ALLOW", "ten": "Phụ cấp", "so_tien": tong_phu_cap}),
                (0, 0, {"sequence": 30, "ma": "OT", "ten": "Tăng ca", "so_tien": tien_tang_ca}),
                (0, 0, {"sequence": 40, "ma": "DED_HOUR", "ten": "Trừ thiếu giờ", "so_tien": -tru_thieu_gio}),
                (0, 0, {"sequence": 50, "ma": "INS", "ten": "Bảo hiểm", "so_tien": -(pl.tru_bao_hiem or 0.0)}),
                (0, 0, {"sequence": 60, "ma": "NET", "ten": "Thực nhận", "so_tien": thuc_nhan}),
            ]
            pl.write({"dong_ids": lines})

    def action_chot(self):
        for pl in self:
            if pl.trang_thai != "da_tinh":
                raise ValidationError("Chỉ được chốt khi phiếu đang ở trạng thái 'Đã tính'!")
            pl.trang_thai = "da_chot"

    def action_da_tra(self):
        for pl in self:
            if pl.trang_thai != "da_chot":
                raise ValidationError("Chỉ được chuyển 'Đã trả' khi phiếu đang 'Đã chốt'!")
            pl.trang_thai = "da_tra"

    def action_ve_nhap(self):
        for pl in self:
            if pl.trang_thai not in ("nhap", "da_tinh"):
                raise ValidationError("Chỉ được về nháp từ 'Nháp' hoặc 'Đã tính'!")
            pl.trang_thai = "nhap"

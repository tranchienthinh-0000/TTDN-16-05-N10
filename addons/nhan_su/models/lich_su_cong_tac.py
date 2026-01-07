# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LichSuCongTac(models.Model):
    _name = "lich_su_cong_tac"
    _description = "Lịch sử công tác"
    _order = "ngay_bat_dau desc, id desc"

    nhan_vien_id = fields.Many2one("nhan_vien", string="Nhân viên", required=True, ondelete="cascade")

    phong_ban_id = fields.Many2one("phong_ban", string="Phòng ban", required=True, ondelete="restrict")
    chuc_vu_id = fields.Many2one("chuc_vu", string="Chức vụ", required=True, ondelete="restrict")

    ngay_bat_dau = fields.Date(string="Ngày bắt đầu", required=True)
    ngay_ket_thuc = fields.Date(string="Ngày kết thúc")

    trang_thai = fields.Selection(
        [("dang_lam", "Đang làm"), ("da_ket_thuc", "Đã kết thúc")],
        string="Trạng thái",
        default="dang_lam",
        required=True
    )

    ly_do = fields.Char(string="Lý do/Diễn giải")
    ghi_chu = fields.Text(string="Ghi chú")

    _sql_constraints = [
        ("check_dates",
         "CHECK(ngay_ket_thuc IS NULL OR ngay_ket_thuc >= ngay_bat_dau)",
         "Ngày kết thúc không được nhỏ hơn ngày bắt đầu!"),
    ]

    @api.constrains("ngay_bat_dau", "ngay_ket_thuc")
    def _check_dates(self):
        for r in self:
            if r.ngay_ket_thuc and r.ngay_bat_dau and r.ngay_ket_thuc < r.ngay_bat_dau:
                raise ValidationError("Ngày kết thúc không được nhỏ hơn ngày bắt đầu!")

    @api.onchange("ngay_ket_thuc")
    def _onchange_ngay_ket_thuc(self):
        for r in self:
            r.trang_thai = "da_ket_thuc" if r.ngay_ket_thuc else "dang_lam"

    def _dong_bo_nhan_vien(self):
        """Đồng bộ phòng ban/chức vụ hiện hành sang hồ sơ nhân viên."""
        for r in self:
            if r.trang_thai == "dang_lam" and r.nhan_vien_id:
                r.nhan_vien_id.write({
                    "phong_ban_id": r.phong_ban_id.id,
                    "chuc_vu_id": r.chuc_vu_id.id,
                })

    @api.model
    def create(self, vals):
        nhan_vien_id = vals.get("nhan_vien_id")
        ngay_bat_dau = vals.get("ngay_bat_dau")
        ngay_ket_thuc = vals.get("ngay_ket_thuc")

        if not vals.get("trang_thai"):
            vals["trang_thai"] = "da_ket_thuc" if ngay_ket_thuc else "dang_lam"

        rec = super().create(vals)

        # ✅ tự đóng bản ghi "đang làm" trước đó
        if nhan_vien_id and rec.trang_thai == "dang_lam" and ngay_bat_dau:
            prev = self.search([
                ("nhan_vien_id", "=", nhan_vien_id),
                ("id", "!=", rec.id),
                ("trang_thai", "=", "dang_lam"),
            ], order="ngay_bat_dau desc, id desc", limit=1)

            if prev:
                prev.write({
                    "ngay_ket_thuc": ngay_bat_dau,
                    "trang_thai": "da_ket_thuc",
                })

        # ✅ đồng bộ phòng ban/chức vụ sang nhân viên
        rec._dong_bo_nhan_vien()
        return rec

    def write(self, vals):
        res = super().write(vals)

        # Nếu user chỉ thay ngay_ket_thuc, tự set trạng thái
        if "ngay_ket_thuc" in vals and "trang_thai" not in vals:
            for r in self:
                r.trang_thai = "da_ket_thuc" if r.ngay_ket_thuc else "dang_lam"

        # Nếu record đang làm, đồng bộ lại
        for r in self:
            if r.trang_thai == "dang_lam" and (set(vals.keys()) & {"phong_ban_id", "chuc_vu_id", "trang_thai"}):
                r._dong_bo_nhan_vien()

        return res

# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BaoTriSuaChua(models.Model):
    _name = "bao_tri_sua_chua"
    _description = "Bảo trì / Sửa chữa"
    _order = "ngay_sua desc, id desc"

    tai_san_id = fields.Many2one(
        "quan_ly_ho_so_tai_san",
        string="Tài sản",
        required=True,
        ondelete="cascade"
    )
    ngay_sua = fields.Date(string="Ngày sửa", required=True, default=fields.Date.today)
    loi_gi = fields.Text(string="Lỗi gì", required=True)

    chi_phi = fields.Float(string="Chi phí", default=0.0)
    do_loi_nhan_vien_id = fields.Many2one(
        "nhan_vien",
        string="Do lỗi nhân viên",
        ondelete="set null"
    )

    trang_thai = fields.Selection(
        [
            ("dang_sua", "Đang sửa"),
            ("da_xong", "Đã xong"),
        ],
        string="Trạng thái",
        default="dang_sua",
        required=True,
        index=True,
    )

    ghi_chu = fields.Text(string="Ghi chú")

    @api.constrains("chi_phi")
    def _check_cost(self):
        for r in self:
            if r.chi_phi < 0:
                raise ValidationError("Chi phí không được âm!")

    @api.constrains("tai_san_id")
    def _check_tai_san(self):
        for r in self:
            if r.tai_san_id and r.tai_san_id.trang_thai == "thanh_ly":
                raise ValidationError("Tài sản đã thanh lý thì không được tạo phiếu bảo trì/sửa chữa!")

    def _dong_bo_trang_thai_tai_san(self):
        """Đồng bộ trạng thái tài sản theo tình trạng bảo trì và tình trạng cấp phát."""
        for r in self:
            if not r.tai_san_id:
                continue

            # Nếu đang sửa -> tài sản phải ở trạng thái bảo trì (trừ khi thanh lý)
            if r.trang_thai == "dang_sua":
                if r.tai_san_id.trang_thai != "thanh_ly":
                    r.tai_san_id.write({"trang_thai": "bao_tri"})
                continue

            # Nếu đã xong -> trả về đang sử dụng hoặc tồn kho tùy có ai đang giữ
            if r.trang_thai == "da_xong":
                dang_giu = r.tai_san_id.cap_phat_ids.filtered(lambda x: x.trang_thai == "dang_giu")
                r.tai_san_id.write({"trang_thai": "dang_su_dung" if dang_giu else "ton_kho"})

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        # tạo xong mặc định đang sửa => đồng bộ tài sản về bảo trì
        rec._dong_bo_trang_thai_tai_san()
        return rec

    def write(self, vals):
        res = super().write(vals)

        # nếu thay đổi trạng thái hoặc đổi tài sản thì đồng bộ lại
        if set(vals.keys()) & {"trang_thai", "tai_san_id"}:
            for r in self:
                r._dong_bo_trang_thai_tai_san()

        return res

    def action_da_xong(self):
        for r in self:
            if r.trang_thai == "da_xong":
                continue
            r.write({"trang_thai": "da_xong"})
        return True

# -*- coding: utf-8 -*-

import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class TaiSan(models.Model):
    _name = 'tai_san'
    _description = 'Bảng chứa thông tin tài sản'
    _order = 'ma_tai_san'
    _rec_name = 'ten_tai_san'

    _sql_constraints = [
        ('ma_tai_san_unique', 'unique(ma_tai_san)', 'Mã tài sản phải là duy nhất!')
    ]

    # =========================================================
    # FIELDS
    # =========================================================
    ma_tai_san = fields.Char(
        string="Mã Tài sản",
        required=True,
        copy=False,
        default="New",
        index=True,
    )
    so_serial = fields.Char(
        string="Serial",
        required=True,
        copy=False,
        default="New",
        index=True,
    )

    ten_tai_san = fields.Char(
        string="Tên Tài Sản",
        required=True,
        index=True,
    )

    ngay_mua = fields.Datetime(string="Ngày mua")
    ngay_het_han_bao_hanh = fields.Date(string="Ngày hết hạn bảo hành")

    gia_tien_mua = fields.Float(string="Giá tiền mua", digits=(16, 2))
    gia_tri_hien_tai = fields.Float(string="Giá trị hiện tại", digits=(16, 2))

    TRANG_THAI = [
        ("CatGiu", "Lưu trữ"),
        ("Muon", "Mượn"),
        ("BaoTri", "Bảo trì"),
        ("DaThanhLy", "Đã thanh lý"),
    ]

    trang_thai = fields.Selection(
        selection=TRANG_THAI,
        string="Trạng thái",
        default="CatGiu",
        tracking=True,
        required=True,
        index=True,
    )

    loai_tai_san_id = fields.Many2one(
        comodel_name='loai_tai_san',
        string="Loại tài sản",
        required=True,
    )

    vi_tri_hien_tai_id = fields.Many2one(
        comodel_name='vi_tri',
        string="Vị trí hiện tại",
        store=True,
    )

    nha_cung_cap_id = fields.Many2one(
        comodel_name='nha_cung_cap',
        string="Nhà cung cấp",
        store=True,
    )

    lich_su_su_dung_ids = fields.One2many(
        comodel_name='lich_su_su_dung',
        inverse_name='tai_san_id',
        string="Lịch sử sử dụng",
        store=True,
    )

    lich_su_bao_tri_ids = fields.One2many(
        comodel_name='lich_su_bao_tri',
        inverse_name='tai_san_id',
        string="Lịch sử bảo trì",
        store=True,
    )

    khau_hao_ids = fields.One2many(
        comodel_name='khau_hao',
        inverse_name='tai_san_id',
        string="Khấu hao",
        store=True,
    )

    lich_su_dieu_chuyen_ids = fields.One2many(
        comodel_name='lich_su_dieu_chuyen',
        inverse_name='tai_san_id',
        string="Lịch sử điều chuyển",
    )

    # Người đang sử dụng (phục vụ nghiệp vụ mượn)
    nguoi_su_dung_id = fields.Many2one(
        comodel_name="nhan_vien",
        string="Người đang sử dụng",
        store=True,
    )

    # Liên kết phiếu thanh lý (nếu có)
    thanh_ly_id = fields.Many2one(
        comodel_name='thanh_ly',
        string="Phiếu thanh lý",
    )

    # =========================================================
    # CREATE (OPTIONAL): AUTO SEQUENCE
    # =========================================================
    @api.model_create_multi
    def create(self, vals_list):
        """
        Nếu bạn có sequence, tự sinh mã cho ma_tai_san và/hoặc so_serial.
        Nếu chưa có sequence, vẫn giữ behavior cũ ('New').
        """
        for vals in vals_list:
            if vals.get('ma_tai_san', 'New') in (False, '', 'New'):
                seq = self.env['ir.sequence'].next_by_code('tai_san')
                if seq:
                    vals['ma_tai_san'] = seq

            if vals.get('so_serial', 'New') in (False, '', 'New'):
                seq2 = self.env['ir.sequence'].next_by_code('tai_san_serial')
                if seq2:
                    vals['so_serial'] = seq2
        return super().create(vals_list)

    # =========================================================
    # BUSINESS RULES (CONSTRAINTS)
    # =========================================================
    @api.constrains('trang_thai', 'nguoi_su_dung_id')
    def _check_trang_thai_nguoi_su_dung(self):
        """
        Quy tắc nghiệp vụ để dữ liệu không tự mâu thuẫn:
        - Nếu tài sản đang 'Muon' thì nên có người sử dụng.
        - Nếu tài sản 'CatGiu'/'BaoTri'/'DaThanhLy' thì không nên có người sử dụng.
        """
        for r in self:
            if r.trang_thai == 'Muon' and not r.nguoi_su_dung_id:
                raise ValidationError(_("Tài sản đang ở trạng thái 'Mượn' nhưng chưa có 'Người đang sử dụng'."))

            if r.trang_thai in ('CatGiu', 'BaoTri', 'DaThanhLy') and r.nguoi_su_dung_id:
                raise ValidationError(_("Tài sản không ở trạng thái 'Mượn' nên không được gắn 'Người đang sử dụng'."))

    @api.constrains('trang_thai', 'thanh_ly_id')
    def _check_thanh_ly_logic(self):
        """
        - Nếu trạng thái 'DaThanhLy' thì nên có thanh_ly_id.
        - Nếu có thanh_ly_id thì trạng thái nên là 'DaThanhLy'.
        (Bạn có thể nới lỏng nếu muốn, nhưng cái này giúp tránh lỗi nghiệp vụ.)
        """
        for r in self:
            if r.trang_thai == 'DaThanhLy' and not r.thanh_ly_id:
                # Nếu bạn không muốn bắt buộc, có thể comment dòng này
                raise ValidationError(_("Tài sản đã thanh lý nhưng chưa liên kết 'Phiếu thanh lý'."))

            if r.thanh_ly_id and r.trang_thai != 'DaThanhLy':
                raise ValidationError(_("Tài sản đã có 'Phiếu thanh lý' thì trạng thái phải là 'Đã thanh lý'."))

    # =========================================================
    # ACTIONS
    # =========================================================
    def action_dieu_chuyen_tai_san(self):
        self.ensure_one()
        return {
            'name': _('Điều chuyển tài sản'),
            'type': 'ir.actions.act_window',
            'res_model': 'lich_su_dieu_chuyen',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_tai_san_id': self.id,
                'default_vi_tri_id': self.vi_tri_hien_tai_id.id,
            },
        }

    # (Tuỳ chọn) Bạn có thể dùng 2 action này trong smart button hoặc server action
    def action_set_cat_giu(self):
        """Đưa tài sản về lưu trữ (không còn người sử dụng)."""
        for r in self:
            r.write({
                'trang_thai': 'CatGiu',
                'nguoi_su_dung_id': False,
                'thanh_ly_id': False,
            })

    def action_set_bao_tri(self):
        """Đưa tài sản sang bảo trì (không còn người sử dụng)."""
        for r in self:
            r.write({
                'trang_thai': 'BaoTri',
                'nguoi_su_dung_id': False,
            })

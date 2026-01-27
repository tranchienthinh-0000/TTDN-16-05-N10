# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ThanhLy(models.Model):
    _name = 'thanh_ly'
    _description = 'Quản lý thanh lý tài sản'
    _order = 'ma_thanh_ly desc'
    _sql_constraints = [
        ('ma_thanh_ly_unique', 'unique(ma_thanh_ly)', 'Mã thanh lý phải là duy nhất!')
    ]

    ma_thanh_ly = fields.Char(
        string="Mã thanh lý",
        copy=False,
        default="New",
    )

    ngay_thanh_ly = fields.Date(
        string="Ngày thanh lý",
        required=True,
        default=fields.Date.context_today,
    )

    tai_san_id = fields.Many2one(
        comodel_name='tai_san',
        string="Tài sản",
        required=True,
    )

    gia_tri_thanh_ly = fields.Float(
        string="Giá trị thanh lý",
        digits=(16, 2),
        required=True,
    )

    TRANG_THAI = [
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ]

    trang_thai = fields.Selection(
        selection=TRANG_THAI,
        string="Trạng thái",
        default='draft',
        required=True,
        tracking=True
    )

    ly_do = fields.Text(string="Lý do thanh lý")

    nguoi_xu_ly_id = fields.Many2one(
        comodel_name='nhan_vien',
        string="Người xử lý",
        required=True,
    )

    # =========================================================
    # CONSTRAINTS
    # =========================================================
    @api.constrains('tai_san_id')
    def _check_tai_san_thanh_ly(self):
        """
        Một tài sản chỉ được liên kết với 1 phiếu thanh lý "active".
        Nếu tài sản đang trỏ thanh_ly_id sang phiếu khác -> chặn.
        """
        for record in self:
            if not record.tai_san_id:
                continue
            if record.tai_san_id.thanh_ly_id and record.tai_san_id.thanh_ly_id != record:
                raise ValidationError(
                    _("Tài sản %s đã có phiếu thanh lý khác!") % (record.tai_san_id.ten_tai_san,)
                )

    @api.constrains('tai_san_id', 'trang_thai')
    def _check_tai_san_trang_thai(self):
        """
        Đồng bộ với TRANG_THAI của model tai_san:
        - Chỉ cho xác nhận/hoàn thành nếu tài sản KHÔNG đang 'Muon' hoặc 'BaoTri'
        - Không dùng 'Hong'/'LuuTru' vì model tai_san không có các key đó
        """
        for record in self:
            if not record.tai_san_id:
                continue

            # Khi xác nhận hoặc hoàn thành: không cho nếu tài sản đang mượn hoặc bảo trì
            if record.trang_thai in ('confirmed', 'done') and record.tai_san_id.trang_thai in ('Muon', 'BaoTri'):
                raise ValidationError(_("Không thể thanh lý tài sản đang được mượn hoặc bảo trì!"))

            # Nếu đã done thì tài sản nên là DaThanhLy (để tránh lệch dữ liệu)
            if record.trang_thai == 'done' and record.tai_san_id.trang_thai != 'DaThanhLy':
                raise ValidationError(_("Phiếu đã hoàn thành thì trạng thái tài sản phải là 'Đã thanh lý'."))

    # =========================================================
    # ACTIONS
    # =========================================================
    def action_confirm(self):
        self.ensure_one()
        if self.trang_thai != 'draft':
            raise ValidationError(_("Chỉ có thể xác nhận phiếu ở trạng thái Nháp!"))

        # Chặn xác nhận nếu tài sản đang mượn/bảo trì (đồng bộ logic)
        if self.tai_san_id.trang_thai in ('Muon', 'BaoTri'):
            raise ValidationError(_("Không thể xác nhận thanh lý: tài sản đang mượn hoặc bảo trì!"))

        self.trang_thai = 'confirmed'

    def action_done(self):
        """
        Hoàn thành thanh lý:
        - yêu cầu phiếu đã confirmed
        - set tài sản: trang_thai=DaThanhLy, thanh_ly_id=phiếu hiện tại, clear nguoi_su_dung_id
        - set phiếu: done
        """
        self.ensure_one()
        if self.trang_thai != 'confirmed':
            raise ValidationError(_("Phiếu cần được xác nhận trước khi hoàn thành!"))

        # Chặn nếu tài sản đang mượn/bảo trì (phòng trường hợp thay đổi sau confirm)
        if self.tai_san_id.trang_thai in ('Muon', 'BaoTri'):
            raise ValidationError(_("Không thể hoàn thành thanh lý: tài sản đang mượn hoặc bảo trì!"))

        self.tai_san_id.write({
            'trang_thai': 'DaThanhLy',
            'thanh_ly_id': self.id,
            'nguoi_su_dung_id': False,
        })

        self.trang_thai = 'done'

    def action_cancel(self):
        """
        Hủy phiếu:
        - chỉ cho hủy khi draft/confirmed
        - clear liên kết phiếu trên tài sản và đưa về CatGiu
        """
        self.ensure_one()
        if self.trang_thai not in ('draft', 'confirmed'):
            raise ValidationError(_("Không thể hủy phiếu đã hoàn thành!"))

        # Nếu tài sản đang trỏ về chính phiếu này thì mới clear (tránh clear nhầm)
        vals = {
            'trang_thai': 'CatGiu',          # KEY ĐÚNG, thay cho 'LuuTru'
            'nguoi_su_dung_id': False,
        }
        if self.tai_san_id.thanh_ly_id == self:
            vals['thanh_ly_id'] = False

        self.tai_san_id.write(vals)

        self.trang_thai = 'cancelled'

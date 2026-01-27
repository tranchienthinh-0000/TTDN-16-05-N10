# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PhieuMuon(models.Model):
    _name = 'phieu_muon'
    _description = 'Phiếu mượn tài sản'
    _order = 'ma_phieu_muon'

    ma_phieu_muon = fields.Char("Mã phiếu mượn", required=True)
    ngay_muon_du_kien = fields.Datetime("Thời gian mượn dự kiến", required=True)
    ngay_muon_thuc_te = fields.Datetime("Thời gian mượn thực tế", required=False)
    ngay_tra_du_kien = fields.Datetime("Thời gian trả dự kiến", required=True)
    ngay_tra_thuc_te = fields.Datetime("Thời gian trả thực tế", required=False)
    ghi_chu = fields.Char("Ghi chú")

    nhan_vien_id = fields.Many2one(
        comodel_name="nhan_vien", string="Nhân sự", required=True, store=True
    )

    tai_san_id = fields.Many2one(
        comodel_name="tai_san",
        string="Tài sản",
        required=True,
        store=True,
        domain=[('trang_thai', '=', 'CatGiu')],
    )

    state = fields.Selection(
        [('draft', 'Nháp'),
         ('approved', 'Đã duyệt'),
         ('done', 'Hoàn thành'),
         ('cancelled', 'Hủy')],
        default='draft',
        string="Trạng thái",
        required=True
    )

    trang_thai_muon = fields.Char(
        'Trạng thái mượn',
        compute='_compute_trang_thai_muon',
        store=True
    )

    # =========================================================
    # COMPUTE
    # =========================================================
    @api.depends('ngay_muon_du_kien', 'ngay_muon_thuc_te', 'ngay_tra_du_kien', 'ngay_tra_thuc_te')
    def _compute_trang_thai_muon(self):
        for record in self:
            muon_do_muon = (
                record.ngay_muon_thuc_te
                and record.ngay_muon_du_kien
                and record.ngay_muon_thuc_te > record.ngay_muon_du_kien
            )
            tra_do_muon = (
                record.ngay_tra_thuc_te
                and record.ngay_tra_du_kien
                and record.ngay_tra_thuc_te > record.ngay_tra_du_kien
            )

            if muon_do_muon and tra_do_muon:
                record.trang_thai_muon = 'Mượn muộn và trả muộn'
            elif muon_do_muon:
                record.trang_thai_muon = 'Mượn muộn'
            elif tra_do_muon:
                record.trang_thai_muon = 'Trả muộn'
            elif record.ngay_muon_thuc_te and record.ngay_tra_thuc_te:
                record.trang_thai_muon = 'Đúng hạn'
            elif record.ngay_muon_thuc_te:
                record.trang_thai_muon = 'Đang mượn'
            else:
                record.trang_thai_muon = 'Chưa mượn'

    # =========================================================
    # VALIDATION
    # =========================================================
    @api.constrains('ngay_muon_du_kien', 'ngay_tra_du_kien')
    def _check_du_kien(self):
        for r in self:
            if r.ngay_muon_du_kien and r.ngay_tra_du_kien and r.ngay_tra_du_kien <= r.ngay_muon_du_kien:
                raise ValidationError(_("Thời gian trả dự kiến phải sau thời gian mượn dự kiến."))

    @api.constrains('ngay_muon_thuc_te', 'ngay_tra_thuc_te')
    def _check_thuc_te(self):
        for r in self:
            if r.ngay_muon_thuc_te and r.ngay_tra_thuc_te and r.ngay_tra_thuc_te <= r.ngay_muon_thuc_te:
                raise ValidationError(_("Thời gian trả thực tế phải sau thời gian mượn thực tế."))

    # =========================================================
    # INTERNAL HELPERS
    # =========================================================
    def _find_lich_su_su_dung(self):
        """Giữ đúng logic bạn đang dùng: tìm theo nhân viên + tài sản + mốc dự kiến."""
        self.ensure_one()
        return self.env['lich_su_su_dung'].search([
            ('nhan_vien_id', '=', self.nhan_vien_id.id),
            ('tai_san_id', '=', self.tai_san_id.id),
            ('ngay_muon', '=', self.ngay_muon_du_kien),
            ('ngay_tra', '=', self.ngay_tra_du_kien),
        ], limit=1)

    def _ensure_can_approve(self):
        """Chặn duyệt nếu tài sản không còn CatGiu (tránh duyệt chồng)."""
        self.ensure_one()
        if not self.tai_san_id:
            raise UserError(_("Vui lòng chọn tài sản."))
        if self.tai_san_id.trang_thai != 'CatGiu':
            raise UserError(_("Tài sản không ở trạng thái 'Lưu trữ'. Không thể duyệt."))
        # nếu bạn muốn chặn theo người đang sử dụng thì bật thêm:
        if self.tai_san_id.nguoi_su_dung_id:
            raise UserError(_("Tài sản đang có người sử dụng. Không thể duyệt."))

    # =========================================================
    # ACTIONS
    # =========================================================
    def action_approve(self):
        """
        Duyệt:
        - Tạo lịch sử sử dụng (dựa theo mốc dự kiến)
        - Chuyển phiếu sang approved
        - Cập nhật tài sản: trang_thai=Muon, nguoi_su_dung_id=nhân viên
        """
        for record in self:
            if record.state != 'draft':
                continue

            record._ensure_can_approve()

            self.env['lich_su_su_dung'].create({
                'ma_lich_su_su_dung': self.env['ir.sequence'].next_by_code('lich_su_su_dung') or 'New',
                'ngay_muon': record.ngay_muon_du_kien,
                'ngay_tra': record.ngay_tra_du_kien,
                'ghi_chu': record.ghi_chu,
                'nhan_vien_id': record.nhan_vien_id.id,
                'tai_san_id': record.tai_san_id.id,
            })

            record.write({'state': 'approved'})

            # SỬA LỖI: field đúng trên tai_san là nguoi_su_dung_id
            record.tai_san_id.write({
                'trang_thai': 'Muon',
                'nguoi_su_dung_id': record.nhan_vien_id.id
            })

    def action_mark_borrowed(self):
        """
        Hướng C - Ghi nhận mượn:
        - Chỉ áp dụng khi approved
        - Set ngay_muon_thuc_te = now (hoặc nếu muốn nhập tay thì bạn bỏ readonly ở view)
        """
        for record in self:
            if record.state != 'approved':
                raise UserError(_("Chỉ có thể ghi nhận mượn khi phiếu ở trạng thái 'Đã duyệt'."))

            if record.ngay_muon_thuc_te:
                raise UserError(_("Phiếu này đã được ghi nhận mượn rồi."))

            record.write({'ngay_muon_thuc_te': fields.Datetime.now()})

    def action_mark_returned(self):
        """
        Hướng C - Ghi nhận trả:
        - Bắt buộc đã ghi nhận mượn
        - Set ngay_tra_thuc_te = now
        - Update lịch sử sử dụng (nếu tìm thấy)
        - Trả tài sản về CatGiu + clear nguoi_su_dung_id
        - Chuyển phiếu sang done
        """
        for record in self:
            if record.state != 'approved':
                raise UserError(_("Chỉ có thể ghi nhận trả khi phiếu ở trạng thái 'Đã duyệt'."))

            if not record.ngay_muon_thuc_te:
                raise UserError(_("Bạn cần 'Ghi nhận mượn' trước khi ghi nhận trả."))

            if record.ngay_tra_thuc_te:
                raise UserError(_("Phiếu này đã được ghi nhận trả rồi."))

            now = fields.Datetime.now()
            if now <= record.ngay_muon_thuc_te:
                raise UserError(_("Ngày trả thực tế phải sau ngày mượn thực tế."))

            record.write({'ngay_tra_thuc_te': now})

            lich_su = record._find_lich_su_su_dung()
            if lich_su:
                lich_su.write({
                    'ngay_muon': record.ngay_muon_thuc_te,
                    'ngay_tra': record.ngay_tra_thuc_te
                })

            record.tai_san_id.write({
                'trang_thai': 'CatGiu',
                'nguoi_su_dung_id': False
            })

            record.write({'state': 'done'})

    def action_done(self):
        """
        Giữ nút cũ (nếu bạn còn chỗ khác gọi) nhưng chuyển sang hướng C:
        - Nếu đã ghi nhận trả rồi thì done
        - Nếu chưa thì hướng người dùng dùng đúng nút
        """
        for record in self:
            if record.state != 'approved':
                continue
            if not record.ngay_muon_thuc_te or not record.ngay_tra_thuc_te:
                raise UserError(_("Hãy dùng nút 'Ghi nhận mượn' và 'Ghi nhận trả' trước."))
            record.write({'state': 'done'})

    def action_cancel(self):
        """
        Hủy:
        - Nếu có lịch sử sử dụng (theo logic search của bạn) thì xoá
        - Trả tài sản về CatGiu + clear nguoi_su_dung_id
        """
        for record in self:
            if record.state not in ['draft', 'approved']:
                continue

            lich_su_su_dung = record._find_lich_su_su_dung()
            if lich_su_su_dung:
                lich_su_su_dung.unlink()

            record.write({'state': 'cancelled'})

            if record.tai_san_id:
                record.tai_san_id.write({
                    'trang_thai': 'CatGiu',
                    'nguoi_su_dung_id': False
                })

    def action_reset_to_draft(self):
        """
        Quay lại nháp:
        - chỉ khi cancelled
        - trả tài sản về CatGiu + clear nguoi_su_dung_id
        """
        for record in self:
            if record.state != 'cancelled':
                continue

            record.write({'state': 'draft'})

            if record.tai_san_id:
                record.tai_san_id.write({
                    'trang_thai': 'CatGiu',
                    'nguoi_su_dung_id': False
                })

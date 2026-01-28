# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
import pytz


class LichSuMuonTra(models.Model):
    _name = "lich_su_muon_tra"
    _description = "Lịch sử sử dụng phòng họp (tổng hợp theo ngày/phòng)"
    _order = "ngay_su_dung desc, phong_id asc"
    _rec_name = "ngay_su_dung"

    ngay_su_dung = fields.Date(string="Ngày", required=True, default=fields.Date.today)
    phong_id = fields.Many2one("quan_ly_phong_hop", string="Phòng", required=True)

    chi_tiet_su_dung_ids = fields.Many2many(
        "dat_phong",
        string="Chi tiết sử dụng",
        compute="_compute_chi_tiet_su_dung",
        store=False,
    )

    tong_thoi_gian_su_dung = fields.Char(
        string="Tổng thời gian sử dụng",
        compute="_compute_tong_thoi_gian",
        store=False,
    )

    # ------------------------------
    # Helpers
    # ------------------------------
    def _user_tz(self):
        return pytz.timezone(self.env.user.tz or "UTC")

    def _day_range_utc(self, ngay_date):
        tz = self._user_tz()
        start_local = tz.localize(datetime.combine(ngay_date, datetime.min.time()))
        end_local = tz.localize(datetime.combine(ngay_date, datetime.max.time()))
        start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)
        end_utc = end_local.astimezone(pytz.utc).replace(tzinfo=None)
        return start_utc, end_utc

    def _status_da_tra(self):
        return ["đã_trả"]

    def _search_bookings(self, phong_id, ngay_date):
        if not phong_id or not ngay_date:
            return self.env["dat_phong"]

        start_dt, end_dt = self._day_range_utc(ngay_date)

        return self.env["dat_phong"].search([
            ("phong_id", "=", phong_id),
            ("trang_thai", "in", self._status_da_tra()),
            ("thoi_gian_muon_thuc_te", "!=", False),
            ("thoi_gian_tra_thuc_te", "!=", False),
            ("thoi_gian_muon_thuc_te", "<=", end_dt),
            ("thoi_gian_tra_thuc_te", ">=", start_dt),
        ], order="thoi_gian_muon_thuc_te asc")

    # ------------------------------
    # Computes
    # ------------------------------
    @api.depends("ngay_su_dung", "phong_id")
    def _compute_chi_tiet_su_dung(self):
        for r in self:
            if not r.ngay_su_dung or not r.phong_id:
                r.chi_tiet_su_dung_ids = [(6, 0, [])]
                continue
            bookings = r._search_bookings(r.phong_id.id, r.ngay_su_dung)
            r.chi_tiet_su_dung_ids = [(6, 0, bookings.ids)]

    @api.depends("ngay_su_dung", "phong_id")
    def _compute_tong_thoi_gian(self):
        for r in self:
            if not r.ngay_su_dung or not r.phong_id:
                r.tong_thoi_gian_su_dung = "00:00:00"
                continue

            start_dt, end_dt = r._day_range_utc(r.ngay_su_dung)
            bookings = r._search_bookings(r.phong_id.id, r.ngay_su_dung)

            total = 0
            for b in bookings:
                s = max(b.thoi_gian_muon_thuc_te, start_dt)
                e = min(b.thoi_gian_tra_thuc_te, end_dt)
                if e > s:
                    total += int((e - s).total_seconds())

            h, rem = divmod(total, 3600)
            m, s = divmod(rem, 60)
            r.tong_thoi_gian_su_dung = f"{h:02d}:{m:02d}:{s:02d}"

    # ------------------------------
    # PUBLIC ACTION: rebuild lịch sử
    # Gọi được từ server action / button
    # ------------------------------
    def update_lich_su_muon_tra(self):
        DatPhong = self.env["dat_phong"].sudo()

        records = DatPhong.search([
            ("trang_thai", "in", self._status_da_tra()),
            ("thoi_gian_muon_thuc_te", "!=", False),
            ("thoi_gian_tra_thuc_te", "!=", False),
            ("phong_id", "!=", False),
        ])

        tz = self._user_tz()
        data = {}

        for r in records:
            muon_local = pytz.utc.localize(r.thoi_gian_muon_thuc_te).astimezone(tz)
            tra_local = pytz.utc.localize(r.thoi_gian_tra_thuc_te).astimezone(tz)

            ngay_muon = muon_local.date()
            ngay_tra = tra_local.date()
            if ngay_tra < ngay_muon:
                continue

            for n in range((ngay_tra - ngay_muon).days + 1):
                d = ngay_muon + timedelta(days=n)
                key = (d, r.phong_id.id)
                if key not in data:
                    data[key] = {"ngay_su_dung": d, "phong_id": r.phong_id.id}

        # rebuild toàn bộ
        self.sudo().search([]).unlink()
        if data:
            self.sudo().create(list(data.values()))

        # ✅ reload lại màn hình list/form ngay sau khi chạy
        return {"type": "ir.actions.client", "tag": "reload"}

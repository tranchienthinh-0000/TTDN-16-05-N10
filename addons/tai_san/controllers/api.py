# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
from datetime import datetime


def _json_ok(data=None):
    return {"success": True, "data": data or {}, "error": None}


def _json_fail(message, code="ERROR"):
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


class PhongHopAPI(http.Controller):

    @http.route("/api/phong_hop/availability", type="json", auth="user", methods=["POST"], csrf=False)
    def availability(self, **payload):
        """
        Payload:
        {
          "from": "2026-01-28 08:00:00",
          "to":   "2026-01-28 10:00:00"
        }
        """
        try:
            dt_from = payload.get("from")
            dt_to = payload.get("to")
            if not dt_from or not dt_to:
                return _json_fail("Thiếu 'from' hoặc 'to'.", "BAD_REQUEST")

            start = datetime.strptime(dt_from, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(dt_to, "%Y-%m-%d %H:%M:%S")
            if start >= end:
                return _json_fail("Khoảng thời gian không hợp lệ (from < to).", "BAD_REQUEST")

            DatPhong = request.env["dat_phong"].sudo()
            Phong = request.env["quan_ly_phong_hop"].sudo()

            # Các booking chiếm phòng: đã duyệt / đang sử dụng
            conflict = DatPhong.search([
                ("trang_thai", "in", ["đã_duyệt", "đang_sử_dụng"]),
                ("thoi_gian_muon_du_kien", "<", dt_to),
                ("thoi_gian_tra_du_kien", ">", dt_from),
                ("phong_id", "!=", False),
            ])
            busy_room_ids = list(set(conflict.mapped("phong_id").ids))

            free_rooms = Phong.search([("id", "not in", busy_room_ids)])
            busy_rooms = Phong.browse(busy_room_ids)

            return _json_ok({
                "from": dt_from,
                "to": dt_to,
                "free": [{"id": r.id, "name": r.display_name} for r in free_rooms],
                "busy": [{"id": r.id, "name": r.display_name} for r in busy_rooms],
            })

        except Exception as e:
            return _json_fail(str(e))

    @http.route("/api/phong_hop/dat_phong", type="json", auth="user", methods=["POST"], csrf=False)
    def create_booking(self, **payload):
        """
        Payload:
        {
          "phong_id": 1,
          "nguoi_muon_id": 3,
          "from": "2026-01-28 08:00:00",
          "to":   "2026-01-28 10:00:00",
          "thiet_bi_ids": [1,2,3]   # optional
        }
        """
        try:
            phong_id = payload.get("phong_id")
            nguoi_muon_id = payload.get("nguoi_muon_id")
            dt_from = payload.get("from")
            dt_to = payload.get("to")
            thiet_bi_ids = payload.get("thiet_bi_ids") or []

            if not phong_id or not nguoi_muon_id or not dt_from or not dt_to:
                return _json_fail("Thiếu phong_id / nguoi_muon_id / from / to.", "BAD_REQUEST")

            # tạo ở trạng thái chờ duyệt
            DatPhong = request.env["dat_phong"].sudo()

            vals = {
                "phong_id": int(phong_id),
                "nguoi_muon_id": int(nguoi_muon_id),
                "thoi_gian_muon_du_kien": dt_from,
                "thoi_gian_tra_du_kien": dt_to,
                "trang_thai": "chờ_duyệt",
            }
            if thiet_bi_ids:
                vals["thiet_bi_ids"] = [(6, 0, [int(x) for x in thiet_bi_ids])]

            rec = DatPhong.create(vals)

            return _json_ok({
                "id": rec.id,
                "name": rec.display_name,
                "trang_thai": rec.trang_thai,
            })

        except UserError as e:
            return _json_fail(e.name, "USER_ERROR")
        except Exception as e:
            return _json_fail(str(e))

@http.route("/api/ping", type="json", auth="none", methods=["POST"], csrf=False)
def ping(self, **kw):
    return {"ok": True, "msg": "pong"}

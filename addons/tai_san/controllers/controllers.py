# -*- coding: utf-8 -*-
# from odoo import http


# class TaiSan(http.Controller):
#     @http.route('/tai_san/tai_san', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tai_san/tai_san/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('tai_san.listing', {
#             'root': '/tai_san/tai_san',
#             'objects': http.request.env['quan_ly_ho_so_tai_san'].search([]),
#         })

#     @http.route('/tai_san/tai_san/objects/<model("quan_ly_ho_so_tai_san"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tai_san.object', {
#             'object': obj
#         })

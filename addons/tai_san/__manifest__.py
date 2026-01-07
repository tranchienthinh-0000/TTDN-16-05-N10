# -*- coding: utf-8 -*-
{
    "name": "Tai_san",
    "summary": "Quản lý tài sản, cấp phát/thu hồi, bảo trì/sửa chữa, khấu hao",
    "category": "Human Resources",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["base", "nhan_su"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/quan_ly_ho_so_tai_san.xml",
        "views/cap_phat_thu_hoi.xml",
        "views/bao_tri_sua_chua.xml",
        "views/khau_hao.xml",
        "views/nhan_vien_inherit.xml",
        "views/menu.xml",
    ],
    "application": True,
    "installable": True,
}

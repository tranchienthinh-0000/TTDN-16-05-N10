# -*- coding: utf-8 -*-
{
    "name": "phong_hop",
    "summary": "Quản lý phòng họp",
    "description": "Thiết lập phòng họp, đặt phòng theo lịch, chặn xung đột.",
    "author": "My Company",
    "category": "Productivity",
    "version": "0.1",
    "license": "LGPL-3",
    "depends": ["base", "nhan_su"],

    "data": [
        "security/ir.model.access.csv",
        "views/phong_hop.xml",
        "views/dat_phong.xml",
        "views/nhan_vien_inherit.xml",
        "views/menu.xml",
    ],
    "application": True,
    "installable": True,
}

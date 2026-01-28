# -*- coding: utf-8 -*-
{
    "name": "Quản lý tài sản",
    "summary": "Quản lý tài sản, mượn trả, bảo trì, điều chuyển, khấu hao, thanh lý",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "nhan_su",
        # "phong_hop",  # BỎ để tránh circular dependency
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/loai_tai_san.xml",
        "views/vi_tri.xml",
        "views/nha_cung_cap.xml",
        "views/tai_san.xml",
        "views/phieu_muon.xml",
        "views/phieu_bao_tri.xml",
        "views/phieu_dieu_chuyen.xml",
        "views/thanh_ly.xml",
        "views/lich_su_su_dung.xml",
        "views/lich_su_bao_tri.xml",
        "views/lich_su_dieu_chuyen.xml",
        "views/khau_hao.xml",
        "views/tai_san_statistics.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
}

# -*- coding: utf-8 -*-
{
    "name": "Quản lý phòng họp",
    "summary": "Quản lý phòng họp, đặt phòng và theo dõi lịch sử mượn/trả gắn với nhân sự",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["base", "nhan_su", "tai_san"],
    "data": [
        "security/ir.model.access.csv",

        "views/menu.xml",  

        "views/quan_ly_phong_hop.xml",
        "views/thiet_bi.xml",
        "views/dat_phong.xml",
        "views/lich_su_thay_doi.xml",
        "views/lich_su_muon_tra.xml",
        "views/dat_phong_dashboard.xml",
        "views/actions.xml",

        "views/phong_hop_ai_wizard_views.xml",  
    ],
    "installable": True,
    "application": True,
}

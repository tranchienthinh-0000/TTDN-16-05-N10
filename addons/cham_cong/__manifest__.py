# -*- coding: utf-8 -*-
{
    "name": "Cham Cong",
    "summary": "Chấm công - Nghỉ phép - Tăng ca",
    "description": "Module chấm công riêng, liên kết nhân sự (nhan_su).",
    "author": "You",
    "version": "1.0",
    "license": "LGPL-3",
    "category": "Human Resources",
    "depends": ["base", "nhan_su"],
    "application": True,
    "data": [
        "security/ir.model.access.csv",
        "views/cham_cong.xml",
        "views/don_nghi_phep.xml",
        "views/don_tang_ca.xml",
        "views/menu.xml",
    ],
    "installable": True,
}

# -*- coding: utf-8 -*-
{
    "name": "Tính lương",
    "summary": "Phiếu lương tổng hợp từ Chấm công / Nghỉ phép / Tăng ca",
    "category": "Human Resources",
    "version": "1.0",
    "license": "LGPL-3",
    "depends": ["base", "nhan_su", "cham_cong"],
    "data": [
        "security/ir.model.access.csv",
        "views/phieu_luong.xml",
        "views/menu.xml",
    ],
    "application": True,
}

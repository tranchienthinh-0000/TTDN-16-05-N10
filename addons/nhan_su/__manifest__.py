# -*- coding: utf-8 -*-
{
    "name": "nhan_su",
    "summary": "Quản lý nhân sự",
    "description": """
Quản lý nhân viên, phòng ban, chức vụ, lịch sử công tác, chứng chỉ, chấm công,
hợp đồng, phụ cấp, nghỉ phép, tăng ca, phiếu lương.
""",
    "author": "My Company",
    "website": "http://www.yourcompany.com",
    "category": "Human Resources",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["base"],

    "data": [
        "security/ir.model.access.csv",
        "views/nhan_vien.xml",
        "views/phong_ban.xml",
        "views/chuc_vu.xml",
        "views/lich_su_cong_tac.xml",
        "views/chung_chi.xml",
        "views/cham_cong.xml",
        "views/loai_phu_cap.xml",
        "views/phu_cap_chuc_vu.xml",
        "views/hop_dong.xml",
        "views/don_nghi_phep.xml",
        "views/don_tang_ca.xml",
        "views/phieu_luong.xml",
        "views/menu.xml",
    ],

    "installable": True,
    "application": True,
}

# -*- coding: utf-8 -*-
{
    'name': "Quản lý phòng họp",

    'summary': """
        Quản lý phòng họp, đặt phòng và theo dõi lịch sử mượn/trả gắn với nhân sự
    """,

    'description': """
        Module Quản lý phòng họp phục vụ các nghiệp vụ:
        - Quản lý danh mục phòng họp và thiết bị đi kèm.
        - Đặt/mượn phòng họp theo khung thời gian, xác định người mượn là nhân viên.
        - Theo dõi lịch sử thay đổi (audit) và lịch sử mượn/trả.
        - Cung cấp giao diện dashboard phục vụ theo dõi tình trạng đặt phòng.

        Module bắt buộc tích hợp với module Quản lý nhân sự (nhan_su):
        - Người mượn phòng (nguoi_muon_id) liên kết tới hồ sơ nhân viên (nhan_vien).
        - Lịch sử thay đổi ghi nhận nhân viên thực hiện thao tác.
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'category': 'Human Resources',
    'version': '0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'nhan_su', 'tai_san'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/quan_ly_phong_hop.xml',
        'views/dat_phong.xml',
        'views/lich_su_thay_doi.xml',
        'views/lich_su_muon_tra.xml',
        'views/thiet_bi.xml',
        'views/dat_phong_dashboard.xml',
        'views/menu.xml',
    ],

    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

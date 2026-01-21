# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

{
    "name": "Bizzup Belement Sale Quote Report",
    "summary": "Belement Sale Quote Report",
    "description": """
        
     """,
    "version": "18.0.1.2.0",
    "category": "",
    "license": "Other proprietary",
    "author": "Gilliam Management Services and Information Systems, Ltd.",
    "website": "www.bizzup.app",
    "depends": ['sale','bizzup_sale_report_customization'],
    "data": [
        'views/sale_order_view.xml',
        'views/sale_order_line_view.xml',
        'reports/external_layout_belement.xml',
        'views/res_company_view.xml',
        'reports/report_saleorder_document_belement.xml'
    ],
    "installable": True,
    "application": False,
}

# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app
# -*- coding: utf-8 -*-

{
    'name': 'Bizzup PCN Report',
    "description": """
        This module will generate a PCN report which will take all the tax
        entries of Account and with header and detailed records in it.""",
    'version': '19.0.1.0.0',
    'license': 'Other proprietary',
    'author': 'Gilliam Management Services and Information Systems, Ltd.',
    'website': 'https://bizzup.app',
    'depends': [
        'base',
        'oii_israel_invoices',
        'ygol_l10n_il_unified',

    ],
    'data': {
        'security/ir.model.access.csv',
        'data/cron.xml',
        "data/pcn_report.xml",
        "data/action_pcn_report.xml",
        'views/account_move_views.xml',
        'views/pcn_attachment_view.xml',
        'report/pcn_report_template.xml',
        'wizards/pcn_report_wizard_views.xml',
    },
    'application': True,
    'installable': True,
}

# -*- coding: utf-8 -*-
{
    "name": "Aktiv Accounting Customisation",
    "category": "Account",
    "author": "Aktiv Software",
    "version": "19.0.1.1.0",
    "license": "OPL-1",
    "depends": ["l10n_in", "l10n_in_edi", "account_followup", "account_reports"],
    "data": [
        "data/account_followup_data.xml",
        "data/followup_report_column_data.xml",
        "data/cron_salesperson_weekly_email.xml",
        "report/external_layout_bubble.xml",
        "report/account_tax_totals.xml",
        "report/report_invoice_views.xml",
    ],
    'assets': {
        'web.report_assets_common': [
                'account_extended/static/src/css/invoice_report.css',
            ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

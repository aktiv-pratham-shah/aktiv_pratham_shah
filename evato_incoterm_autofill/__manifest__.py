# -*- coding: utf-8 -*-
{
    'name': 'Evato Incoterm Auto-fill',
    'version': '19.0.1.0.0',
    'category': 'Account',
    'summary': 'Auto-fill Incoterm from Partner in Sales, Purchase, and Invoices',
    'description': """
        This module automatically populates the Incoterm field when a partner is selected in:
        - Sales Order
        - Purchase Order
        - Account Move (Invoices)
    """,
    'depends': ['account', 'account_accountant', 'contacts', 'sale_stock', 'purchase', 'purchase_stock'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

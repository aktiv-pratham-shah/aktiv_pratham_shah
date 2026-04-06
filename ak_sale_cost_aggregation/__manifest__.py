{
    'name': 'Sale Order Cost Aggregation',
    'version': '19.0.1.0.0',
    'summary': 'Aggregates all order line costs into the first line for margin calculation.',
    'description': """
Sale Order Cost Aggregation
===========================
This module consolidates the costs of all products in a Sale Order into the first line.
Individual costs remain editable, but for margin purposes, the total cost is attributed only to the first line.

Key Features:
- Adds an 'Individual Cost' field for each sale order line.
- Automatically calculates the first line's purchase price as the sum of all lines' costs.
- Sets the purchase price of subsequently added lines to zero (for margin calculation).
- Preserves standard margin calculation logic while redirecting the cost focus.
    """,
    'category': 'Sales/Sales',
    'author': 'Pratham',
    'depends': ['sale_margin','sale'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

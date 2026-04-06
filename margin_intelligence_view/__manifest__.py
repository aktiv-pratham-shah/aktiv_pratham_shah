{
    'name': 'Margin Intelligence View',
    'version': '18.0.1.0.0',
    'category': 'Sales/Purchase',
    'summary': 'Real-time profit margin analysis for Sales and Purchase orders',
    'description': 'Adds a dashboard view to analyze profit margins on sale and purchase lines with health-coded status.',
    "author": "Pratham Shah",
    'depends': ['sale_management', 'purchase', 'stock'],
    'data': [
        'views/margin_intelligence_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'margin_intelligence_view/static/src/css/margin_intelligence.css',
            'margin_intelligence_view/static/src/js/margin_intelligence.js',
            'margin_intelligence_view/static/src/xml/margin_intelligence.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

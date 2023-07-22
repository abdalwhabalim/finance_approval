{
    'name': 'Finance Vouchers Approval / Cash Approval',
    'version': '15.0',
    'category': 'Accounting',
    'author': 'SGT',
    'support': 'support@softguidetech.com',
    'website': 'https://softguidetech.com',
    'license': 'OPL-1',
    'price': '11',
    'currency': 'EUR',
    'data': [

        'security/security_view.xml',
        'security/ir.model.access.csv',
        'views/cash_voucher_view.xml',
        'views/res_config_settings_views.xml',
        'views/voucher_approval_route.xml',
        'data/voucher_approval_route.xml',
        'reports/cash_report.xml',
    ],
    'images': [
        'static/description/logo.png',
    ],
    'depends': ['base','account','analytic','payment'],




    'installable': True,
    'application': True,






}

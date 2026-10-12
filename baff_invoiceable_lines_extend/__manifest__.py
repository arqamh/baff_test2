{
    'name': 'Invoiceable Lines Extend',
    'version': '16.0.1.1',
    'sequence': 10,
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'summary': 'Price the quotation invoiceable lines from the Job Costing Sheet',
    'description': """
Replaces the 'Add Invoiceable Lines' button of the Job Costing Sheet.
One invoiceable line per ticked line ('Is Included In Report', normally the child BOMs), plus one
line per main parent for the cost of its lines that are not ticked, priced with the Material,
Labour, Overhead share, Gross Profit % Markup and Sale Commission of the sheet.
The button is available once the Sales Order is created, until the sheet is Done.
""",
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'depends': [
        'odoo_job_costing_management',
        'centrics_sales_separate_process',
    ],
    'data': [
        'views/job_costing_views.xml',
    ],
}

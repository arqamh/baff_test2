from odoo import fields, models


class InvoiceableLines(models.Model):
    _inherit = 'invoiceable.lines'

    category = fields.Selection(
        selection=[
            ('product', 'Product'),
            ('labor', 'Labor'),
            ('overhead', 'Overhead'),
        ],
        string='Category',
        help='Categorises invoiceable lines generated from a Job Costing '
             'Sheet so the Product / Labor / Overhead totals can be tracked '
             'and rendered in the SO and on the invoice.')
    job_costing_id = fields.Many2one(
        'job.costing', string='Job Costing Sheet',
        help='Job Costing Sheet that produced this invoiceable line.')
    finished_good_id = fields.Many2one(
        'job.costing.finished.good', string='Finished Good',
        help='Finished-good line on the Job Costing Sheet that produced '
             'this invoiceable line (only set on Product-category lines).')

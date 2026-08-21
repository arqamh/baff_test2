from odoo import models, fields, api


class ProcurementPlanColor(models.Model):
    _name = 'procurement.plan.color'
    _description = 'Procurement Plan Colors'

    company_id = fields.Many2one('res.company')
    condition_type = fields.Selection([('on_date', 'On Order Date'), ('date_before_date', 'Before Order Date'), ('has_passed_date', 'Order Date Due'), ('partial_delivery', 'Partial Delivery')], required=True)
    condition_colors = fields.Selection([('warning', 'Warning'),
                                ('red', 'Red'),
                                ('blue', 'Blue'),
                                ('green', 'Green'),
                                         ], required=True)
    no_of_dates = fields.Integer(default=1)

    _sql_constraints = [
        ('company_condition_unique',
         'unique (company_id, condition_type)',
         'Condition Type must be unique per company'
         ),
        (
            'check_no_of_dates_zero',
            'CHECK(no_of_dates >= 1)',
            "Minimum Days count should be more than 1",
        ),
    ]



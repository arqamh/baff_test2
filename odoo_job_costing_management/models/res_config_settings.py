from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    factory_admin_overhead = fields.Float(string='Factory and Admin Overhead',
                                          config_parameter='odoo_job_costing_management.factory_admin_overhead',
                                          related='company_id.factory_admin_overhead', readonly=False)

    profit_margin = fields.Float(string='Profit Margin', config_parameter='odoo_job_costing_management.profit_margin',
                                 related='company_id.profit_margin', readonly=False)
    job_cost_prefix = fields.Char(string="Sequence Prefix", related='company_id.job_cost_prefix', readonly=False)
    job_cost_revise_suffix = fields.Char(string="Revise Sequence Suffix", related='company_id.job_cost_revise_suffix', readonly=False)
    vendor_price_margin = fields.Float(string="Vendor Price Margin", related='company_id.vendor_price_margin', readonly=False)



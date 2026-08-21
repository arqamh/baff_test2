from odoo import models,fields,api,_


class HrContract(models.Model):
    _inherit = 'hr.contract'

    advances_limit_line_ids = fields.One2many('hr.contract.advance.limit.line', 'contract_id')
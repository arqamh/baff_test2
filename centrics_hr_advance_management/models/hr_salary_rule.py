from odoo import models,fields,api,_


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    is_advance_rule = fields.Boolean(string="Is Advance Rule", help="Flag to indicate if salary rule is an advance rule")

    @api.model
    def create(self, values):
        """
        Create a new HR Salary Rule record.

        This method extends the create operation of the `HrSalaryRule` model and adds
        additional functionality. Specifically, it interacts with the `advance.type`
        model if the `advance_type_id` is provided in the context. Upon creating a new
        record, it updates the corresponding `advance.type` record with the new salary
        rule's ID.
        """
        res = super(HrSalaryRule, self).create(values)
        advance_type_id = self.env.context.get('advance_type_id')
        if advance_type_id:
            self.env['advance.type'].browse(advance_type_id).write({'hr_salary_rule_id': res.id})
        return res
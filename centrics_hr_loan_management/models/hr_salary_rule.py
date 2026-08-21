from odoo import models,fields,api,_


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    is_loan_rule = fields.Boolean(string="Is Loan Rule", help="Flag to indicate if salary rule is a loan rule")

    @api.model
    def create(self, values):
        """
        Handle the creation of HrSalaryRule records with additional logic for loan configuration.

        This method overrides the create method of the HrSalaryRule model.
        If a `loan_configuration_id` is present in the context, it retrieves the corresponding
        employee loan configuration record and associates the newly created salary rule's ID with it.

        Arguments:
            values (dict): A dictionary of values for the record to be created.

        Returns:
            recordset: The newly created HrSalaryRule record.
        """
        res = super(HrSalaryRule, self).create(values)
        loan_type_id = self.env.context.get('loan_type_id')
        if loan_type_id:
            self.env['employee.loan.type'].browse(loan_type_id).write({'hr_salary_rule_id': res.id})
        return res
from odoo import models,fields,api,_
from odoo.exceptions import UserError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    fixed_allowance_deduction_template_id = fields.Many2one('fixed.allowance.deduction.template', string="Fixed Allowance Deduction Template")
    template_adding_option = fields.Selection([('add','Add'),('replace','Replace')], default='add', string='Template Adding Option')
    fixed_allowance_ids = fields.One2many('fixed.allowance.deduction.line', 'hr_contract_allowance_id')
    fixed_deduction_ids = fields.One2many('fixed.allowance.deduction.line', 'hr_contract_deduction_id')

    def action_process_template_info(self):
        """
        Processes the template information to update fixed allowances and deductions.

        This method updates the current fixed allowances and deductions based on the
        selected fixed allowance/deduction template and the template adding option.
        When the template adding option is set to 'replace', it clears the current
        records before applying the ones from the selected template. The processed
        data is then assigned to the fixed allowances and deductions fields.

        Parameters
        ----------
        self : object
            The class instance that calls this method. It should contain the
            following attributes used within this method:
            - fixed_allowance_deduction_template_id: an object representing the
              selected fixed allowance/deduction template.
            - template_adding_option: a string indicating how the template data should
              be applied. Expected values are 'replace' or other.
            - fixed_allowance_ids: a modifiable collection of fixed allowance records.
            - fixed_deduction_ids: a modifiable collection of fixed deduction records.

        Raises
        ------
        None

        Returns
        -------
        None
        """
        if not self.fixed_allowance_deduction_template_id:
            raise UserError(_("Please select a template to process."))
        if self.fixed_allowance_deduction_template_id and self.template_adding_option:
            if self.template_adding_option == 'replace':
                self.fixed_allowance_ids.unlink()
                self.fixed_deduction_ids.unlink()

            allowance_values  = []
            for fixed_allowance_id in self.fixed_allowance_deduction_template_id.fixed_allowance_template_line_ids:
                allowance_values.append((0, 0, {
                    'type_id': fixed_allowance_id.type_id.id,
                    'amount': fixed_allowance_id.amount,
                }))
            self.fixed_allowance_ids = allowance_values

            deduction_values  = []
            for fixed_deduction_id in self.fixed_allowance_deduction_template_id.fixed_deduction_template_line_ids:
                deduction_values.append((0, 0, {
                    'type_id': fixed_deduction_id.type_id.id,
                    'amount': fixed_deduction_id.amount,
                }))
            self.fixed_deduction_ids = deduction_values
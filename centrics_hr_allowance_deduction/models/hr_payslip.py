from odoo import models,fields,api,_


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # @api.depends('employee_id', 'date_from', 'date_to')
    # def _compute_input_line_ids(self):
    #     """
    #     Compute and update input line IDs for payslips based on employee contracts.
    #
    #     This method recalculates the input lines for payslips by considering fixed allowances and deductions
    #     defined in the employee's running contract. It removes any pre-existing fixed allowance or deduction
    #     records from the payslip's input lines before creating new ones based on the contract details. The
    #     updates are performed only for payslips associated with an employee and a valid running contract.
    #
    #     Parameters
    #     ----------
    #     self : HrPayslip
    #         Instance of the payslip on which the input lines need to be computed.
    #
    #     Returns
    #     -------
    #     Any
    #         Returns the result of the superclass method `_compute_input_line_ids`.
    #     """
    #     # Need to get fixed allocations and fixed deductions from Employee Contract
    #     return_obj = super(HrPayslip, self)._compute_input_line_ids()
    #     for payslip in self:
    #         if payslip.employee_id:
    #             running_contract = payslip.contract_id
    #             if payslip.input_line_ids:
    #                 # Remove Fixed Allowance and Fixed Deduction records if exist
    #                 fixed_allowance_deduction_ids = payslip.input_line_ids.filtered(lambda x: x.input_type_id.fixed_type in ['fixed_deduction','fixed_allowance'])
    #                 fixed_allowance_deduction_ids.unlink()
    #             inputs = []
    #             if running_contract:
    #                 fixed_allowance_ids = running_contract.fixed_allowance_ids
    #                 fixed_deduction_ids = running_contract.fixed_deduction_ids
    #                 if fixed_allowance_ids or fixed_deduction_ids:
    #                     for allowance_id in fixed_allowance_ids:
    #                         inputs.append((0, 0, {
    #                             'input_type_id': allowance_id.type_id.input_type_id.id,
    #                             'name': allowance_id.description,
    #                             'amount': allowance_id.amount,
    #                         }))
    #                     for deduction_id in fixed_deduction_ids:
    #                         inputs.append((0, 0, {
    #                             'input_type_id': deduction_id.type_id.input_type_id.id,
    #                             'name': deduction_id.description,
    #                             'amount': -deduction_id.amount,
    #                         }))
    #                     payslip.input_line_ids += inputs
    #
    #     return return_obj

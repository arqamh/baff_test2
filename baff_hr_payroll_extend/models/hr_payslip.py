import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_loan_types(self, company_id):
        """
        Fetches and returns a list of employee loan types associated with the specified
        company.
        """
        return self.env['employee.loan.type'].search([('company_id', '=', company_id)])

    def _get_attendance_records(self, employee_id, date_from, date_to):
        """
        Fetches attendance records for a specific employee over a specified date range.

        This method searches the 'hr.attendance' model to retrieve attendance records
        that match the given employee ID and fall within the specified date range. The
        records are filtered using the 'check_in_date' field.
        """
        return {
            "input_type_id": self.env.ref('baff_hr_payroll_extend.baff_input_attendance_day_count').id,
            "name": "Attendance Count",
            "amount": self.env['hr.attendance'].search_count(
                [('employee_id', '=', employee_id.id), ('check_in_date', '>=', date_from),
                 ('check_in_date', '<=', date_to)])
        }

    def _get_no_of_experience(self, employee_id, date_to):
        """
        Calculates and returns the number of years of experience for a specific
        employee until the given date.
        """
        employee = employee_id
        if employee and employee.joined_date:
            experience_duration = date_to - employee.joined_date
            return {
                "input_type_id": self.env.ref('baff_hr_payroll_extend.input_no_of_experience').id,
                "name": "No of Experience",
                "amount": experience_duration.days // 365
            }
        return {
            "input_type_id": self.env.ref('baff_hr_payroll_extend.input_no_of_experience').id,
            "name": "No of Experience",
            "amount": 0
        }

    def _get_normal_ot_hours(self, employee_id, date_from, date_to):
        """
        Calculates and returns the total normal overtime hours for a specific employee
        based on the criteria defined below:
        1. `employee_id` matches the provided employee_id.
        2. `eligible_for_overtime` is True.
        3. `overtime_approval_status` is 'approved'.
        4. The records fall between `date_from` and `date_to`.
        """
        attendance_records = self.env['hr.attendance'].search([
            ('employee_id', '=', employee_id.id),
            ('eligible_for_overtime', '=', True),
            ('overtime_approval_status', '=', 'approved'),
            ('check_in_date', '>=', date_from),
            ('check_in_date', '<=', date_to)
        ])
        if attendance_records:

            return {
                "input_type_id": self.env.ref('baff_hr_payroll_extend.baff_input_norm_ot_hours').id,
                "name": "Normal Overtime",
                "amount": sum(attendance_records.mapped('normal_overtime'))
            }

        return {
            "input_type_id": self.env.ref('baff_hr_payroll_extend.baff_input_norm_ot_hours').id,
            "name": "Normal Overtime",
            "amount": 0
        }

    def _get_double_ot_hours(self, employee_id, date_from, date_to):
        """
        Calculates and returns the total double overtime hours for a specific employee
        based on the criteria defined below:
        1. `employee_id` matches the provided employee_id.
        2. `eligible_for_overtime` is True.
        3. `overtime_approval_status` is 'approved'.
        4. The records fall between `date_from` and `date_to`.
        """
        attendance_records = self.env['hr.attendance'].search([
            ('employee_id', '=', employee_id.id),
            ('eligible_for_overtime', '=', True),
            ('overtime_approval_status', '=', 'approved'),
            ('check_in_date', '>=', date_from),
            ('check_in_date', '<=', date_to)
        ])
        if attendance_records:
            return {
                "input_type_id": self.env.ref('baff_hr_payroll_extend.baff_input_dbl_ot_hours').id,
                "name" :  "Double Overtime",
                "amount": sum(attendance_records.mapped('double_overtime'))
            }
        return {
            "input_type_id": self.env.ref('baff_hr_payroll_extend.baff_input_dbl_ot_hours').id,
            "name" : "Double Overtime",
            "amount": 0
        }

    def _get_triple_ot_hours(self, employee_id, date_from, date_to):
        """
        Calculates and returns the total triple overtime hours for a specific employee
        based on the criteria defined below:
        1. `employee_id` matches the provided employee_id.
        2. `eligible_for_overtime` is True.
        3. `overtime_approval_status` is 'approved'.
        4. The records fall between `date_from` and `date_to`.
        """
        attendance_records = self.env['hr.attendance'].search([
            ('employee_id', '=', employee_id.id),
            ('eligible_for_overtime', '=', True),
            ('overtime_approval_status', '=', 'approved'),
            ('check_in_date', '>=', date_from),
            ('check_in_date', '<=', date_to)
        ])
        if attendance_records:
            return {
                "input_type_id": self.env.ref('baff_hr_payroll_extend.baff_input_tpl_ot_hours').id,
                "name" : "Triple OT",
                "amount": sum(attendance_records.mapped('triple_overtime'))
            }
        return {
            "input_type_id": self.env.ref('baff_hr_payroll_extend.baff_input_tpl_ot_hours').id,
            "name": "Triple OT",
            "amount": 0
        }

    def _get_no_pay_count(self, employee_id, date_from, date_to):
        """
        Fetches and returns the total no-pay days taken by the employee within the
        specified date range. The leave type must be mapped to a work entry type with
        code 'NOPAY'. Leaves that partially overlap the payslip period are included.
        """
        nopay_work_entry_type = self.env['hr.work.entry.type'].search([('code', '=', 'NOPAY')], limit=1)
        days = 0
        if nopay_work_entry_type:
            leave_types = self.env['hr.leave.type'].search([('work_entry_type_id', '=', nopay_work_entry_type.id)])
            # Use request_date_from/to (Date fields) to avoid Datetime vs Date comparison issues.
            # Overlap condition: leave starts on or before period end AND ends on or after period start.
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee_id.id),
                ('request_date_from', '<=', date_to),
                ('request_date_to', '>=', date_from),
                ('state', '=', 'validate'),
                ('holiday_status_id', 'in', leave_types.ids),
            ])
            days = sum(leaves.mapped('number_of_days'))
        return {
            "input_type_id": self.env.ref('baff_hr_payroll_extend.input_no_pay_days').id,
            "name": "No Pay Days",
            "amount": days,
        }

    def _get_relocation_allowance(self):
        return {
            "input_type_id": self.env.ref('baff_hr_payroll_extend.baff_input_relocation_allowance').id,
            "name" :  "Relocation Allowance",
            "amount": 0
        }

    def _get_leave_balance(self):
        return {
            "input_type_id": self.env.ref('baff_hr_payroll_extend.baff_input_leave_allowance').id,
            "name" : "Leave Balance",
            "amount": 0
        }

    def _get_holiday_count(self, employee_id, date_from, date_to):
        """
        Sums holiday_hours from approved attendance records for the employee within
        the specified date range. Only records where eligible_for_overtime is True
        and overtime_approval_status is 'approved' are considered.
        """
        attendance_records = self.env['hr.attendance'].search([
            ('employee_id', '=', employee_id.id),
            ('eligible_for_overtime', '=', True),
            ('overtime_approval_status', '=', 'approved'),
            ('check_in_date', '>=', date_from),
            ('check_in_date', '<=', date_to),
        ])
        return {
            "input_type_id": self.env.ref('baff_hr_payroll_extend.baff_input_holiday_hours').id,
            "name": "Holiday Count",
            "amount": sum(attendance_records.mapped('holiday_hours')) if attendance_records else 0,
        }

    def get_employee_loans(self, payslip, loan_type=None):
        """
        Retrieves the loan installments associated with the specified employee and loan
        type within the date range defined in the given payslip. The loans must meet
        certain conditions, including being in specified loan stages and having a
        draft status.

        Parameters:
            payslip (Payslip): The payslip record containing the employee and date
                range for the loan search.
            loan_type (Optional[LoanType]): The loan type to filter on. Defaults to
                None, which will not filter by loan type.

        Returns:
            List[LoanInstallment] | None: A list of loan installment line records
            meeting the criteria, or None if no such loans exist.
        """
        employee_loans = self.env['employee.loan.installment.line'].search(
            [('employee_loan_id.employee_id', '=', payslip.employee_id.id),
             ('employee_loan_id.loan_status', 'in', ['paid', 'in_recovery']),
             ('year', '>=', payslip.date_to.year),
             ('month', '>=', payslip.date_from.month),
             ('month', '<=', payslip.date_to.month),
             ('employee_loan_id.loan_type', '=',
              loan_type.id if loan_type else False),
             ('status', '=', 'draft')
             ])
        if not employee_loans:
            return False
        return employee_loans
        
        
    def get_employee_loans_sum(self, loan_type):
        """
        Calculates the total sum of an employee's loans based on the specified loan type.

        This function retrieves loans of a given type for an employee and calculates the
        total amount of installment payments. It returns a dictionary with the associated
        input type ID, the name of the loan type, and the calculated amount.

        Parameters:
        loan_type
            The type of loan for which the total sum needs to be calculated.

        Returns:
        dict
            A dictionary containing:
            - 'input_type_id': ID of the HR payslip input type associated with the loan
              type.
            - 'name': The name of the loan type.
            - 'amount': The total installment amount for the specified loan type.
        """
        employee_loans = self.get_employee_loans(self, loan_type)
        input_type = loan_type.hr_payslip_input_type_id
        if employee_loans and input_type:
            return {
                "input_type_id": input_type.id,
                "name": loan_type.name,
                "amount": sum(employee_loans.mapped('installment_amount'))
            }
        if not input_type:
            return False
        return {
            "input_type_id": input_type.id,
            "name": loan_type.name,
            "amount": 0
        }

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_input_line_ids(self):
        return_obj = super(HrPayslip, self)._compute_input_line_ids()
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                payslip.input_line_ids = [(6, 0, [])]
                year = payslip.date_from.year
                month = payslip.date_from.month
                inputs = []
                loan_types = self._get_loan_types(self.company_id.id)

                attendance_records = self._get_attendance_records(payslip.employee_id, payslip.date_from, payslip.date_to)
                if attendance_records:
                    inputs.append((0, 0, attendance_records))

                normal_ot = self._get_normal_ot_hours(payslip.employee_id, payslip.date_from, payslip.date_to)
                if normal_ot:
                    inputs.append((0, 0, normal_ot))

                double_ot = self._get_double_ot_hours(payslip.employee_id, payslip.date_from, payslip.date_to)
                if double_ot:
                    inputs.append((0, 0, double_ot))

                triple_ot = self._get_triple_ot_hours(payslip.employee_id, payslip.date_from, payslip.date_to)
                if triple_ot:
                    inputs.append((0, 0, triple_ot))

                relocation = self._get_relocation_allowance()
                if relocation:
                    inputs.append((0, 0, relocation))

                experience = self._get_no_of_experience(payslip.employee_id, payslip.date_to)
                if experience:
                    inputs.append((0, 0, experience))

                no_pay = self._get_no_pay_count(payslip.employee_id, payslip.date_from, payslip.date_to)
                if no_pay:
                    inputs.append((0, 0, no_pay))

                leave_balance = self._get_leave_balance()
                if leave_balance:
                    inputs.append((0, 0, leave_balance))

                holiday_count = self._get_holiday_count(payslip.employee_id, payslip.date_from, payslip.date_to)
                if holiday_count:
                    inputs.append((0, 0, holiday_count))

                for loan_type in loan_types:
                    loan_sum = payslip.get_employee_loans_sum(loan_type)
                    if loan_sum:
                        inputs.append((0, 0, loan_sum))

                running_contract = payslip.contract_id
                if running_contract:
                    fixed_allowance_ids = running_contract.fixed_allowance_ids
                    fixed_deduction_ids = running_contract.fixed_deduction_ids
                    if fixed_allowance_ids or fixed_deduction_ids:
                        for allowance_id in fixed_allowance_ids:
                            input_type = allowance_id.type_id.input_type_id
                            if not input_type:
                                _logger.warning(
                                    "Fixed allowance type '%s' has no Input Type configured — "
                                    "skipped for payslip %s (employee: %s).",
                                    allowance_id.type_id.name,
                                    payslip.name,
                                    payslip.employee_id.name,
                                )
                                continue
                            inputs.append((0, 0, {
                                'input_type_id': input_type.id,
                                'name': allowance_id.description,
                                'amount': allowance_id.amount,
                            }))
                        for deduction_id in fixed_deduction_ids:
                            input_type = deduction_id.type_id.input_type_id
                            if not input_type:
                                _logger.warning(
                                    "Fixed deduction type '%s' has no Input Type configured — "
                                    "skipped for payslip %s (employee: %s).",
                                    deduction_id.type_id.name,
                                    payslip.name,
                                    payslip.employee_id.name,
                                )
                                continue
                            inputs.append((0, 0, {
                                'input_type_id': input_type.id,
                                'name': deduction_id.description,
                                'amount': -deduction_id.amount,
                            }))

                payslip.input_line_ids = inputs

        return return_obj

    def action_recall_payslip_input_lines_calculation(self):
        """
        Recalculates the input lines on the payslip.

        This method triggers the recalculation of the input lines IDs on the current payslip by invoking the `
        _compute_input_line_ids` method, ensuring that the payslip's input data is up-to-date.

        Returns:
            bool: Always returns True, indicating the recalculation process has completed successfully.
        """
        self._compute_input_line_ids()
        return True

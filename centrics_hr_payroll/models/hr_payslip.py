from odoo import models, fields, api, _
from odoo.tools import date_utils


class EpfEtfBaseCalculator:
    """
    A callable class that dynamically computes the EPF/ETF base amount.

    This is needed because salary rules are computed sequentially, and the EPF/ETF
    rules need to sum the amounts of previously computed rules that have
    'add_to_calc_epf_etf' = True.

    The localdict contains the computed totals for each rule code (e.g., localdict['BASIC']).
    This class sums those totals for rules marked for EPF/ETF calculation.
    """

    def __init__(self, localdict, epf_etf_rule_codes):
        self.localdict = localdict
        self.epf_etf_rule_codes = epf_etf_rule_codes

    def __call__(self):
        """Compute the sum of all EPF/ETF base rules that have been computed so far."""
        total = 0.0
        for code in self.epf_etf_rule_codes:
            # Get the computed amount from localdict (defaults to 0 if not computed yet)
            total += self.localdict.get(code, 0.0)
        return total


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_epf_etf_base(self):
        """
        Calculate the base amount for EPF/ETF contributions by summing all payslip lines
        that are marked with 'add_to_calc_epf_etf' = True.

        Note: This method is used AFTER payslip computation (when line_ids exist).
        For use DURING computation, use the EpfEtfBaseCalculator in localdict.

        Returns:
            float: The total amount from all rules marked for EPF/ETF calculation
        """
        self.ensure_one()
        total = 0.0

        for line in self.line_ids:
            if line.salary_rule_id and line.salary_rule_id.add_to_calc_epf_etf:
                total += line.total

        return total

    def _get_localdict(self):
        """
        Override to add epf_etf_base callable to the salary rule evaluation context.

        The epf_etf_base is a callable that dynamically computes the sum of all
        previously computed rules that have 'add_to_calc_epf_etf' = True.

        Usage in salary rule Python code:
            result = epf_etf_base() * 0.08
        """
        localdict = super()._get_localdict()

        # Get all rule codes that should be included in EPF/ETF base calculation
        epf_etf_rule_codes = self.struct_id.rule_ids.filtered(
            lambda r: r.add_to_calc_epf_etf
        ).mapped('code')

        # Add the callable to localdict
        localdict['epf_etf_base'] = EpfEtfBaseCalculator(localdict, epf_etf_rule_codes)

        return localdict

    def _compute_worked_days_line_ids(self):
        """
        Override to skip work entry generation when the company setting is enabled.
        """
        if self.company_id.skip_work_entry_validation:
            # Skip work entry generation and validation
            if not self or self.env.context.get('salary_simulation'):
                return
            valid_slips = self.filtered(lambda p: p.employee_id and p.date_from and p.date_to and p.contract_id and p.struct_id)
            if not valid_slips:
                return
            # Make sure to reset invalid payslip's worked days line
            self.update({'worked_days_line_ids': [(5, 0, 0)]})

            for slip in valid_slips:
                if not slip.struct_id.use_worked_day_lines:
                    continue
                # Calculate worked days based on calendar without requiring work entries
                slip.update({'worked_days_line_ids': slip._get_new_worked_days_lines()})
        else:
            # Call the parent method for normal work entry based calculation
            return super(HrPayslip, self)._compute_worked_days_line_ids()

    def _get_worked_day_lines_values(self, domain=None):
        """
        Override to calculate worked days from calendar when work entries are skipped.
        """
        self.ensure_one()

        if self.company_id.skip_work_entry_validation:
            res = []
            hours_per_day = self._get_worked_day_lines_hours_per_day()

            # Get the default work entry type for attendance
            work_entry_type_attendance = self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False)
            if not work_entry_type_attendance:
                # Fallback: get any attendance type
                work_entry_type_attendance = self.env['hr.work.entry.type'].search([('code', '=', 'WORK100')], limit=1)

            if work_entry_type_attendance and self.contract_id.resource_calendar_id:
                # Calculate work hours from calendar
                calendar = self.contract_id.resource_calendar_id
                work_data = calendar.get_work_duration_data(
                    fields.Datetime.to_datetime(self.date_from),
                    fields.Datetime.to_datetime(self.date_to),
                    compute_leaves=True
                )

                hours = work_data.get('hours', 0)
                days = round(hours / hours_per_day, 5) if hours_per_day else 0

                attendance_line = {
                    'sequence': work_entry_type_attendance.sequence,
                    'work_entry_type_id': work_entry_type_attendance.id,
                    'number_of_days': days,
                    'number_of_hours': hours,
                }
                res.append(attendance_line)

            return res
        else:
            # Call the parent method for normal work entry based calculation
            return super(HrPayslip, self)._get_worked_day_lines_values(domain=domain)



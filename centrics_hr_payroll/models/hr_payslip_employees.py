# -*- coding: utf-8 -*-

from odoo import models, _


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _check_undefined_slots(self, work_entries, payslip_run):
        """
        Override to skip work entry validation when company setting is enabled.
        """
        if self.env.company.skip_work_entry_validation:
            # Skip the validation entirely
            return
        else:
            # Call parent method for normal validation
            return super(HrPayslipEmployees, self)._check_undefined_slots(work_entries, payslip_run)

    def compute_sheet(self):
        """
        Override to skip work entry generation when company setting is enabled.
        """
        if self.env.company.skip_work_entry_validation:
            # Modified version that skips work entry generation
            self.ensure_one()
            if not self.env.context.get('active_id'):
                from datetime import datetime
                from dateutil.relativedelta import relativedelta
                from odoo import fields
                from odoo.tools import format_date
                from odoo.exceptions import UserError

                from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
                end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
                today = fields.date.today()
                first_day = today + relativedelta(day=1)
                last_day = today + relativedelta(day=31)
                if from_date == first_day and end_date == last_day:
                    batch_name = from_date.strftime('%B %Y')
                else:
                    batch_name = _('From %s to %s', format_date(self.env, from_date), format_date(self.env, end_date))
                payslip_run = self.env['hr.payslip.run'].create({
                    'name': batch_name,
                    'date_start': from_date,
                    'date_end': end_date,
                })
            else:
                payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

            employees = self.with_context(active_test=False).employee_ids
            if not employees:
                raise UserError(_("You must select employee(s) to generate payslip(s)."))

            # Prevent a payslip_run from having multiple payslips for the same employee
            employees -= payslip_run.slip_ids.employee_id
            success_result = {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payslip.run',
                'views': [[False, 'form']],
                'res_id': payslip_run.id,
            }
            if not employees:
                return success_result

            Payslip = self.env['hr.payslip']
            contracts = employees._get_contracts(
                payslip_run.date_start, payslip_run.date_end, states=['open', 'close']
            ).filtered(lambda c: c.active)

            # SKIP: contracts.generate_work_entries() when setting is enabled
            # SKIP: work entry validation when setting is enabled

            default_values = Payslip.default_get(Payslip.fields_get())
            payslips_vals = []
            for contract in self._filter_contracts(contracts):
                values = dict(default_values, **{
                    'name': _('New Payslip'),
                    'employee_id': contract.employee_id.id,
                    'payslip_run_id': payslip_run.id,
                    'date_from': payslip_run.date_start,
                    'date_to': payslip_run.date_end,
                    'contract_id': contract.id,
                    'struct_id': self.structure_id.id or contract.structure_type_id.default_struct_id.id,
                })
                payslips_vals.append(values)
            payslips = Payslip.with_context(tracking_disable=True).create(payslips_vals)
            payslips._compute_name()
            payslips.compute_sheet()
            payslip_run.state = 'verify'

            return success_result
        else:
            # Call parent method for normal flow
            return super(HrPayslipEmployees, self).compute_sheet()

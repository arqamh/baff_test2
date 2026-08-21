from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BAFFPayslipReport(models.AbstractModel):
    _name = 'report.baff_hr_payroll_extend.baff_payslip_report'
    _description = 'BAFF Payslip Report'

    # this function get supplier monthly payroll data
    def _get_supplier_for_the_month(self, batch_id, payment_method, routes):
        res = []
        for route in routes:
            payslips = self.env['supplier.payroll'].search(
                [('batch_id', '=', batch_id), ('payment_method', '=', payment_method), ('route', '=', route),
                 ('weight', '>', 0)], order='supplier_no')
            [res.append(payslip) for payslip in sorted(payslips, key=lambda x: int(x.supplier_no))]
        return res

    # get pdf report values
    @api.model
    def _get_report_values(self, docids, data=None):
        if data.get('form'):
            records = self.env['hr.payslip.run'].browse(data.get('form').get('batch_id')[0]).slip_ids
        else:
            records = self.env['hr.payslip'].browse(docids)
        records_list = [records[x:x + 2] for x in range(0, len(records), 2)]
        baff_payroll_report = self.env['ir.actions.report']._get_report_from_name('baff_hr_payroll_extend.baff_payslip_report')
        return {
            'doc_ids': self.ids,
            'doc_model': baff_payroll_report.model,
            'docs': records_list
        }

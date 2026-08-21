# -*- coding: utf-8 -*-
import io
import base64
from odoo import fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False

# ── Column definitions (col_number, label) ────────────────────────────────────

_STAFF_HEADERS = [
    (1,  'EPF\nNo'),
    (2,  'Name'),
    (3,  'Designation'),
    (4,  'Holiday\nHours'),
    (5,  'Basic\nSalary'),
    (6,  'N. OT\nHours'),
    (7,  'Rate'),
    (8,  'OT\nAmount'),
    (9,  'Nopay\nDays'),
    (10, 'Holiday\nPayment\nAmount'),
    (11, 'Special\nIncentive'),
    (12, 'Special\nAllowance'),
    (13, 'Attendance\nAllowance'),
    (14, 'Salary\nAdjsment'),
    (15, 'Gross\nSalary'),
    (16, 'Salary\nAdvance'),
    (17, 'Loan'),
    (18, 'Suwa\nSampatha'),
    (19, 'Team Help\nfund'),
    (20, 'E.P.F\n8%'),
    (21, 'APIT'),
    (22, 'Nopay\nAmount'),
    (23, 'Total\nDedu:'),
    (24, 'Net\nSalary'),
]

_NON_STAFF_HEADERS = [
    (1,  'EPF\nNo'),
    (2,  'Name'),
    (3,  'Designation'),
    (4,  'Holiday\nHours'),
    (5,  'Basic\nSalary'),
    (6,  'N. OT\nHours'),
    (7,  'Rate'),
    (8,  'D. OT\nHours'),
    (9,  'Rate'),
    (10, 'T.OT\nHours'),
    (11, 'Rate'),
    (12, 'OT\nAmount'),
    (13, 'Nopay\nDays'),
    (14, 'Holiday\nPayment'),
    (15, 'Leader\nAllowance'),
    (16, 'Attentance\nAllowance'),
    (17, 'Relocation\nPayment'),
    (18, 'Salary\nAdjsment'),
    (19, 'Gross\nSalary'),
    (20, 'Salary\nAdvance'),
    (21, 'Loan'),
    (22, 'Suwa\nSampatha'),
    (23, 'Team\nHelp\nFund'),
    (24, 'E.P.F 8%'),
    (25, 'APIT'),
    (26, 'Nopay'),
    (27, 'Total\nDedu:'),
    (28, 'Net\nSalary'),
]

# DED codes that have their own columns — excluded from loan residual
_KNOWN_DED_CODES = frozenset({
    'SAL_ADV', 'TEAM_HELP', 'EPF_EE_8', 'PAYE_TAX',
    'NOPAY_DED', 'TOT_DED', 'SUWA_SAMP',
})


class HrSalarySheetWizard(models.TransientModel):
    _name = 'hr.salary.sheet.wizard'
    _description = 'Salary Sheet Report'

    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payroll Batch',
        required=True,
    )
    employee_category = fields.Selection(
        [('staff', 'Staff'), ('non_staff', 'Non Staff')],
        string='Employee Category',
        required=True,
    )

    # ── data helpers ──────────────────────────────────────────────────────────

    def _line(self, payslip, code):
        """Absolute total of a salary rule line."""
        lines = payslip.line_ids.filtered(lambda l: l.code == code)
        return abs(sum(lines.mapped('total'))) if lines else 0.0

    def _net(self, payslip, code):
        """Signed total — used for Net Salary."""
        lines = payslip.line_ids.filtered(lambda l: l.code == code)
        return sum(lines.mapped('total')) if lines else 0.0

    def _inp(self, payslip, code):
        """Amount from a payslip input line."""
        inputs = payslip.input_line_ids.filtered(
            lambda i: i.input_type_id.code == code
        )
        return abs(sum(inputs.mapped('amount'))) if inputs else 0.0

    def _loan_amount(self, payslip):
        """Sum loan deductions via salary rules linked on employee.loan.type."""
        loan_types = self.env['employee.loan.type'].search([
            ('company_id', '=', payslip.company_id.id),
            ('hr_salary_rule_id', '!=', False),
        ])
        loan_codes = set(loan_types.mapped('hr_salary_rule_id.code'))
        return abs(sum(
            l.total for l in payslip.line_ids if l.code in loan_codes
        ))

    # ── row builders ──────────────────────────────────────────────────────────

    def _staff_row(self, payslip):
        e = payslip.employee_id
        c = payslip.contract_id
        return [
            e.epf_number or '',
            e.name,
            e.job_id.name or '',
            self._inp(payslip, 'HOL_HRS'),
            self._line(payslip, 'BAFF_BASIC'),
            self._inp(payslip, 'NORM_OT_HRS'),
            c.baff_ot_rate_normal,
            self._line(payslip, 'NORM_OT_AMT'),
            self._inp(payslip, 'NOPAY'),
            self._line(payslip, 'HOL_AMT'),
            self._line(payslip, 'SPEC_INCNTV'),
            self._line(payslip, 'SPEC_ALLW'),
            self._line(payslip, 'ATTND_ALLW'),
            self._line(payslip, 'SAL_ADJ'),
            self._line(payslip, 'BAFF_GROSS'),
            self._line(payslip, 'SAL_ADV'),
            self._loan_amount(payslip),
            self._line(payslip, 'SUWA_SAMP'),
            self._line(payslip, 'TEAM_HELP'),
            self._line(payslip, 'EPF_EE_8'),
            self._line(payslip, 'PAYE_TAX'),
            self._line(payslip, 'NOPAY_DED'),
            self._line(payslip, 'TOT_DED'),
            self._net(payslip, 'BAFF_NET'),
        ]

    def _non_staff_row(self, payslip):
        e = payslip.employee_id
        c = payslip.contract_id
        ot_total = (
            self._line(payslip, 'NORM_OT_AMT')
            + self._line(payslip, 'DBL_OT_AMT')
            + self._line(payslip, 'TRPL_OT_AMT')
        )
        return [
            e.epf_number or '',
            e.name,
            e.job_id.name or '',
            self._inp(payslip, 'HOL_HRS'),
            self._line(payslip, 'BAFF_BASIC'),
            self._inp(payslip, 'NORM_OT_HRS'),
            c.baff_ot_rate_normal,
            self._inp(payslip, 'DBL_OT_HRS'),
            c.baff_ot_rate_double,
            self._inp(payslip, 'TRPL_OT_HRS'),
            c.baff_ot_rate_triple,
            ot_total,
            self._inp(payslip, 'NOPAY'),
            self._line(payslip, 'HOL_AMT'),
            self._line(payslip, 'LDR_ALLW'),
            self._line(payslip, 'ATTND_ALLW'),
            self._line(payslip, 'REL_ALLW'),
            self._line(payslip, 'SAL_ADJ'),
            self._line(payslip, 'BAFF_GROSS'),
            self._line(payslip, 'SAL_ADV'),
            self._loan_amount(payslip),
            self._line(payslip, 'SUWA_SAMP'),
            self._line(payslip, 'TEAM_HELP'),
            self._line(payslip, 'EPF_EE_8'),
            self._line(payslip, 'PAYE_TAX'),
            self._line(payslip, 'NOPAY_DED'),
            self._line(payslip, 'TOT_DED'),
            self._net(payslip, 'BAFF_NET'),
        ]

    # ── Excel builder ─────────────────────────────────────────────────────────

    def _build_excel(self, payslips, headers, row_fn, title):
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Salary Sheet')
        col_count = len(headers)

        # ── formats ──
        title_fmt = wb.add_format({
            'bold': True, 'font_size': 14,
            'align': 'center', 'valign': 'vcenter',
        })
        subtitle_fmt = wb.add_format({
            'bold': True, 'font_size': 12,
            'align': 'center', 'valign': 'vcenter',
        })
        hdr_fmt = wb.add_format({
            'bold': True, 'bg_color': '#ED7D31', 'font_color': '#FFFFFF',
            'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'border': 1,
        })
        text_fmt = wb.add_format({
            'align': 'left', 'valign': 'vcenter', 'border': 1,
        })
        num_fmt = wb.add_format({
            'num_format': '#,##0.00', 'align': 'right',
            'valign': 'vcenter', 'border': 1,
        })
        total_lbl_fmt = wb.add_format({
            'bold': True, 'align': 'left', 'valign': 'vcenter', 'border': 1,
        })
        total_num_fmt = wb.add_format({
            'bold': True, 'num_format': '#,##0.00',
            'align': 'right', 'valign': 'vcenter', 'border': 1,
        })

        # ── row 0: company name ──
        ws.merge_range(0, 0, 0, col_count - 1, self.env.company.name, title_fmt)
        ws.set_row(0, 22)

        # ── row 1: report title ──
        ws.merge_range(1, 0, 1, col_count - 1, title, subtitle_fmt)
        ws.set_row(1, 20)

        # ── row 2: column numbers ──
        for ci, (num, _) in enumerate(headers):
            ws.write(2, ci, num, hdr_fmt)
        ws.set_row(2, 18)

        # ── row 3: column labels ──
        for ci, (_, lbl) in enumerate(headers):
            ws.write(3, ci, lbl, hdr_fmt)
        ws.set_row(3, 48)

        # ── data rows ──
        totals = [0.0] * col_count
        row = 4
        for payslip in payslips.sorted(key=lambda p: p.employee_id.name):
            values = row_fn(payslip)
            for ci, val in enumerate(values):
                if isinstance(val, (int, float)):
                    ws.write_number(row, ci, val, num_fmt)
                    totals[ci] += val
                else:
                    ws.write(row, ci, val or '', text_fmt)
            row += 1

        # ── totals row ──
        ws.write(row, 0, 'Total', total_lbl_fmt)
        ws.write(row, 1, '', total_lbl_fmt)
        ws.write(row, 2, '', total_lbl_fmt)
        for ci in range(3, col_count):
            if totals[ci]:
                ws.write_number(row, ci, totals[ci], total_num_fmt)
            else:
                ws.write(row, ci, '', total_lbl_fmt)

        # ── column widths ──
        ws.set_column(0, 0, 8)   # EPF No
        ws.set_column(1, 1, 24)  # Name
        ws.set_column(2, 2, 16)  # Designation
        ws.set_column(3, col_count - 1, 11)

        wb.close()
        output.seek(0)
        return output.read()

    # ── action ────────────────────────────────────────────────────────────────

    def action_generate_report(self):
        if not HAS_XLSXWRITER:
            raise UserError(_(
                'The xlsxwriter Python library is required. '
                'Install it with: pip install xlsxwriter'
            ))

        payslips = self.payslip_run_id.slip_ids.filtered(
            lambda p: (
                p.employee_id.ocean_voyager_emp_category == self.employee_category
                and p.state != 'cancel'
            )
        )
        if not payslips:
            raise UserError(_(
                'No confirmed payslips found for the selected batch '
                'and employee category.'
            ))

        run = self.payslip_run_id
        month_name = run.date_start.strftime('%B')
        year = run.date_start.strftime('%Y')

        if self.employee_category == 'staff':
            headers = _STAFF_HEADERS
            row_fn = self._staff_row
            title = f'Staff Salary Sheet Month of {month_name} {year}'
            filename = f'staff_salary_sheet_{month_name}_{year}.xlsx'
        else:
            headers = _NON_STAFF_HEADERS
            row_fn = self._non_staff_row
            title = f'Non-Staff Salary Sheet Month of {month_name} {year}'
            filename = f'non_staff_salary_sheet_{month_name}_{year}.xlsx'

        xlsx_data = self._build_excel(payslips, headers, row_fn, title)

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': (
                'application/vnd.openxmlformats-officedocument'
                '.spreadsheetml.sheet'
            ),
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO
from datetime import datetime


class ETFContributionReportWizard(models.TransientModel):
    """
    ETF Contribution Report Wizard

    Transient model to generate ETF (Employees' Trust Fund) contribution reports
    in Excel format for selected payroll batches.

    The report includes only EPF-eligible employees and extracts ETF contribution
    amounts from salary rules configured with etf_3 flag.
    """
    _name = 'etf.contribution.report.wizard'
    _description = 'ETF Contribution Report Wizard'

    payslip_batch_ids = fields.Many2many(
        'hr.payslip.run',
        string='Payroll Batches',
        required=True,
        help='Select the payroll batches for ETF contribution report. '
             'Only payslips from EPF-eligible employees will be included.'
    )

    def action_generate_excel(self):
        """
        Generate ETF Contribution Excel file

        This method generates an Excel report containing ETF (Employees' Trust Fund)
        contribution details for selected payroll batches.

        Process:
        1. Get all payslips from selected payroll batches
        2. Filter payslips where:
           - Payslip state is 'done'
           - Employee is eligible for EPF (is_provident_fund_eligible = True)
        3. For each eligible payslip, extract salary rules with etf_3 configuration
        4. Generate Excel file with the following columns:
           - Member Number (employee.epf_number)
           - Members Initials (employee.name_initials)
           - Members Surname (employee.last_name)
           - NIC Number (employee.identification_id)
           - Contribution (sum of etf_3 salary rule amounts)

        Returns:
            dict: Action to download the generated Excel file

        Raises:
            UserError: If no payroll batches are selected or xlsxwriter is not installed
        """
        if not self.payslip_batch_ids:
            raise UserError(_('Please select at least one Payroll Batch.'))

        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('xlsxwriter library is not installed. Please install it to generate Excel reports.'))

        # Create Excel file in memory
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('ETF Contribution')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        # Define headers
        headers = [
            'Member Number',
            'Members Initials',
            'Members Surname',
            'NIC Number',
            'Contribution'
        ]

        # Write headers
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, 20)

        # Get payslips from all selected batches
        # Filter by:
        # 1. Payslip state must be 'done'
        # 2. Employee must be eligible for EPF (is_provident_fund_eligible = True)
        payslips = self.payslip_batch_ids.mapped('slip_ids').filtered(
            lambda p: p.state == 'done' and p.employee_id.is_provident_fund_eligible
        )

        # Write data
        row = 0
        for payslip in payslips:
            employee = payslip.employee_id

            # Member Number (EPF Number)
            member_number = employee.epf_number or ''

            # Members Initials
            initials = employee.name_initials or ''

            # Members Surname (Last Name)
            surname = employee.last_name or ''

            # NIC Number
            nic_number = employee.identification_id or ''

            # Calculate ETF Contribution (3%)
            # Find salary rule lines with etf_3 configuration enabled
            etf_3_lines = payslip.line_ids.filtered(lambda l: l.salary_rule_id.etf_3)
            contribution = sum(etf_3_lines.mapped('total'))

            # Write row data
            row += 1
            worksheet.write(row, 0, member_number, data_format)
            worksheet.write(row, 1, initials, data_format)
            worksheet.write(row, 2, surname, data_format)
            worksheet.write(row, 3, nic_number, data_format)
            worksheet.write(row, 4, contribution, data_format)

        workbook.close()
        output.seek(0)
        excel_file = base64.b64encode(output.read())
        output.close()

        # Generate filename
        current_date = datetime.now().strftime('%Y%m%d')
        if len(self.payslip_batch_ids) == 1:
            batch_name = self.payslip_batch_ids.name.replace('/', '_').replace(' ', '_')
        else:
            batch_name = 'Multiple_Batches'
        filename = f'{batch_name}_etf_contribution_{current_date}.xlsx'

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': excel_file,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO
from datetime import datetime


class EPFContributionReportWizard(models.TransientModel):
    """
    EPF Contribution Report Wizard

    Transient model to generate EPF (Employees' Provident Fund) contribution reports
    in Excel format for selected payroll batches.

    The report includes only EPF-eligible employees and extracts:
    - Employer's contribution (12%) from salary rules with epf_12 flag
    - Member's contribution (8%) from salary rules with epf_8 flag
    - Total earnings from salary rules with add_to_calc_epf_etf flag
    - Attendance-based days worked count
    """
    _name = 'epf.contribution.report.wizard'
    _description = 'EPF Contribution Report Wizard'

    payslip_batch_ids = fields.Many2many(
        'hr.payslip.run',
        string='Payroll Batches',
        required=True,
        help='Select the payroll batches for EPF contribution report. '
             'Only payslips from EPF-eligible employees will be included.'
    )

    def action_generate_excel(self):
        """
        Generate EPF Contribution Excel file

        This method generates an Excel report containing EPF (Employees' Provident Fund)
        contribution details for selected payroll batches.

        Process:
        1. Get all payslips from selected payroll batches
        2. Filter payslips where:
           - Payslip state is 'done'
           - Employee is eligible for EPF (is_provident_fund_eligible = True)
        3. For each eligible payslip, extract:
           - Employer's Contribution: salary rules with epf_12 configuration
           - Member's Contribution: salary rules with epf_8 configuration
           - Total Earnings: salary rules with add_to_calc_epf_etf configuration
           - Days Worked: count of hr.attendance records in payslip period
        4. Generate Excel file with 15 columns as per EPF reporting format

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
        worksheet = workbook.add_worksheet('EPF Contribution')

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
            'NIC/Passport Number',
            'Last Name',
            'Initials',
            'Member AC Number',
            'Total Contribution',
            "Employer's Contribution",
            "Member's Contribution",
            'Total Earnings',
            'Member Status E=Extg. N=New V=Vacated',
            'Zone code',
            'Employer Number',
            'Contribution Year & Month',
            'Data Submission Number',
            'No of Days Worked',
            'Occupation Classification Grade'
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

        # Get company EPF details
        company = self.env.company
        zone_code = company.epf_zone_code or ''
        employer_number = company.epf_employer_number or ''

        # Write data
        row = nic_passport = last_name = initials = member_ac_number = ''
        total_contribution = employer_contribution = member_contribution = 0.0
        total_earnings = 0.0
        member_status = ''
        contribution_year_month = ''
        data_submission_number = ''
        no_of_days_worked = 0
        occupation_grade = ''

        for payslip in payslips:
            row += 1
            employee = payslip.employee_id

            # NIC/Passport Number
            nic_passport = employee.identification_id or ''

            # Last Name and Initials
            last_name = employee.last_name or ''
            initials = employee.name_initials or ''

            # Member AC Number (EPF Number)
            member_ac_number = employee.epf_number or ''

            # Calculate contributions from payslip lines
            # Employer's Contribution (12%)
            epf_12_lines = payslip.line_ids.filtered(lambda l: l.salary_rule_id.epf_12)
            employer_contribution = sum(epf_12_lines.mapped('total'))

            # Member's Contribution (8%)
            epf_8_lines = payslip.line_ids.filtered(lambda l: l.salary_rule_id.epf_8)
            member_contribution = sum(epf_8_lines.mapped('total'))

            # Total Contribution
            total_contribution = employer_contribution + member_contribution

            # Total Earnings - Sum of salary rules with add_to_calc_epf_etf configuration
            epf_etf_earnings_lines = payslip.line_ids.filtered(lambda l: l.salary_rule_id.add_to_calc_epf_etf)
            total_earnings = sum(epf_etf_earnings_lines.mapped('total'))

            # Member Status - From EPF Employment Type code
            member_status = employee.epf_employment_type_id.code if employee.epf_employment_type_id else ''

            # Contribution Year & Month (Format: YYYYMM)
            if payslip.date_from:
                contribution_year_month = payslip.date_from.strftime('%Y%m')
            else:
                contribution_year_month = ''

            # Data Submission Number (always 1)
            data_submission_number = '1'

            # No of Days Worked - Count attendance records for the payslip period
            attendance_count = self.env['hr.attendance'].search_count([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', payslip.date_from),
                ('check_in', '<=', payslip.date_to)
            ])
            no_of_days_worked = attendance_count

            # Occupation Classification Grade - From Occupational Group code
            occupation_grade = employee.occupational_group_id.code if employee.occupational_group_id else ''

            # Write row data
            worksheet.write(row, 0, nic_passport, data_format)
            worksheet.write(row, 1, last_name, data_format)
            worksheet.write(row, 2, initials, data_format)
            worksheet.write(row, 3, member_ac_number, data_format)
            worksheet.write(row, 4, total_contribution, data_format)
            worksheet.write(row, 5, employer_contribution, data_format)
            worksheet.write(row, 6, member_contribution, data_format)
            worksheet.write(row, 7, total_earnings, data_format)
            worksheet.write(row, 8, member_status, data_format)
            worksheet.write(row, 9, zone_code, data_format)
            worksheet.write(row, 10, employer_number, data_format)
            worksheet.write(row, 11, contribution_year_month, data_format)
            worksheet.write(row, 12, data_submission_number, data_format)
            worksheet.write(row, 13, no_of_days_worked, data_format)
            worksheet.write(row, 14, occupation_grade, data_format)

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
        filename = f'{batch_name}_epf_contribution_{current_date}.xlsx'

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

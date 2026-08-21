from odoo import fields, models, api, _
import xlsxwriter
import base64


class FixedAssetWizard(models.TransientModel):
    _name = 'fixed.asset.report'
    _description = "Fixed Asset"

    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")

    def action_print_report(self):
        """generate xlsx report and convert into a file"""
        file = self.print_fixed_asset_report()
        open_file = open(file, 'rb+')
        document = open_file.read()
        values = {
            'name': file,
            'res_model': 'ir.ui.view',
            'res_id': False,
            'type': 'binary',
            'public': True,
            'datas': base64.b64encode(document),
        }
        attachment_id = self.env['ir.attachment'].sudo().create(values)
        download_url = '/web/content/' + str(attachment_id.id) + '?download=True'
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }

    def print_fixed_asset_report(self):
        """Generating Fixed Asset report"""
        # Setting name for the report
        report = 'Fixed Asset Report' + '.xlsx'
        workbook = xlsxwriter.Workbook(report)

        # Create worksheet
        worksheet = workbook.add_worksheet('Fixed Asset Report')
        worksheet.set_landscape()

        # Design styles
        title = workbook.add_format({'align': 'left', 'bold': False, 'font_size': 10, 'font_name': 'Times New Roman'})
        title1 = workbook.add_format({'align': 'left', 'bold': False, 'font_size': 10})
        title2 = workbook.add_format({'align': 'left', 'bold': True, 'font_size': 15, 'font_name': 'Times New Roman'})

        center_text_format_bold = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'size': 10, 'border': 1, 'font_name': 'Times New Roman', 'text_wrap': True})
        center_text_format_bold1 = workbook.add_format({'align': 'left', 'bold': True, 'size': 11, 'font_name': 'Times New Roman'})
        center_text_format_bold2 = workbook.add_format({'align': 'center', 'bold': True, 'size': 11, 'font_name': 'Times New Roman'})

        row = 0
        col = 0

        row_number = 36

        # Create Total for line
        border_format = workbook.add_format({'top': 1, 'top_color': 'black'})

        # Define the range of columns from H to T
        start_col = 7
        end_col = 19

        # Apply the single line into the cells
        for col in range(start_col, end_col + 1):
            worksheet.write(row_number, col, '', border_format)

        row_number = 37

        # Create Total for double line
        double_border_format = workbook.add_format({'top': 6, 'top_color': 'black'})

        # Define the range of columns from H to T
        start_col = 7
        end_col = 19

        # Apply the double line into the cells
        for col in range(start_col, end_col + 1):
            worksheet.write(row_number, col, '', double_border_format)

        worksheet.freeze_panes(4, 0)

        # Write data on the worksheet
        worksheet.write('A2', 'BAFF POLYMECH PVT LTD', title)
        worksheet.write('A3', 'PROPERTY PLANT & EQUIPMENT', title)
        worksheet.merge_range('G10:I10', 'Summary of Depreciation-2022/23', title2)
        worksheet.write('H11', 'Apr-22', center_text_format_bold2)
        worksheet.write('I11', 'May-22', center_text_format_bold2)
        worksheet.write('J11', 'Jun-22', center_text_format_bold2)
        worksheet.write('K11', 'Jul-22', center_text_format_bold2)
        worksheet.write('L11', 'Aug-22', center_text_format_bold2)
        worksheet.write('M11', 'Sep-22', center_text_format_bold2)
        worksheet.write('N11', 'Oct-22', center_text_format_bold2)
        worksheet.write('O11', 'Nov-22', center_text_format_bold2)
        worksheet.write('P11', 'Dec-22', center_text_format_bold2)
        worksheet.write('Q11', 'Jan-23', center_text_format_bold2)
        worksheet.write('R11', 'Feb-23', center_text_format_bold2)
        worksheet.write('S11', 'Mar-23', center_text_format_bold2)
        worksheet.write('T11', 'Total', center_text_format_bold2)
        worksheet.write('G13', 'Buildings', center_text_format_bold1)
        worksheet.write('G16', 'Tools & Equipments', center_text_format_bold1)
        worksheet.write('G19', 'Plant & Machinery', center_text_format_bold1)
        worksheet.write('G22', 'Furnitures & Fittings', center_text_format_bold1)
        worksheet.write('G25', 'Computer & Accessories', center_text_format_bold1)
        worksheet.write('G28', 'Motor Vehicle', center_text_format_bold1)
        worksheet.write('G31', 'Telephone', center_text_format_bold1)
        worksheet.write('G34', 'Intangible Assets', center_text_format_bold1)
        worksheet.write('G37', 'Total', center_text_format_bold1)

        row = 3
        header_row = 2
        col = 0

        row_number = 3
        new_height = 40

        worksheet.set_row(row_number, new_height)

        worksheet.set_column('A:A', 40)
        worksheet.set_column('B:B', 10)
        worksheet.set_column('C:C', 5)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:H', 18)
        worksheet.set_column('I:U', 15)

        worksheet.write(row, col, 'Item', center_text_format_bold)
        worksheet.write(row, col + 1, 'Acquired Date', center_text_format_bold)
        worksheet.write(row, col + 2, 'Rate %', center_text_format_bold)
        worksheet.write(row, col + 3, 'Purchase Price', center_text_format_bold)
        worksheet.write(row, col + 4, 'Written Down Value as at 31.03.2022', center_text_format_bold)
        worksheet.write(row, col + 5, 'Depreciation 2022/23', center_text_format_bold)
        worksheet.write(row, col + 6, 'Monthly Depreciation', center_text_format_bold)
        worksheet.write(row, col + 7, 'Apr-22', center_text_format_bold)
        worksheet.write(row, col + 8, 'May-22', center_text_format_bold)
        worksheet.write(row, col + 9, 'Jun-22', center_text_format_bold)
        worksheet.write(row, col + 10, 'Jul-22', center_text_format_bold)
        worksheet.write(row, col + 11, 'Aug-22', center_text_format_bold)
        worksheet.write(row, col + 12, 'Sep-22', center_text_format_bold)
        worksheet.write(row, col + 13, 'Oct-22', center_text_format_bold)
        worksheet.write(row, col + 14, 'Nov-22', center_text_format_bold)
        worksheet.write(row, col + 15, 'Dec-22', center_text_format_bold)
        worksheet.write(row, col + 16, 'Jan-23', center_text_format_bold)
        worksheet.write(row, col + 17, 'Feb-23', center_text_format_bold)
        worksheet.write(row, col + 18, 'Mar-23', center_text_format_bold)
        worksheet.write(row, col + 19, 'Depreciation 2022/23', center_text_format_bold)
        worksheet.write(row, col + 20, 'Written Down Value as at 31.03.2023', center_text_format_bold)

        # Getting dependent data
        # domain = []
        # if self.date_from and self.date_to:
        #     domain += ['|', '|', '&', ('visa_exp_date', '>=', self.date_from),
        #                ('visa_exp_date', '<=', self.date_to),
        #                '&', ('passport_exp_date', '>=', self.date_from),
        #                ('passport_exp_date', '<=', self.date_to),
        #                '&', ('resident_exp_date', '>=', self.date_from),
        #                ('resident_exp_date', '<=', self.date_to)]

        workbook.close()
        return report
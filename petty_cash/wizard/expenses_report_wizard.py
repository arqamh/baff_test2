from odoo import fields, models, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import xlsxwriter
import base64


class ExpensesReportWizard(models.TransientModel):
    """
    Wizard for expenses report generate
    """
    _name = 'petty.cash.expenses.report.wizard'
    _description = 'Expenses report Wizard'

    start_from = fields.Date(required=True, default=lambda self: datetime.today() - relativedelta(months=1))
    end_from = fields.Date(default=fields.Date.today, required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def data_excel_report(self):
        """Generate data for report from start date to end date"""

        report = 'Shipment Summary Report'
        workbook = xlsxwriter.Workbook(report)
        worksheet = workbook.add_worksheet('Sheet 01')
        worksheet.set_landscape()

        #   styles
        main_header = workbook.add_format({'bold': True, 'align': 'center', 'font_size':15})
        sub_header = workbook.add_format({'align': 'center', 'font_size':11})
        empty_cell = workbook.add_format({'align': 'left', 'border': 1})
        table_header = workbook.add_format({'align': 'center', 'border': 1,'bg_color': '#9d9e9d'})
        table_cate_name = workbook.add_format({'bold': False, 'align': 'center','bg_color': '#e6e6e6', 'border': 1})
        table_cate_currency= workbook.add_format({'bold': False, 'align': 'center','bg_color': '#e6e6e6', 'border': 1, 'num_format': '#,##0.00'})
        table_data = workbook.add_format({'bold': False, 'align': 'left', 'border': 1})
        table_currency = workbook.add_format({'bold': False, 'align': 'right', 'border': 1, 'num_format': '#,##0.00'})
        table_total_currency = workbook.add_format({'bold': False, 'align': 'right', 'border': 1, 'bg_color': '#9d9e9d', 'num_format': '#,##0.00'})

        total_title = workbook.add_format({'bold': False, 'align': 'left'})
        total_currency = workbook.add_format({'bold': False, 'align': 'right', 'bg_color': '#e6e6e6', 'num_format': '#,##0.00'})
        border_bottom = workbook.add_format({'bottom': 2, 'align': 'right', 'bg_color': '#e6e6e6', 'num_format': '#,##0.00'})
        ref_no_class = workbook.add_format({'border': 1, 'align': 'center'})



        worksheet.set_column("A:A", 15)
        worksheet.set_column("C:C", 50)
        worksheet.set_column("D:D", 20)

        worksheet.set_row(3, 20)

        today = datetime.today()
        today = today.strftime("%d-%b-%Y")
        worksheet.write("A2", today)
        worksheet.write("C2", self.company_id.name, main_header)
        worksheet.write("C3", "Petty cash expenses - %s to %s" % (self.start_from.strftime("%d-%b-%Y"), self.end_from.strftime("%d-%b-%Y")), sub_header)

        #   table header
        worksheet.write("A4", "Date", table_header)
        worksheet.write("B4", "Ref No", table_header)
        worksheet.write("C4", "Description", table_header)
        worksheet.write("D4", "Amount", table_header)

        expenses = self.env.ref('account.data_account_type_expenses').id
        expenses_accounts = self.env['account.account'].search([('user_type_id', '=', expenses)])

        account_dict = {}
        for account in expenses_accounts:
            # accounts list
            account_dict[account.id] = (account.name, [])

        start_date = self.start_from.strftime("%Y-%m-%d 00:00:00")
        start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")

        end_date = self.end_from.strftime("%Y-%m-%d 23:59:59")
        end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        reimbursements = self.env['petty.cash.out'].search([('cash_date', '>', start_date), ('cash_date', '<', end_date),('state', '=', 'complete')], order="cash_date asc")

        for reimb in reimbursements:
            for line in reimb.expenses_line:
                account_dict.get(line.expense_account_id.id)[1].append(
                    {
                        'date': reimb.cash_date,
                        'description': line.name,
                        'amount': line.amount,
                    }
                )

        iou_requests = self.env['petty.cash.release'].search([('release_date', '>', start_date), ('release_date', '<', end_date), ('state', '=', 'complete')], order="release_date asc")

        total_advanced = 0.00

        for iou in iou_requests:
            for line in iou.expenses_line:
                account_dict.get(line.expense_account_id.id)[1].append(
                    {
                        'date': iou.release_date,
                        'description': line.name,
                        'amount': line.amount,
                    }
                )
            total_advanced += iou.balanced_amount

        def change_order(lists):
            # change value to date order
            return lists['date']

        # change dict order
        for value in account_dict.values():
            value[1].sort(key=change_order)

        row_no = 5
        ref_no = 0
        report_total = 0.00
        for rec in account_dict.values():
            category_total = 0.00
            if rec[1]:
                cat_row_no = row_no
                worksheet.merge_range("A%d:C%d" % (row_no, row_no), rec[0], table_cate_name)
                for amount in rec[1]:
                    row_no += 1
                    ref_no += 1
                    worksheet.write("A%d" % row_no, amount["date"].strftime("%d-%b-%Y"), table_data)
                    worksheet.write("B%d" % row_no, ref_no, ref_no_class)
                    worksheet.write("C%d" % row_no, amount["description"], table_data)
                    worksheet.write("D%d" % row_no, amount["amount"], table_currency)
                    category_total += amount['amount']
                worksheet.write("D%d" % cat_row_no, category_total, table_cate_currency)
                row_no += 1

            report_total += category_total

        worksheet.merge_range("A%d:D%d" % (row_no, row_no), report_total, table_total_currency)

        #   Total Opening Balance
        topups = self.env['petty.cash.in'].search(
            [('cash_date', '>', start_date), ('cash_date', '<', end_date)], order="cash_date asc")
        opening_balance = 0.00
        for topup in topups:
            opening_balance += topup.amount
        row_no += 2
        worksheet.write("C%d" % row_no, "Opening Balance", total_title)
        worksheet.write("D%d" % row_no, opening_balance, total_currency)
        row_no += 1
        worksheet.write("C%d" % row_no, "Cash Reimbursement", total_title)
        worksheet.write("D%d" % row_no, report_total, total_currency)
        row_no += 1
        worksheet.write("C%d" % row_no, "Cash Advances", total_title)
        worksheet.write("D%d" % row_no, total_advanced, border_bottom)
        row_no += 1
        worksheet.write("C%d" % row_no, "Cash in Hand", total_title)
        worksheet.write("D%d" % row_no, opening_balance - report_total, border_bottom)

        row_no += 1
        worksheet.set_row(row_no-1, 30)
        worksheet.write("C%d" % row_no, "Prepared By", total_title)
        row_no += 1
        worksheet.set_row(row_no - 1, 30)
        worksheet.write("C%d" % row_no, "Checked By", total_title)

        workbook.close()
        return report

    def download_report(self):
        """Get the report type from the context and downloads the report"""

        self.ensure_one()
        if self.start_from > self.end_from:
            raise ValidationError(_("Start Date must be less Than End Date"))
        else:
            report = self.data_excel_report()
            my_report_data = open(report, 'rb+')
            f = my_report_data.read()
            values = {
                'name': 'Petty Cash Expenses',
                'res_model': 'ir.ui.view',
                'res_id': False,
                'type': 'binary',
                'public': True,
                'datas': base64.encodebytes(f),
            }
            attachment_id = self.env['ir.attachment'].sudo().create(values)
            download_url = '/web/content/' + str(attachment_id.id) + '?download=True'
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            return {
                "type": "ir.actions.act_url",
                "url": str(base_url) + str(download_url),
                "target": "new",
            }


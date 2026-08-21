import json
from operator import itemgetter
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.http import request
import xlsxwriter
import base64


class ReimbursementSummaryReport(models.Model):
    _name = "reimbursement.summary.report"
    _description = 'Reimbursement Summery Report'
    _order = 'create_date desc'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    def _default_report_line_ids(self):
        """get cash out ids from active ids only in confirm state"""
        drawer_summery_lines = self.env['petty.cash.line'].browse(self._context.get('active_ids', []))
        if len(drawer_summery_lines.mapped('petty_cash_id')) > 1:
            drawer_no = ', '.join(drawer_summery_lines.mapped('petty_cash_id.name'))
            raise ValidationError("Summery Can be generated only for one drawer - ( %s ) " % drawer_no)
        out_ids = []
        for rec in drawer_summery_lines:
            if not rec.summary_report_id and not rec.petty_cash_in and rec.is_completed and rec.company_id.id == self.env.company.id:
                out_ids.append(rec.id)
        return [(6, 0, out_ids)]

    @api.depends('report_line_ids')
    def compute_total_amount(self):
        """Compute total in report from lines"""
        for report in self:
            total = 0.00
            for report_line in report.report_line_ids:
                total += report_line.amount
            report.total_amount = total

    name = fields.Char(default=lambda self: _("New"))
    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash Drawer")
    date = fields.Date(default=fields.Date.today(), required=True)
    user_id = fields.Many2one('res.users', string="User", default=lambda self: self.env.user, tracking=True)
    requested_approver = fields.Many2one('res.users', string="Requested Approver")
    is_requested_approver = fields.Boolean(compute="compute_is_requested_approver")
    reject_reason = fields.Char('Reject Reason')
    approved_by = fields.Many2one("res.users", string="Approved/rejected User", copy=False, tracking=True)
    approver_comment = fields.Char('Approve/reject Comment', copy=False)
    approved_date = fields.Datetime(string="Approved/Rejected Date", copy=False, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", required=True, readonly=False,
                                  string='Currency')
    total_amount = fields.Float('Total Amount', compute="compute_total_amount", store=True, tracking=True)
    petty_cash_topup_id = fields.Many2one('petty.cash.in', string="Petty Cash Top UP")
    report_line_ids = fields.One2many('petty.cash.line', 'summary_report_id', string="Report lines", default=_default_report_line_ids, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('awaiting_approval', 'Awaiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='draft', string="Status", tracking=True)

    @api.onchange('report_line_ids')
    def get_petty_cash_drawer_no(self):
        """Set default petty cash drawer from first selected drawer line """
        self.petty_cash_id = self.report_line_ids[0].petty_cash_id.id if self.report_line_ids else False

    def button_request_approval_summery_report(self):
        """open approvel request wizard with mail details"""
        if not self.report_line_ids:
            raise ValidationError("Please add Report lines")
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': 'Approval for Summary report',
            'msg_type': 'There is a Reimbursement summary report for  your approval.',
        }
        return {
            'name': _('Request approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'petty.cash.approver.user.wizard',
            'target': 'new',
            'context': {
                        'default_model_id': model.id,
                        'mail_body': mail_body,
                        }
        }

    def change_state_to_awaiting_approval(self, approvar):
        """Update approvar and change state"""
        if approvar:

            self.requested_approver = approvar.id
            self.state = "awaiting_approval"

    def button_approve_summery_report(self):
        """Open Wizard for approve the report"""
        self.ensure_one()
        if not self.report_line_ids:
            raise ValidationError("Please add Report lines")
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': '%s  Summary report has been Approved' % self.name,
            'msg_type': 'The  Summary report has been  approved.You can proceed. ',
            'status': 'approved',
        }

        return {
            'name': _('Approve'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'petty.cash.approved.comment.wizard',
            'target': 'new',
            'context': {
                        'default_model_id': model.id,
                        'mail_body': mail_body,
                        }
        }

    def change_state_to_approve(self):
        """Change state to Approve"""
        self.state = "approved"
        self.approved_date = datetime.now()

    def button_reject_summery_report(self):
        """Open Wizard for Reject the report"""
        self.ensure_one()
        model = self.env['ir.model'].sudo().search([('model', '=', request.params.get('model'))])
        mail_body = {
            'subject': '%s - Summary report has been Rejected' % self.name,
            'msg_type': 'The Summary report has been Rejected. ',
        }

        return {
            'name': _('Rejected'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'petty.cash.draft.reason',
            'target': 'new',
            'context': {
                        'default_model_id': model.id,
                        'mail_body': mail_body,
                        }
        }

    def button_petty_cash_request_reject(self, reason):
        """Change state to Cancel"""
        self.ensure_one()
        self.state = "rejected"
        self.approver_comment = reason
        self.approved_date = datetime.now()
        self.approved_by = self.env.user

    def set_to_draft(self):
        """Change state to Draft"""
        self.ensure_one()
        self.state = "draft"

    def compute_is_requested_approver(self):
        """Check Current user is a requested approvar"""
        for record in self:
            if record.requested_approver and record.requested_approver.id == self.env.user.id:
                record.is_requested_approver =True
            else:
                record.is_requested_approver = False

    def button_create_topup(self):
        """Create a topup for this report"""
        context = self.env.context.copy()
        context.update({
            'default_summery_report_id': [(4, self.id)],
            'default_petty_cash_id': self.petty_cash_id.id if self.petty_cash_id else False,
            'default_amount': self.total_amount,
            'is_amount_readonly': True,
        })
        view_id = self.env.ref('petty_cash.view_petty_cash_in_form').id
        return {'type': 'ir.actions.act_window',
                'name': _('Top Up'),
                'res_model': 'petty.cash.in',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'context': context,
                }

    def unlink(self):
        """Restrict delete option if there is a cash topup"""
        if self.petty_cash_topup_id:
            raise ValidationError("Cannot delete this report because there is a linked cash top-up")
        return super(ReimbursementSummaryReport, self).unlink()

    #############################################
    #   Account Wise Excel report
    #############################################

    def get_values_for_report(self):
        """Generate values from IOU lines and reimbursement lines"""
        expenses_vals = []
        account_vals = []

        def search_journal_value(acc_id):
            #   search value in account value list
            index = False
            for value in account_vals:
                if value.get('id') == acc_id:
                    index = account_vals.index(value)
                    break
            return index

        def search_duplicate_expenses_vals(name, amount, record_id):
            """Check this available in the list"""
            return next((True for vals in expenses_vals if vals["number"] == name and vals["amount"] == amount and vals["id"] == record_id), False)

        def create_expenses_vals(record_date, number, line, special=False, record_id=None, vendor_bil=False):
            """Create expenses record

            """
            if vendor_bil:
                if not search_duplicate_expenses_vals(number, line.paid_amount, record_id):
                    return {
                        'id': record_id,
                        'date': datetime.combine(record_date.today(), datetime.min.time()),
                        'number': number,
                        'description': "Vendor Bill - " + line.vendor_bill_id.name,
                        'acc_id': False,
                        'amount': line.paid_amount,
                        'column': False
                    }
                else:
                    return {}
            else:
                return {
                    'id': record_id,
                    'date': record_date,
                    'number': number,
                    'description': line.name if not special else line.reason,
                    'acc_id': line.to_acc.id if special else line.expense_account_id.id,
                    'amount': line.amount,
                    'column': account_vals[-1].get('column') + 1 if account_vals else 4
                }

        def create_account_vals(line, special=False):
            """Create account record"""
            return {
                'column': account_vals[-1].get('column') + 1 if account_vals else 4,
                'id': line.to_acc.id if special else line.expense_account_id.id,
                'title': line.to_acc.name if special else line.expense_account_id.name,
                'total': line.amount
            }

        for lines in self.report_line_ids:
            if '000009' in lines.name:
                #vendor_bills Petty cash reimbursement30th January 2023
                aaaa = lines
            if lines.cash_release_id:
                # if report line is Iou request
                for iou_lines in lines.cash_release_id.expenses_line:
                    date = lines.cash_release_id.release_date
                    iou_vals = create_expenses_vals(date, lines.cash_release_id.name, iou_lines)
                    if iou_vals:
                        account_index = search_journal_value(iou_lines.expense_account_id.id)
                        if str(account_index) == 'False':
                            account_vals.append(create_account_vals(iou_lines))
                            iou_vals['column'] = account_vals[-1].get('column')
                        else:
                            account_vals[account_index]['total'] += iou_lines.amount
                            iou_vals['column'] = account_vals[account_index].get('column')
                        expenses_vals.append(iou_vals)

                # if available vendor bills
                for iou_lines in lines.cash_release_id.vendor_bills:
                    date = iou_lines.paid_date
                    iou_vals = create_expenses_vals(date, lines.cash_release_id.name, iou_lines, vendor_bil=True, record_id=iou_lines.id)
                    # if iou_vals:
                    #     account_index = search_journal_value(iou_lines.expense_account_id.id)
                    #     if str(account_index) == 'False':
                    #         account_vals.append(create_account_vals(iou_lines))
                    #         iou_vals['column'] = account_vals[-1].get('column')
                    #     else:
                    #         account_vals[account_index]['total'] += iou_lines.amount
                    #         iou_vals['column'] = account_vals[account_index].get('column')
                    if iou_vals:
                        expenses_vals.append(iou_vals)
            elif lines.cash_reimbursement_id:
                # if report line is Reimbursement
                for iou_lines in lines.cash_reimbursement_id.expenses_line:
                    date = lines.cash_reimbursement_id.cash_date
                    iou_vals = create_expenses_vals(date, lines.cash_reimbursement_id.name, iou_lines)
                    if iou_vals:
                        account_index = search_journal_value(iou_lines.expense_account_id.id)
                        if str(account_index) == 'False':
                            account_vals.append(create_account_vals(iou_lines))
                            iou_vals['column'] = account_vals[-1].get('column')
                        else:
                            account_vals[account_index]['total'] += iou_lines.amount
                            iou_vals['column'] = account_vals[account_index].get('column')
                        expenses_vals.append(iou_vals)
            else:
                date = lines.create_date
                iou_vals = create_expenses_vals(date, lines.name, lines, special=True)
                if iou_vals:
                    account_index = search_journal_value(lines.to_acc.id)
                    if str(account_index) == 'False':
                        account_vals.append(create_account_vals(lines, special=True))
                        iou_vals['column'] = account_vals[-1].get('column')
                    else:
                        account_vals[account_index]['total'] += lines.amount
                        iou_vals['column'] = account_vals[account_index].get('column')
                    expenses_vals.append(iou_vals)

        return expenses_vals, account_vals

    def data_for_account_wise_excel_report(self):
        """Generate data for report from start date to end date"""

        report = 'Account Wise Expenses'
        workbook = xlsxwriter.Workbook(report)
        worksheet = workbook.add_worksheet('Sheet 01')
        worksheet.set_landscape()

        #   styles
        main_header = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 15, 'border': 1})
        second_header_title = workbook.add_format({'align': 'right', 'bold': True,  'font_size': 12, 'border': 1})
        second_header_date = workbook.add_format({'align': 'center', 'bold': True, 'font_size': 12, 'num_format': 'd mmmm', 'border': 1})
        second_header_currency = workbook.add_format({'align': 'center', 'font_size': 12, 'num_format': '"%s" #,##0.00' % self.currency_id.symbol, 'border': 1})
        second_header = workbook.add_format({'align': 'center', 'font_size': 12, 'border': 1})
        second_header_left = workbook.add_format({'align': 'right', 'font_size': 12, 'border': 1})
        second_header_right = workbook.add_format({'align': 'left', 'font_size': 12, 'border': 1})
        third_header = workbook.add_format({'align': 'center', 'bold': True, 'font_size': 12, 'border': 1})
        table_title = workbook.add_format({'align': 'center', 'bold': True,  'border': 1,'bg_color': '#d4d4d4'})
        table_date = workbook.add_format({'align': 'center', 'border': 1,'num_format': 'd mmmm yyyy'})
        table_left = workbook.add_format({'align': 'center', 'border': 1})
        table_currency = workbook.add_format({'align': 'center', 'border': 1, 'num_format': '"%s" #,##0.00' % self.currency_id.symbol})
        table_right = workbook.add_format({'align': 'center', 'border': 1, 'num_format': '"%s" #,##0.00' % self.currency_id.symbol})
        table_footer = workbook.add_format({'align': 'center', 'border': 1, 'bg_color': '#d4d4d4', 'num_format': '"%s" #,##0.00' % self.currency_id.symbol})

        worksheet.set_column("A:A", 10)
        worksheet.set_column("B:B", 15)
        worksheet.set_column("C:C", 25)
        worksheet.set_column("D:D", 20)

        # worksheet.set_row(3, 20)
        expenses_vals, account_vals = self.get_values_for_report()
        expenses_vals.sort(key=itemgetter('date'), reverse=False)

        worksheet.merge_range(0, 0, 0, len(account_vals) + 3, self.company_id.name, main_header)

        worksheet.merge_range(1, 0, 1, len(account_vals) + 3, "Petty Cash Summary - %s" % self.name, second_header)

        # worksheet.merge_range(2, 0, 2, 3, "Imprest Cash Amount", second_header_title)
        worksheet.merge_range(2, 0, 2, 3, 'Petty Cash Float - {:,.2f}'.format(self.petty_cash_id.petty_cash_float), second_header_left)
        worksheet.merge_range(2, 4, 2, len(account_vals) + 3, ' Current Petty Cash Balance: {:,.2f}'.format(self.petty_cash_id.cash_balance), second_header_right)

        worksheet.merge_range(3, 0, 3, len(account_vals) + 3, "Credit", third_header)

        #   table header
        worksheet.write("A5", "Date", table_title)
        worksheet.write("B5", "Description", table_title)
        worksheet.write("C5", "VN", table_title)
        worksheet.write("D5", "Payments", table_title)
        for account in account_vals:
            worksheet.write_string(4, account.get('column'), account.get('title'), table_title)
        row = 5
        for expense in expenses_vals:

            worksheet.write(row, 0, expense.get('date').strftime("%d-%m-%Y"), table_date)
            worksheet.write_string(row, 1, expense.get('description'), table_left)
            worksheet.write_string(row, 2, expense.get('number') or '', table_left)
            worksheet.write(row, 3, expense.get('amount'), table_currency)
            if expense.get('column', False):
                worksheet.write(row, expense.get('column'), expense.get('amount'), table_right)

            worksheet.conditional_format(row, 4, row, len(account_vals) + 3, {
                'type': 'cell',
                'criteria': '=',
                'value': 0,
                'format': table_right
            })

            row += 1

        worksheet.merge_range(row,0, row, 2, 'Petty Cash Expenses', table_title)
        worksheet.write_formula(row,3, "=SUM(D6:D%d)" % row, table_footer)
        for account in account_vals:
            worksheet.write(row, account.get('column'), account.get('total'), table_footer)

        workbook.close()
        return report

    def download_account_wise_report(self):
        """Get the report type from wizard button and downloads the report"""

        self.ensure_one()
        if not self.petty_cash_id:
            raise ValidationError("Select a Petty cash Drawer for this report")
        report = self.data_for_account_wise_excel_report()
        my_report_data = open(report, 'rb+')
        f = my_report_data.read()
        values = {
            'name': 'Account Wise Expenses',
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

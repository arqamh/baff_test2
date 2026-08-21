# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.http import request
from datetime import timedelta


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    pdc_id = fields.Many2one('pdc.wizard')


class PDC_wizard(models.Model):
    _name = "pdc.wizard"
    _description = "PDC Wizard"
    
    def open_attachments(self):
        """button action for open related attachments"""
        [action] = self.env.ref('base.action_attachment').read()
        ids = self.env['ir.attachment'].search([('pdc_id','=',self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        action['domain'] = [('id', 'in', id_list)]
        return action
    
    def open_journal_items(self):
        """button action for open related journals"""
        [action] = self.env.ref('account.action_account_moves_all').read()
        ids = self.env['account.move.line'].search([('pdc_id','=',self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        action['domain'] = [('id', 'in', id_list)]
        return action
    
    def open_journal_entry(self):
        """button action for open related journal entries"""
        [action] = self.env.ref('sh_pdc.sh_pdc_action_move_journal_line').read()
        ids = self.env['account.move'].search([('pdc_id','=',self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        action['domain'] = [('id', 'in', id_list)]
        return action

    @api.model
    def default_get(self, fields):
        """Override default_get method and update default values"""
        rec = super(PDC_wizard, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec
        invoices = self.env['account.move'].browse(active_ids)
        if invoices:
            invoice = invoices[0]
            if invoice.move_type in ('out_invoice','out_refund'):
                rec.update({'payment_type':'receive_money'})
            elif invoice.move_type in ('in_invoice','in_refund'):
                rec.update({'payment_type':'send_money'})

            rec.update({'partner_id':invoice.partner_id.id,
                        'payment_amount':invoice.amount_residual,
                        'invoice_id':invoice.id,
                        'due_date':invoice.invoice_date_due,
                        'memo':invoice.name})

        return rec

    name = fields.Char("Name",default='New',readonly=1)
    check_amount_in_words = fields.Char(string="Amount in Words",compute='_compute_check_amount_in_words')
    payment_type = fields.Selection([('receive_money','Receive Money'),('send_money','Send Money')],string="Payment Type",default='receive_money')
    partner_id = fields.Many2one('res.partner',string="Partner", required=True)
    payment_amount = fields.Monetary("Payment Amount")
    currency_id = fields.Many2one('res.currency',string="Currency",default=lambda self:self.env.company.currency_id)
    reference = fields.Char("Cheque No")
    journal_id = fields.Many2one('account.journal',string="Payment Journal",domain=[('type','=','bank')],required=1)
    cheque_status = fields.Selection([('draft','Draft'),('deposit','Deposit'),('paid','Paid')],string="Cheque Status",default='draft')
    payment_date = fields.Date("Payment Date",default=fields.Date.today(),required=1)
    cheque_date = fields.Date("Cheque Date",default=fields.Date.today(),required=1)
    due_date = fields.Date("Due Date",required=1)
    memo = fields.Char("Memo")
    agent = fields.Char("Agent")
    company_id = fields.Many2one('res.company',string='company',default=lambda self: self.env.company)
    bank_id = fields.Many2one('res.bank',string="Branch")
    attachment_ids = fields.Many2many('ir.attachment', string='Cheque Image')
    invoice_id = fields.Many2one('account.move',string="Invoice/Bill")
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting_approval', 'Waiting For Approval'),
                              ('approved', 'Approved'),
                              ('registered', 'Registered'),
                              ('returned', 'Returned'),
                              ('deposited', 'Deposited'),
                              ('bounced', 'Bounced'),
                              ('done', 'Done'),
                              ('cancel', 'Cancelled')],string="State",default='draft')
    deposited_debit = fields.Many2one('account.move.line')
    deposited_credit = fields.Many2one('account.move.line')
    custom_url = fields.Char("URL")
    approved_by = fields.Many2one('res.users', string="Approved/Rejected By", readonly=1, tracking=True)
    approve_Date = fields.Date(string="Approved/Rejected Date", readonly=1, tracking=True)
    comment = fields.Text(string="Approved/Rejected Comment", readonly=1, tracking=True)
    triggered_approval = fields.Boolean(string="Triggered Approval", default=False)
    receipt_id = fields.Many2one('account.receipt.payment')
    main_bank_id = fields.Many2one('main.bank', string="Bank")
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Account No")
#     attachment_ids = fields.One2many('ir.attachment','pdc_id',string="Attachments")

    is_cheque_ac_payee = fields.Boolean(string="A/c Payee", default=False)
    invoice_ids = fields.Many2many('account.move')
    done_date = fields.Date(string="Done Date", readonly=True, tracking=True)
    account_move_ids = fields.Many2many('account.move', compute="compute_account_moves")


    def _compute_check_amount_in_words(self):
        """Compute and update amount in text"""
        if self:
            for rec in self:
                rec.check_amount_in_words = False
                rec.check_amount_in_words = rec.currency_id.amount_to_text(rec.payment_amount)

    # Register pdc payment
    def button_register(self):
        if self:
            if self.cheque_status == 'draft':
                self.write({'state':'draft'})

            if self.cheque_status == 'deposit':
                self.action_register()
                self.action_deposited()
                self.write({'state':'deposited'})

            if self.cheque_status == 'paid':
                self.action_register()
                self.action_deposited()
                # self.action_done()
                self.write({'state':'done'})

            if self.invoice_id:
                self.invoice_id.sudo().write({
#                     'amount_residual_signed': self.invoice_id.amount_residual_signed - self.payment_amount,
                    'amount_residual':self.invoice_id.amount_residual - self.payment_amount,
                    })
                self.invoice_id._compute_amount()
        result = self.action_register()
        if result:
            return result

    def action_register(self):
        """action for register payment"""
        if self.payment_type == 'receive_money':
            first_approval_customer = self.env['ir.config_parameter'].sudo().get_param(
                'sh_pdc.pdc_payment_approval')
            if not self.triggered_approval:
                if first_approval_customer:
                    amount = float(self.env['ir.config_parameter'].sudo().get_param(
                        'sh_pdc.pdc_approval_amount'))
                    payment_currency_id = int(self.env['ir.config_parameter'].sudo().get_param(
                        'sh_pdc.pdc_approval_currency_id'))
                    payment_amount = self.payment_amount
                    if payment_currency_id:
                        if self.currency_id and self.currency_id.id != payment_currency_id:
                            currency_id = self.env['res.currency'].browse(payment_currency_id)
                            payment_amount = self.currency_id._convert(
                                self.payment_amount, currency_id, self.company_id,
                                self.cheque_date or fields.Date.today(), round=True)
                    if payment_amount > amount:
                        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
                        return {
                            'name': _('Send to Approval'),
                            'type': 'ir.actions.act_window',
                            'view_mode': 'form',
                            'res_model': 'pdc.payments.approver.user.wizard',
                            'target': 'new',
                            'context': {'default_pdc_id': self.id,
                                        'default_model_id': model.id}
                        }
            self.check_payment_amount()
            self.write({'state':'registered'})
        if self.payment_type == 'send_money':
            first_approval_vendor = self.env['ir.config_parameter'].sudo().get_param(
                'sh_pdc.pdc_vendor_payment_approval')
            if not self.triggered_approval:
                if first_approval_vendor:
                    amount = float(self.env['ir.config_parameter'].sudo().get_param(
                        'sh_pdc.pdc_vendor_approval_amount'))
                    payment_currency_id = int(self.env['ir.config_parameter'].sudo().get_param(
                        'sh_pdc.pdc_vendor_approval_currency_id'))
                    payment_amount = self.payment_amount
                    if payment_currency_id:
                        if self.currency_id and self.currency_id.id != payment_currency_id:
                            currency_id = self.env['res.currency'].browse(payment_currency_id)
                            payment_amount = self.currency_id._convert(
                                self.payment_amount, currency_id, self.company_id,
                                self.cheque_date or fields.Date.today(), round=True)
                    if payment_amount > amount:
                        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
                        return {
                            'name': _('Send to Approval'),
                            'type': 'ir.actions.act_window',
                            'view_mode': 'form',
                            'res_model': 'pdc.payments.approver.user.wizard',
                            'target': 'new',
                            'context': {'default_pdc_id': self.id,
                                        'default_model_id': model.id}
                        }
            self.check_payment_amount()
            self.write({'state':'registered'})

    def check_payment_amount(self):
        """Validate amount"""
        if self.payment_amount <= 0.0:
            raise UserError("Amount must be greater than zero!")

    def check_pdc_account(self):
        """Validate account type"""
        if self.payment_type == 'receive_money':
            if not self.env.company.pdc_customer:
                raise UserError("Please Set PDC payment account for Customer !")
            else:
                # return self.env.company.pdc_customer.id
                return self.env.company.pdc_customer.id

        else:
            if not self.env.company.pdc_vendor:
                raise UserError("Please Set PDC payment account for Supplier !")
            else:
                return self.env.company.pdc_vendor.id

    def get_partner_account(self):
        """method for get default account from partner"""
        if self.payment_type == 'receive_money':
            return self.partner_id.property_account_receivable_id.id
        else:
            return self.partner_id.property_account_payable_id.id

    def action_returned(self):
        """button action for pdc return"""
        self.check_payment_amount()
        self.write({'state': 'returned'})

    def get_credit_move_line(self, account):
        """create journal entry line values for credit"""
        return {
            'pdc_id': self.id,
            'account_id': account,
            'credit': self.payment_amount,
            'partner_id': self.partner_id.id,
            'ref': self.memo,
            'date': self.cheque_date,
            'date_maturity': self.due_date,
        }

    def get_debit_move_line(self, account):
        """create journal entry line values for debit"""
        return {
            'pdc_id': self.id,
            'account_id': account,
            'debit': self.payment_amount,
            'partner_id': self.partner_id.id,
            'ref': self.memo,
            'date': self.cheque_date,
            'date_maturity': self.due_date,
        }

    def get_move_vals(self, debit_line, credit_line):
        """create journal entry values"""
        return {
            'pdc_id': self.id,
            'date': self.cheque_date,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
            'ref': self.memo,
            'line_ids': [(0, 0, debit_line),
                         (0, 0, credit_line)]
        }

    def validate_cheque_date(self):
        """Open pdc confirmation wizard with message"""
        if self.cheque_date < fields.Date.today():
            date_type = "Previous Date "
        else:
            date_type = "Future Date "
        message = " Cheque Date is a %s. \n " \
                  "Do you want to deposit cheque with this cheque date :- %s ." % (
                  date_type, self.cheque_date.strftime("%d-%m-%Y"))
        return {
            'name': _('Confirmation'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'pdc.confirmation.wizard',
            'target': 'new',
            'context': {
                'default_pdc_payment_id': self.id,
                'default_message': message,
            }
        }

    def action_deposited(self):
        """Method for deposit the cheque
            create journal entries and reconcile
        """
        if not self.env.context.get('confirm_cheque_date') and self.cheque_date != fields.Date.today():
            # 'confirm_cheque_date' context value get form confirm_wizard in pdc
            # Validate cheque date
            return self.validate_cheque_date()

        if self.env.context.get('confirm_wizard_deposit'):
            # 'confirm_wizard_deposit' context value get form pdc_payment wizard in invoice or bill
            # if register pdc before deposit
            result = self.button_register()
            if result:
                return result

        move = self.env['account.move']

        self.check_payment_amount() # amount must be positive
        pdc_account = self.check_pdc_account()
        partner_account = self.get_partner_account()

        # Create Journal Item
        move_line_vals_debit = {}
        move_line_vals_credit = {}
        if self.payment_type=='receive_money':
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(partner_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(partner_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)
        
        #create move and post it
        move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        move_id = move.create(move_vals)
        move_id.action_post()
        self.write({'state': 'deposited', 'deposited_debit':move_id.line_ids.filtered(lambda x:x.debit > 0),
                    'deposited_credit':move_id.line_ids.filtered(lambda x:x.credit > 0)})
        self._reconcile_payments()

    def _reconcile_payments(self):
        """ Reconcile the payments.

        :param to_process:  A list of python dictionary, one for each payment to create, containing:
                            * create_vals:  The values used for the 'create' method.
                            * to_reconcile: The journal items to perform the reconciliation.
                            * batch:        A python dict containing everything you want about the source journal items
                                            to which a payment will be created (see '_get_batches').
        :param edit_mode:   Is the wizard in edition mode.
        """

        payment_lines = self.env['account.move.line'].search([('pdc_id','=',self.id),('account_internal_type', 'in', ('receivable', 'payable'))])

        lines = self.invoice_id.line_ids
        # for line in lines + payment_lines:
        #     line.reconcile()
        for account in payment_lines.account_id:
                (payment_lines + lines).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]).reconcile()


        # for account in payment_lines.account_id:
        #         (payment_lines + lines).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]).reconcile()
        #
        #
    def action_bounced(self):
        move = self.env['account.move']
        
        self.check_payment_amount() # amount must be positive
        pdc_account = self.check_pdc_account()
        partner_account = self.get_partner_account()
        
        # Create Journal Item
        move_line_vals_debit = {}
        move_line_vals_credit = {}
        
        if self.payment_type=='receive_money':
            move_line_vals_debit = self.get_debit_move_line(partner_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(partner_account)
            
        if self.memo:
            move_line_vals_debit.update({'name':'PDC Payment :'+self.memo})
            move_line_vals_credit.update({'name':'PDC Payment :'+self.memo})
        else:
            move_line_vals_debit.update({'name':'PDC Payment'})
            move_line_vals_credit.update({'name':'PDC Payment'})
        #create move and post it
        move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        move_id = move.create(move_vals)
        move_id.action_post()
        
        self.write({'state':'bounced'})

    ############
    # This on is commented because of reconcilation process
    ############
    ############
    # This is uncomment action_done is not a valid action on pdc.wizard
    ############

    def action_done(self):
        move = self.env['account.move']

        self.check_payment_amount() # amount must be positive
        pdc_account = self.check_pdc_account()
        if self.payment_type == 'receive_money':
            #   if payment_type inbound
            lines = self.journal_id.inbound_payment_method_line_ids.filtered(lambda self: self.code == "cheque")
        else:
            lines = self.journal_id.outbound_payment_method_line_ids.filtered(lambda self: self.code == "cheque")
        bank_account = lines.payment_account_id.id if lines and lines.payment_account_id else self.journal_id.default_account_id.id

        # Create Journal Item
        move_line_vals_debit = {}
        move_line_vals_credit = {}
        if self.payment_type=='receive_money':
            move_line_vals_debit = self.get_debit_move_line(bank_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(bank_account)

        if self.memo:
            move_line_vals_debit.update({'name':'PDC Payment :'+self.memo, 'partner_id':self.partner_id.id})
            move_line_vals_credit.update({'name':'PDC Payment :'+self.memo, 'partner_id':self.partner_id.id})
        else:
            move_line_vals_debit.update({'name':'PDC Payment','partner_id':self.partner_id.id})
            move_line_vals_credit.update({'name':'PDC Payment','partner_id':self.partner_id.id})

        #create move and post it
        move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        move_id = move.create(move_vals)
        move_id.action_post()


        invoice = self.env['account.move'].sudo().search([('id','=',self.invoice_id.id)])
        if invoice:
            if self.payment_type=='receive_money':
                # reconcilation Entry for Invoice
                debit_move_id = self.env['account.move.line'].sudo().search([('move_id','=',invoice.id),
                                                                                 ('debit','>',0.0)],limit=1)

                credit_move_id = self.env['account.move.line'].sudo().search([('move_id','=',move_id.id),
                                                             ('credit','>',0.0)],limit=1)

                if debit_move_id and credit_move_id:
                    amount = 0.0
                    if  move_line_vals_debit['debit'] > 0.0:
                        amount = move_line_vals_debit['debit']
                    else:
                        amount =  move_line_vals_debit['credit']
                    full_reconcile_id = self.env['account.full.reconcile'].create({})
                    reconcile_id = self.env['account.partial.reconcile'].sudo().create({'debit_move_id': debit_move_id.id,
                                                                         'credit_move_id':self.deposited_credit.id,
                                                                         'debit_amount_currency':amount,
                                                                         'full_reconcile_id':full_reconcile_id.id
                                                                       })

                    reconcile_id = self.env['account.partial.reconcile'].sudo().create({'debit_move_id': self.deposited_debit.id,
                                                                         'credit_move_id':credit_move_id.id,
                                                                         'credit_amount_currency':amount,
                                                                         'full_reconcile_id':full_reconcile_id.id
                                                                       })

                    debit_move_id.write({'full_reconcile_id':full_reconcile_id.id})
                    credit_move_id.write({'full_reconcile_id':full_reconcile_id.id})
                    self.deposited_debit.write({'full_reconcile_id':full_reconcile_id.id})
                    self.deposited_credit.write({'full_reconcile_id':full_reconcile_id.id})
            else:
                credit_move_id = self.env['account.move.line'].sudo().search([('move_id','=',invoice.id),
                                                                                 ('credit','>',0.0)],limit=1)

                debit_move_id = self.env['account.move.line'].sudo().search([('move_id','=',move_id.id),
                                                             ('debit','>',0.0)],limit=1)

                if debit_move_id and credit_move_id:
                    amount = 0.0
                    if  move_line_vals_debit['debit'] > 0.0:
                        amount = move_line_vals_debit['debit']
                    else:
                        amount =  move_line_vals_debit['credit']

                    full_reconcile_id = self.env['account.full.reconcile'].create({})
                    reconcile_id = self.env['account.partial.reconcile'].sudo().create({'debit_move_id': self.deposited_debit.id,
                                                                         'credit_move_id':credit_move_id.id,
                                                                         'debit_amount_currency':amount,
                                                                         'credit_amount_currency':amount,
                                                                         'full_reconcile_id':full_reconcile_id.id
                                                                       })
                    reconcile_id = self.env['account.partial.reconcile'].sudo().create({'debit_move_id': debit_move_id.id,
                                                                         'credit_move_id':self.deposited_credit.id,
                                                                         'debit_amount_currency':amount,
                                                                         'credit_amount_currency':amount,
                                                                         'full_reconcile_id':full_reconcile_id.id
                                                                       })
                    debit_move_id.write({'full_reconcile_id':full_reconcile_id.id})
                    credit_move_id.write({'full_reconcile_id':full_reconcile_id.id})
                    self.deposited_debit.write({'full_reconcile_id':full_reconcile_id.id})
                    self.deposited_credit.write({'full_reconcile_id':full_reconcile_id.id})

        self.write({'state': 'done'})

    # Multi Action Starts for change the state of PDC check
    def action_set_draft(self):
        self.sudo().write({
            'state': 'draft',
        })
        
    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft',
                    'triggered_approval': False})

    def approve_transfer(self):
        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
        return {
            'name': _('Comment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'pdc.payment.approve.comment.wizard',
            'target': 'new',
            'context': {'default_pdc_id': self.id,
                        'default_model_id': model.id,
                        'default_action': self._context.get('action') or False,
                        }
        }

    def reject_transfer(self):
        model = self.env['ir.model'].search([('model', '=', request.params.get('model'))])
        return {
            'name': _('Comment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'pdc.payment.approve.comment.wizard',
            'target': 'new',
            'context': {'default_pdc_id': self.id,
                        'default_model_id': model.id,
                        'default_action': self._context.get('action') or False,
                        }
        }
    
    @api.model
    def create(self, vals):
        """Override create method"""
        if vals.get('payment_type')=='receive_money':
            vals['name'] = self.env['ir.sequence'].next_by_code('pdc.payment.customer')
        elif vals.get('payment_type')=='send_money':
            vals['name'] = self.env['ir.sequence'].next_by_code('pdc.payment.vendor')
                
        return super(PDC_wizard, self).create(vals)

    #==============================
    #    CRON SCHEDULER CUSTOMER
    #==============================
    @api.model
    def notify_customer_due_date(self):
        emails = []
        if self.env.company.is_cust_due_notify:
            notify_day_1 = self.env.company.notify_on_1
            notify_day_2 = self.env.company.notify_on_2
            notify_day_3 = self.env.company.notify_on_3
            notify_day_4 = self.env.company.notify_on_4
            notify_day_5 = self.env.company.notify_on_5
            notify_date_1 = False
            notify_date_2 = False
            notify_date_3 = False
            notify_date_4 = False
            notify_date_5 = False
            if notify_day_1:
                notify_date_1 = fields.date.today() + timedelta(days=int(notify_day_1)*-1)
            if notify_day_2:
                notify_date_2 = fields.date.today() + timedelta(days=int(notify_day_2)*-1)
            if notify_day_3:
                notify_date_3 = fields.date.today() + timedelta(days=int(notify_day_3)*-1)
            if notify_day_4:
                notify_date_4 = fields.date.today() + timedelta(days=int(notify_day_4)*-1)
            if notify_day_5:
                notify_date_5 = fields.date.today() + timedelta(days=int(notify_day_5)*-1)
            
            records = self.search([('payment_type','=','receive_money')])
            for user in self.env.company.sh_user_ids:
                    if user.partner_id and user.partner_id.email:
                        emails.append(user.partner_id.email)
            email_values = {
                'email_to': ','.join(emails),
            }
            view = self.env.ref("sh_pdc.sh_pdc_payment_form_view",raise_if_not_found = False).sudo()
            view_id = view.id if view else 0
            for record in records:
                if (record.due_date == notify_date_1
                    or record.due_date == notify_date_2
                    or record.due_date == notify_date_3
                    or record.due_date == notify_date_4
                    or record.due_date == notify_date_5):
                    
                    if self.env.company.is_notify_to_customer:
                        template_download_id = record.env['ir.model.data'].get_object(
                            'sh_pdc', 'sh_pdc_company_to_customer_notification_1'
                            )
                        _ = record.env['mail.template'].browse(
                            template_download_id.id
                            ).send_mail(record.id,notif_layout='mail.mail_notification_light',force_send=True)
                    if self.env.company.is_notify_to_user and self.env.company.sh_user_ids:
                        url = ''
                        base_url = request.env['ir.config_parameter'].sudo(
                        ).get_param('web.base.url')
                        url = base_url + "/web#id=" + \
                                str(record.id) + \
                                "&&model=pdc.wizard&view_type=form&view_id=" + str(view_id)
                        ctx = {
                            "customer_url": url,
                        }
                        template_download_id = record.env['ir.model.data'].get_object(
                            'sh_pdc', 'sh_pdc_company_to_int_user_notification_1'
                            )
                        _ = request.env['mail.template'].sudo().browse(template_download_id.id).with_context(ctx).send_mail(
                            record.id, email_values=email_values, notif_layout='mail.mail_notification_light', force_send=True)
                        
    
    
    
    #==============================
    #    CRON SCHEDULER VENDOR
    #==============================
    @api.model
    def notify_vendor_due_date(self):
        emails = []
        if self.env.company.is_vendor_due_notify:
            notify_day_1_ven = self.env.company.notify_on_1_vendor
            notify_day_2_ven = self.env.company.notify_on_2_vendor
            notify_day_3_ven = self.env.company.notify_on_3_vendor
            notify_day_4_ven = self.env.company.notify_on_4_vendor
            notify_day_5_ven = self.env.company.notify_on_5_vendor
            notify_date_1_ven = False
            notify_date_2_ven = False
            notify_date_3_ven = False
            notify_date_4_ven = False
            notify_date_5_ven = False
            if notify_day_1_ven:
                notify_date_1_ven = fields.date.today() + timedelta(days=int(notify_day_1_ven)*-1)
            if notify_day_2_ven:
                notify_date_2_ven = fields.date.today() + timedelta(days=int(notify_day_2_ven)*-1)
            if notify_day_3_ven:
                notify_date_3_ven = fields.date.today() + timedelta(days=int(notify_day_3_ven)*-1)
            if notify_day_4_ven:
                notify_date_4_ven = fields.date.today() + timedelta(days=int(notify_day_4_ven)*-1)
            if notify_day_5_ven:
                notify_date_5_ven = fields.date.today() + timedelta(days=int(notify_day_5_ven)*-1)
            
            records = self.search([('payment_type','=','send_money')])
            for user in self.env.company.sh_user_ids_vendor:
                    if user.partner_id and user.partner_id.email:
                        emails.append(user.partner_id.email)
            email_values = {
                'email_to': ','.join(emails),
            }
            view = self.env.ref("sh_pdc.sh_pdc_payment_form_view",raise_if_not_found = False)
            view_id = view.id if view else 0
            for record in records:
                if (record.due_date == notify_date_1_ven
                    or record.due_date == notify_date_2_ven
                    or record.due_date == notify_date_3_ven
                    or record.due_date == notify_date_4_ven
                    or record.due_date == notify_date_5_ven):
                    
                    if self.env.company.is_notify_to_vendor:
                        template_download_id = record.env['ir.model.data'].get_object(
                            'sh_pdc', 'sh_pdc_company_to_customer_notification_1'
                            )
                        _ = record.env['mail.template'].browse(
                            template_download_id.id
                            ).send_mail(record.id,notif_layout='mail.mail_notification_light',force_send=True)
                    if self.env.company.is_notify_to_user_vendor and self.env.company.sh_user_ids_vendor:
                        url = ''
                        base_url = request.env['ir.config_parameter'].sudo(
                        ).get_param('web.base.url')
                        url = base_url + "/web#id=" + \
                                str(record.id) + \
                                "&&model=pdc.wizard&view_type=form&view_id=" + str(view_id)
                        ctx = {
                            "customer_url": url,
                        }
                        template_download_id = record.env['ir.model.data'].get_object(
                            'sh_pdc', 'sh_pdc_company_to_int_user_notification_1'
                            )
                        _ = request.env['mail.template'].sudo().browse(template_download_id.id).with_context(ctx).send_mail(
                            record.id, email_values=email_values, notif_layout='mail.mail_notification_light', force_send=True)


    # Multi Action Starts for change the state of PDC check

    def action_state_register(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')
        
        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')
            
            if len(set(states)) == 1:
                if states[0] == 'draft':
                    for active_model in active_models:
                        active_model.action_register()
                else:
                    raise UserError(
                        "Only Draft state PDC check can switch to Register state!!")
            else:
                raise UserError(
                        "States must be same!!")

    def action_state_return(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')

            if len(set(states)) == 1:
                if states[0] == 'registered':
                    for active_model in active_models:
                        active_model.action_returned()
                else:
                    raise UserError(
                        "Only Register state PDC check can switch to return state!!")
            else:
                raise UserError(
                        "States must be same!!")

    def action_state_deposit(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')

            if len(set(states)) == 1:
                if states[0] in ['registered','returned','bounced']:
                    for active_model in active_models:
                        active_model.action_deposited()
                else:
                    raise UserError(
                        "Only Register,Return and Bounce state PDC check can switch to Deposit state!!")
            else:
                raise UserError(
                        "States must be same!!")
        
    def action_state_bounce(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')

            if len(set(states)) == 1:
                if states[0] == 'deposited':
                    for active_model in active_models:
                        active_model.action_bounced()
                else:
                    raise UserError(
                        "Only Deposit state PDC check can switch to Bounce state!!")
            else:
                raise UserError(
                        "States must be same!!")

    def action_state_done(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')

            if len(set(states)) == 1:
                if states[0] == 'deposited':
                    pass
                    # for active_model in active_models:
                    #     active_model.action_done()
                else:
                    raise UserError(
                        "Only Deposit state PDC check can switch to Done state!!")
            else:
                raise UserError(
                        "States must be same!!")

    def action_state_cancel(self):
        active_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')

        if len(active_ids) > 0:
            active_models = self.env[active_model].browse(active_ids)
            states = active_models.mapped('state')

            if len(set(states)) == 1:
                if states[0] in ['registered','returned','bounced']:
                    for active_model in active_models:
                        active_model.action_cancel()
                else:
                    raise UserError(
                        "Only Register,Return and Bounce state PDC check can switch to Cancel state!!")
            else:
                raise UserError(
                        "States must be same!!")
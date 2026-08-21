import json
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PettyCash(models.Model):
    """
    Petty cash Handling class
    """
    _name = "petty.cash"
    _description = "Petty Cash"
    _order = "end_date desc"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    @api.model
    def default_get(self, default_fields):
        """ Compute default start date and end date
        using the default values computed for the other fields.
        """
        res = super(PettyCash, self).default_get(default_fields)

        petty_cashes = self.env['petty.cash'].search([], order="end_date desc", limit=1)
        date_range = self.env['ir.config_parameter'].sudo().get_param('petty_cash.petty_cash_date_range') or False
        if petty_cashes:
            start_date = petty_cashes.end_date + timedelta(days=1)
            res['start_date'] = start_date
            if not date_range:
                date_range = 30
            else:
                date_range = int(date_range)
            res['end_date'] = start_date + timedelta(days=date_range)
            # res['end_date'] = start_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
        else:
            today = fields.Date.today()
            res['start_date'] = today
            if not date_range:
                date_range = 30
            else:
                date_range = int(date_range)
            res['end_date'] = today + timedelta(days=date_range)
        return res

    name = fields.Char(default=lambda self: _('New'), required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    user_id = fields.Many2one("res.users", string="Responsible Users", default=lambda self: self.env.user, required=True)
    accessible_user_ids = fields.Many2many("res.users", string="Accessible Users", default=lambda self: self.env.user, domain=lambda self: [('groups_id', 'in', self.env.ref('petty_cash.petty_cash_group_user_all').id)], tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", required=True, readonly=False,
                                  string='Currency')
    petty_cash_float = fields.Float("Petty Cash Float", default=0.00, required=True, tracking=True)
    increased_float_amount = fields.Float("Increased Float", default=0.00)
    cash_flow = fields.Float("Cash IN")
    cash_out = fields.Float("Cash Out")
    cash_balance = fields.Float("Cash Balance", compute="_compute_cash_amount")
    cash_out_line_ids = fields.One2many('petty.cash.out', 'petty_cash_id', string="Settlement")
    cash_issue_line_ids = fields.One2many('petty.cash.release', 'petty_cash_id', string="Petty Cash Out")
    cash_in_line_ids = fields.One2many('petty.cash.in', 'petty_cash_id', string="Petty Cash IN")
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]}, domain="[('is_petty_cash','=', True),'|', ('company_id', '=', company_id), ('company_id', '=', False)]")

    is_transferred = fields.Boolean(default=False)
    state = fields.Selection([
                            ('draft', 'Draft'),
                            ('in_progress', 'In Progress'),
                            ('complete', 'completed'),
                            ('balance', 'Balanced')], string="State", default="draft", tracking=True)
    move_id = fields.Many2many('account.move', string="Journal Entries", copy=False)
    petty_cash_line_ids = fields.One2many('petty.cash.line', 'petty_cash_id', string="Transactions")
    sequence_prefix = fields.Char("Prefix for Sequence", help="Prefix value of the record for the sequence", required=True)
    sequence_format = fields.Char("Sequence Format", default="/%(day)s%(month)s%(year)s/", store=True)
    iou_sequence_id = fields.Many2one("ir.sequence")
    rem_sequence_id = fields.Many2one("ir.sequence")
    topup_sequence_id = fields.Many2one("ir.sequence")
    is_available_topup = fields.Boolean(default=True)

    def create_sequence_for_cash_drawer(self, drawer=None):
        """Create a sequence for cash drawer and link to drawer"""

        if not drawer:
            drawer = self
        sequence_format = drawer.sequence_format if drawer.sequence_format else '/%(day)s%(month)s%(year)s/'
        sequence_object = self.env['ir.sequence']
        if not drawer.iou_sequence_id:
            drawer.iou_sequence_id = sequence_object.sudo().create({
                                        'name': drawer.name + " - IOU",
                                        'prefix': drawer.sequence_prefix.upper() + '/IOU' + sequence_format,
                                        'padding': 6,
                                        'company_id': drawer.company_id.id,
                                    })
        if not drawer.rem_sequence_id:
            drawer.rem_sequence_id = sequence_object.sudo().create({
                                        'name': drawer.name + " - REIM",
                                        'prefix': drawer.sequence_prefix.upper() + '/REIM' + sequence_format,
                                        'padding': 6,
                                        'company_id': drawer.company_id.id,
                                    })
        if not drawer.topup_sequence_id:
            drawer.topup_sequence_id = sequence_object.sudo().create({
                                        'name': drawer.name + " - TOP",
                                        'prefix': drawer.sequence_prefix.upper() + '/TOP' + sequence_format,
                                        'padding': 6,
                                        'company_id': drawer.company_id.id,
                                    })

    @api.model_create_multi
    def create(self, values):
        """Override create method and added sequence generate option"""
        drawers = super(PettyCash, self).create(values)
        for drawer in drawers:
            if drawer:
                self.create_sequence_for_cash_drawer(drawer)
        return drawers

    def write(self, vals):
        """Override Write method and added sequence generate option"""
        drawer = super(PettyCash, self).write(vals)
        if vals.get('sequence_prefix'):
            self.create_sequence_for_cash_drawer()
        return drawer

    @api.depends('cash_in_line_ids')
    def _compute_cash_amount(self):
        """Compute cash out and balanced amount"""
        for rec in self:
            rec.cash_balance = rec.cash_flow - rec.cash_out

    #   """"""""""""""""""""""""""""""  #
    #   Removed   #
    #   """"""""""""""""""""""""""""""  #
    # @api.onchange('journal_id')
    # def _onchange_journal_id(self):
    #     """Change start and end date when change the journal id"""
    #     date_range = self.env['ir.config_parameter'].sudo().get_param('petty_cash.petty_cash_date_range') or False
    #     if self.journal_id:
    #         petty_cashes = self.env['petty.cash'].search([('journal_id', '=', self.journal_id.id)], order="end_date desc", limit=1)
    #
    #         if petty_cashes:
    #             start_date = petty_cashes.end_date + timedelta(days=1)
    #             self.start_date = start_date
    #             if not date_range:
    #                 date_range = 30
    #             else:
    #                 date_range = int(date_range)
    #             self.end_date = start_date + timedelta(days=date_range)
    #         else:
    #             start_date = datetime.today().date()
    #             self.start_date = start_date
    #             if not date_range:
    #                 date_range = 30
    #             else:
    #                 date_range = int(date_range)
    #             self.end_date = start_date + timedelta(days=date_range)
    #     else:
    #         start_date = datetime.today().date()
    #         self.start_date = start_date
    #         if not date_range:
    #             date_range = 30
    #         else:
    #             date_range = int(date_range)
    #         self.end_date = start_date + timedelta(days=date_range)

    def button_confirm_petty_cash(self):
        """Confirm Petty cash Flow"""
        self.ensure_one()
        if self.petty_cash_float <= 0.00:
            raise ValidationError("Cash Float must be more than 0.00 ")
        self.state = 'in_progress'

    def button_petty_cash_iou_request(self):
        """Create Cash release for petty cash"""
        self.ensure_one()
        context = self.env.context.copy()
        context.update({'default_petty_cash_id': self.id, 'default_is_wizard': True})
        view_id = self.env.ref('petty_cash.view_petty_cash_release_form').id
        return {'type': 'ir.actions.act_window',
                'name': _('IOU Request'),
                'res_model': 'petty.cash.release',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'context': context,
                }

    def action_button_petty_cash_in(self):
        """Create Cash IN for petty cash"""
        self.ensure_one()
        context = self.env.context.copy()
        context.update({'default_petty_cash_id': self.id, 'create': False})
        action = self.env.ref('petty_cash.action_petty_cash_in_by_petty_cash').read()[0]
        action['domain'] = [('id', 'in', self.cash_in_line_ids.ids)]
        action['view_mode'] = 'tree,form'
        action['context'] = context
        return action

    def action_button_iou_requests(self):
        """Create Cash IOU Requests for petty cash"""
        self.ensure_one()
        context = self.env.context.copy()
        context.update({'default_petty_cash_id': self.id, 'create': False})
        action = self.env.ref('petty_cash.action_iou_request_by_petty_cash').read()[0]
        action['domain'] = [('petty_cash_id', '=', self.id)]
        action['view_mode'] = 'tree,form'
        action['context'] = context
        return action

    def action_button_reimbursement(self):
        """Create Cash Reimbursement for petty cash"""
        self.ensure_one()
        context = self.env.context.copy()
        context.update({'default_petty_cash_id': self.id, 'create': False})
        action = self.env.ref('petty_cash.action_petty_cash_out').read()[0]
        action['domain'] = [('petty_cash_id', '=', self.id)]
        action['view_mode'] = 'tree,form'
        action['context'] = context
        return action

    def button_petty_cash_in(self):
        """Create Cash IN for petty cash"""
        context = self.env.context.copy()
        context.update({
            'default_petty_cash_id': self.id,
            'default_is_wizard': True,
        })

        if not self.cash_in_line_ids:
            # First time cash float amount equal to cash drawer float
            context.update({
                'default_amount': self.petty_cash_float,
                'is_amount_readonly': True,
            })

        elif self.increased_float_amount > 0:

            context.update({
                'default_amount': self.increased_float_amount,
                'is_amount_readonly': True,
            })
        view_id = self.env.ref('petty_cash.view_petty_cash_in_form').id
        return {'type': 'ir.actions.act_window',
                'name': _('Top Up') if self.cash_in_line_ids else _('Cash Float'),
                'res_model': 'petty.cash.in',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'context': context,
                }

    def button_petty_reimbursement(self):
        """create Reimbursement for petty cash"""
        self.ensure_one()
        context = self.env.context.copy()
        context.update({'default_petty_cash_id':self.id, 'default_is_wizard': True})
        view_id = self.env.ref('petty_cash.view_petty_cash_out_form').id
        return {'type': 'ir.actions.act_window',
                'name': _('Reimbursement'),
                'res_model': 'petty.cash.out',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                'context': context,
                }

    def button_view_journal_entries(self):
        """view journal entries related to this"""
        self.ensure_one()
        context = self.env.context.copy()
        context.update({'create': False})
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('id', 'in', self.move_id.ids)]
        action['view_mode'] = 'form'
        action['context'] = context
        return action

    def button_petty_cash_complete(self):
        """functions for confirm petty cash balanced"""
        self.ensure_one()

        self.ensure_one()
        for cash_in in self.cash_in_line_ids:
            if cash_in.state not in ('toppedup', 'reject', 'draft'):
                raise ValidationError(" (%s) - TopUp is not  toppedup or rejected " % cash_in.name)

        for iou in self.cash_issue_line_ids:
            if iou.state not in ('complete', 'reject', 'draft'):
                raise ValidationError(" (%s) - IOU Request is not completed or rejected " % iou.name)

        for cash_out in self.cash_out_line_ids:
            if cash_out.state not in ('complete', 'reject', 'draft'):
                raise ValidationError(" (%s) - Reimbursement is not completed or rejected " % cash_out.name)

        # CHECK IS THERE A CASH IN THE SELECTED JOURNAL
        if self.cash_balance == 0.00:
            self.state = 'complete'
        else:
            context = self.env.context.copy()
            context.update({
                'default_petty_cash_id': self.id,
                'default_journal_id': self.journal_id.id,
                'default_cash_balance': self.cash_balance,
            })
            view_id = self.env.ref('petty_cash.petty_cash_balance_wizard_form').id
            return {'type': 'ir.actions.act_window',
                    'name': _('Petty Cash Balance'),
                    'res_model': 'petty.cash.balance.wizard',
                    'target': 'new',
                    'view_mode': 'form',
                    'views': [[view_id, 'form']],
                    'context': context,
                    }

    def create_new_petty_cash_flow(self):
        """Create next petty cash"""
        date_range = self.env['ir.config_parameter'].sudo().get_param('petty_cash.petty_cash_date_range') or False
        petty_cash_val = {
            'start_date': self.end_date + timedelta(days=1),
            'end_date': self.end_date + timedelta(days=1 + int(date_range) if date_range else 30),
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'user_id': self.env.user.id
        }
        petty_cash = self.env['petty.cash'].create(petty_cash_val)
        if not self.is_transferred and self.cash_balance > 0.00:
            vals={
                'petty_cash_id': petty_cash.id,
                'request_date': fields.Datetime.now(),
                'cash_date': fields.Datetime.now(),
                'amount': self.cash_balance,
                'reason': "From %s" % self.name,
                'state': "done",
            }
            petty_cash_in = self.env['petty.cash.in'].create(vals)
            petty_cash.write({
                'cash_in_line_ids': [(4, petty_cash_in.id)],
                'cash_flow': petty_cash_in.amount,
            })
        self.state = "balance"
        return {
            'name': _('Petty Cash'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'petty.cash',
            'target': 'current',
            'res_id': petty_cash.id,
            'domain': [('id', '=', petty_cash.id)],
        }

    def unlink(self):
        """check validations for delete"""
        self.ensure_one()
        if self.move_id:
            raise ValidationError("Please delete relevant Journal entries (Top UP - %s)" % self.name)
        for topup in self.cash_in_line_ids:
            if topup.move_id:
                raise ValidationError("Please delete relevant Journal entries (Top UP - %s)" % topup.name)
            else:
                topup.sudo().unlink()
        for iou in self.cash_issue_line_ids:
            if iou.move_id:
                raise ("Please delete relevant Journal entries (Top UP - %s)" % iou.name)
            else:
                iou.sudo().unlink()

        for reimb in self.cash_out_line_ids:
            if reimb.move_id:
                raise ValidationError("Please delete relevant Journal entries (Top UP - %s)" % reimb.name)
            else:
                reimb.sudo().unlink()
        return super(PettyCash, self).unlink()


class PettyCashLine(models.Model):
    _name = "petty.cash.line"
    _description = "Petty Cash Lines"
    _order = 'create_date desc'

    name = fields.Char(required=True, string="number")
    petty_cash_id = fields.Many2one('petty.cash', string='Petty Cash Drawer')
    company_id = fields.Many2one('res.company', related='petty_cash_id.company_id')
    from_acc = fields.Many2one('account.account', string="Source")
    to_acc = fields.Many2one('account.account', string="Destination")
    reason = fields.Char(string="Reason")
    amount = fields.Float(string="Amount")
    status = fields.Char(compute="compute_line_status")
    is_completed = fields.Boolean(default=False)
    transfer_type = fields.Selection([
        ('cash drawer', 'Cash Drawer'),
        ('iou', 'IOU'),
        ('reimbursement', 'Reimbursement'),
        ('top up', 'TOP UP'),
    ], compute="compute_line_transfer_type", store=True)

    employee_id = fields.Many2one('hr.employee', string="Employee To")
    approved_by = fields.Many2one('res.users', string="Approved By")
    user_id = fields.Many2one('res.users', string="User")
    petty_cash_in = fields.Many2one('petty.cash.in', string="TopUp")
    cash_release_id = fields.Many2one('petty.cash.release', string="IOU Request")
    cash_reimbursement_id = fields.Many2one('petty.cash.out', string="Reimbursements")
    summary_report_id = fields.Many2one('reimbursement.summary.report')

    @api.depends('petty_cash_in', 'cash_release_id', 'cash_reimbursement_id', 'petty_cash_id')
    def compute_line_status(self):
        """ Get transaction status """

        for rec in self:
            if rec.petty_cash_in:
                rec.status = "TopUp - %s" % dict(rec.petty_cash_in._fields['state'].selection).get(rec.petty_cash_in.state)
            elif rec.cash_release_id:
                rec.status = "IOU - %s" % dict(rec.cash_release_id._fields['state'].selection).get(rec.cash_release_id.state)
            elif rec.cash_reimbursement_id:
                rec.status = "REM - %s" % dict(rec.cash_reimbursement_id._fields['state'].selection).get(rec.cash_reimbursement_id.state)
            else:
                rec.status = "Petty Cash Balanced"
            # Check process is Completed
            rec.is_completed = 'Completed' in rec.status

    @api.depends('petty_cash_in', 'cash_release_id', 'cash_reimbursement_id','petty_cash_id')
    def compute_line_transfer_type(self):
        """Compute transfer type"""
        for rec in self:
            if rec.petty_cash_in:
                rec.transfer_type = 'top up'

            elif rec.cash_release_id:
                rec.transfer_type = 'iou'

            elif rec.cash_reimbursement_id:
                rec.transfer_type = 'reimbursement'

            else:
                rec.transfer_type = 'cash drawer'

    def button_view_line_details(self):
        """Action for view details of summary list"""
        if self.petty_cash_in:
            # Open petty cash topup
            view_id = self.env.ref('petty_cash.view_petty_cash_in_form').id
            return {'type': 'ir.actions.act_window',
                    'name': _('Top UP'),
                    'res_model': 'petty.cash.in',
                    'res_id': self.petty_cash_in.id,
                    'target': 'new',
                    'view_mode': 'form',
                    'views': [[view_id, 'form']],
                    }
        elif self.cash_release_id:
            # Open Petty cash IOU
            view_id = self.env.ref('petty_cash.view_petty_cash_release_form').id
            return {'type': 'ir.actions.act_window',
                    'name': _('IOU'),
                    'res_model': 'petty.cash.release',
                    'res_id': self.cash_release_id.id,
                    'target': 'new',
                    'view_mode': 'form',
                    'views': [[view_id, 'form']],
                    }
        elif self.cash_reimbursement_id:
            # Open Petty cash Reimbursements
            view_id = self.env.ref('petty_cash.view_petty_cash_out_form').id
            return {'type': 'ir.actions.act_window',
                    'name': _('Reimbursement'),
                    'res_model': 'petty.cash.out',
                    'res_id': self.cash_reimbursement_id.id,
                    'target': 'new',
                    'view_mode': 'form',
                    'views': [[view_id, 'form']],
                    }

    def button_remove_line_details(self):
        """Action for view details of summary list"""
        self.summary_report_id = False

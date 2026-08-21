from odoo import models,fields,api,_


class SalaryAdjustmentRequest(models.Model):
    _name = 'salary.adjustment.request'
    _description = 'Salary Adjustment Request'
    _order = 'id desc'


    name = fields.Char(string="Reference", default="New", readonly=True, copy=False)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, help="Employee that will receive the salary increment/decrement")
    contract_id = fields.Many2one('hr.contract', string="Contract", required=True, help="Contract of the employee")
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='draft')
    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    requested_date = fields.Datetime(default=fields.Datetime.now)
    approved_by = fields.Many2one('res.users', help="Document approved by")
    approved_date = fields.Datetime(string="Approved Date", help="Document approved date")
    rejected_by = fields.Many2one('res.users', help="Uer that rejected the document")
    rejected_date = fields.Datetime(string="Rejected Date", help="Date when the document was rejected")
    reason = fields.Text(string="Reason")
    effective_date = fields.Date(string="Effective Date", required=True)
    note = fields.Text(string="Internal Notes")
    line_ids = fields.One2many('salary.adjustment.request.line', 'request_id', string="Lines")

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.line_ids = []
            contract = self.employee_id.contract_id
            self.contract_id = contract.id
            self.line_ids = [(0,0,{
                'type':'basic',
                'current_amount':contract.wage,
            })]
            data_set = []
            for allowance_record in contract.fixed_allowance_ids:
                new_line_data = (0, 0, {
                    'type': 'allowance',
                    'allowance_deduction_id': allowance_record.type_id.id,
                    'current_amount': allowance_record.amount,
                    'existing_record_id': allowance_record.id,
                })
                data_set.append(new_line_data)
            for deduction_record in contract.fixed_deduction_ids:
                new_line_data = (0, 0, {
                    'type': 'deduction',
                    'allowance_deduction_id': deduction_record.type_id.id,
                    'current_amount': deduction_record.amount,
                    'existing_record_id': deduction_record.id,
                })
                data_set.append(new_line_data)
            self.update({'line_ids': data_set})

    def action_submit(self):
        self.write({'state': 'submitted'})
        self.message_post(body="Salary Change Request has been submitted.")

    def action_approve(self):
        self.ensure_one()
        contract = self.contract_id
        if self.new_wage > contract.wage or self.new_wage < contract.wage:
            old = contract.wage
            contract.wage = self.new_wage
            message = _("Basic salary has been updated from %(old_wage).2f to %(new_wage).2f by %(approver_name)s.") % {
                'old_wage': old,
                'new_wage': self.new_wage,
                'approver_name': self.env.user.name
            }
            contract.message_post(body=message)
        for line in self.line_ids:
            if line.current_amount != line.new_amount:
                allowance_deduction_id = line.allowance_deduction_id
                old = line.current_amount
                new = line.new_amount
                line_type = line.type
                original_record_id = line.existing_record_id
                origin_record = self.env['fixed.allowance.deduction.line'].browse(original_record_id)
                origin_record.write({'amount': new})

                message = _(
                    "%(allowance_or_deduction) has been updated from %(old_wage).2f to %(new_wage).2f by %(approver_name)s.") % {
                              'allowance_or_deduction': line_type.capitalize(),
                              'old_wage': old,
                              'new_wage': new,
                              'approver_name': self.env.user.name
                          }
                self.contract_id.message_post(body=message)
        self.state = 'approved'
        self.approved_by = self.env.user
        self.write({'effective_date': fields.Date.today()})
        self.message_post(body="Salary Change Request has been approved.")



    def action_reject(self):
        self.write({'state': 'rejected'})
        self.message_post(body="Salary Change Request has been rejected.")


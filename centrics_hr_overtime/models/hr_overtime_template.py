from odoo import models,fields,api,_


class HrOvertimeTemplate(models.Model):
    _name = 'hr.overtime.template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Overtime Template'

    name = fields.Char(required=True, tracking=True, help="Name of the overtime template")
    is_global = fields.Boolean(string="Global Template", compute='_compute_is_global', store=True, tracking=True,
                               help="Indicates if this template applies globally or only to specific job positions")
    job_position_ids = fields.Many2many('hr.job', string="Job Positions", tracking=True,
                                        help="Specific job positions this template applies to")
    for_working_days = fields.Selection([
        ('predefined', 'Pre defined check-in and check-out'),
        ('working_schedule', 'Use Working Schedules')
    ], string='For Working Days', required=True, default='working_schedule', tracking=True,
        help="Define how working days should be calculated - using predefined times or working schedules")
    check_in_time = fields.Float(string="Check-in Time", tracking=True,
                                 help="Standard check-in time for overtime calculation")
    check_out_time = fields.Float(string="Check-out Time", tracking=True,
                                  help="Standard check-out time for overtime calculation")
    rule_ids = fields.One2many('hr.overtime.rule', 'template_id', string="Overtime Rules", order='sequence',
                               help="List of overtime rules associated with this template")
    multiple_rule_ids = fields.One2many('hr.overtime.rule', 'secondary_template_id', string="Overtime Rules", order='sequence',
                               help="List of overtime rules associated with this template")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True,
                                 help="Company this overtime template belongs to")
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Lock')], default='draft', tracking=True,)
    active = fields.Boolean(default=True, tracking=True, help="Whether this overtime template is active or archived")

    deduction_source = fields.Selection([
        ('worked_hours', 'Deduct from Worked Hours'),
        ('ot_hours', 'Deduct From OT Hours'),
    ], string='Deduction Source', default='ot_hours', required=True, tracking=True,
        help="Determines whether dynamic deductions are subtracted from worked hours or overtime hours")

    enable_multiple_days = fields.Boolean(string="Enable Multiple Days", default=False, tracking=True, help="Enable Multiple Days")
    need_to_continue_from_first_day = fields.Boolean(string="Need to Continue from First Day", default=False, tracking=True, help="Need to Continue from First Day")
    use_separate_overtime_rule = fields.Boolean(string="Use Separate Overtime Rule", default=False, tracking=True, help="Use Separate Overtime Rule")

    @api.depends('job_position_ids')
    def _compute_is_global(self):
        """
        Computes the 'is_global' attribute based on the presence of related
        job positions. The attribute is set to `False` when there are associated
        job positions and `True` otherwise.

        Parameters
        ----------
        self : recordset
            The set of records for which the computation is performed.

        Attributes
        ----------
        is_global : bool
            A computed attribute indicating whether the record is global
            (when there are no related job positions, it is `True`). Otherwise,
            it is `False`.
        """
        for record in self:
            record.is_global = False if record.job_position_ids else True

    def action_lock(self):
        """Lock the template to prevent further changes."""
        self.ensure_one()
        self.write({'state': 'lock'})

    def action_set_to_draft(self):
        """Reopen the template for editing."""
        # Allow batch operation to set multiple records back to draft
        self.write({'state': 'draft'})



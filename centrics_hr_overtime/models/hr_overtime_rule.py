from odoo import models, fields, api, _
from odoo.exceptions import UserError

SELECTION_RULE_TYPE = [
    ('normal', 'Normal OT'),
    ('double', 'Double OT'),
    ('triple', 'Triple OT')
]

CONDITION_TYPE = [
    ('upto_hours', 'Upto X Hours'),
    ('remaining_hours', 'Remaining Hours'),
    ('full_day', 'Full Day')
]

APPLY_ON = [
    ('scheduled_days_check_in', 'Scheduled Days(Check In)'),
    ('scheduled_days_check_out', 'Scheduled Days(Check Out)'),
    ('weekends', 'Weekends'),
    ('holidays', 'Public/Mercantile Holidays'),
    ('all', 'All Days')
]


class HrOvertimeRule(models.Model):
    _name = 'hr.overtime.rule'
    _description = 'Overtime Rule'
    _order = 'sequence, id'  # Ensures ordering by sequence in all views

    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string="Overtime Rule Name")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    rule_type = fields.Selection(selection=SELECTION_RULE_TYPE)
    apply_on = fields.Selection(selection=APPLY_ON, default='all')
    condition = fields.Selection(selection=CONDITION_TYPE, default='after_checkout')
    threshold_hours = fields.Float('Threshold (Hours)', help="Applicable for double OT")
    template_id = fields.Many2one('hr.overtime.template')
    secondary_template_id = fields.Many2one('hr.overtime.template')
    deduction_ids = fields.Many2many('overtime.dynamic.deduction', string='Deductions')

    @api.onchange('rule_type', 'condition')
    def onchange_name(self):
        """
            Updates the name based on the selected rule type and condition.

            The method is triggered whenever there is a change in the 'rule_type' or
            'condition' fields. It constructs the 'name' attribute by mapping the
            rule type and condition values to their respective string representations
            and concatenates them with a separator.

            Raises:
                None

            Args:
                None

            Returns:
                None
        """
        SELECTION_RULE_TYPE_DICT = dict(SELECTION_RULE_TYPE)
        CONDITION_TYPE_DICT = dict(CONDITION_TYPE)
        APPLICATION_DICT = dict(APPLY_ON)
        if SELECTION_RULE_TYPE_DICT.get(self.rule_type) and APPLICATION_DICT.get(
                self.apply_on) and CONDITION_TYPE_DICT.get(self.condition):
            self.name = SELECTION_RULE_TYPE_DICT.get(self.rule_type) + "-" + APPLICATION_DICT.get(
                self.apply_on) + " - " + CONDITION_TYPE_DICT.get(self.condition)
        if self.condition != 'upto_hours':
            self.threshold_hours = 0

    @api.model
    def create(self, values):
        """
        Creates a new record with provided values, with additional validation for specific conditions.

        This method is overridden to include additional logic for handling the
        'condition' and 'threshold_hours' fields. If the condition is 'after_hours',
        a validation check ensures that the 'threshold_hours' is greater than 0
        before creating the record.

        Parameters
        ----------
        values : dict
            A dictionary containing the fields and their respective values needed for
            creating the record. Must include keys such as 'condition' and optionally
            'threshold_hours' if relevant.

        Returns
        -------
        res : recordset
            The newly created record after validation and creation.

        Raises
        ------
        UserError
            If 'condition' is 'after_hours' and 'threshold_hours' is less than or
            equal to 0.
        """
        res = super(HrOvertimeRule, self).create(values)
        if values.get('condition') == 'upto_hours':
            if values.get('threshold_hours') <= 0:
                raise UserError(_('Threshold Hours must be greater than 0.'))
        return res

    def write(self, values):
        """
        Modifies records based on input values and applies validation rules for
        specific conditions.

        The method first writes the changes in the inherited class. After applying
        the changes, if the 'condition' field in `values` has the value
        'after_hours', it verifies whether the threshold_hours for each record
        is greater than 0. If the condition is not met, an error is raised.

        Parameters
        ----------
        values : dict
            A dictionary of field-value pairs to be written to the records.

        Returns
        -------
        bool
            Returns True if the write operation is successful, otherwise False.

        Notes
        -----
        This method overrides the `write` method from a parent class and injects
        additional logic to implement validation for specific conditions.
        """
        res = super(HrOvertimeRule, self).write(values)
        if 'condition' in values and values['condition'] == 'upto_hours':
            for record in self:
                if record.threshold_hours <= 0:
                    raise UserError(_('Threshold Hours must be greater than 0.'))
        return res

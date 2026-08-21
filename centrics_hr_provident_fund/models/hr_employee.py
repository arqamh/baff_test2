from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    """
    Employee Model Extension for Provident Fund Management

    Extends the base hr.employee model to add EPF (Employees' Provident Fund) and
    ETF (Employees' Trust Fund) related fields and validations.

    All EPF/ETF fields are organized in the 'HR Settings' tab under the
    'EPF/ETF Information' section in the employee form view.
    """
    _inherit = 'hr.employee'

    is_provident_fund_eligible = fields.Boolean(
        string="Eligible for EPF?",
        help="Check this if the employee is eligible for Employees' Provident Fund contributions"
    )
    epf_number = fields.Char(
        string="EPF Number",
        help="Unique EPF registration number assigned to the employee"
    )
    date_of_epf_resisted = fields.Date(
        string="Date of EPF Registered",
        help="Date when the employee was registered for EPF"
    )
    occupational_group_id = fields.Many2one(
        'occupational.group',
        string="Occupational Group",
        help="Occupational classification group for EPF/ETF reporting purposes"
    )
    epf_employment_type_id = fields.Many2one(
        'epf.employment.type',
        string="EPF Employment Type",
        help="Employment type category for EPF calculations and reporting"
    )

    @api.constrains('is_provident_fund_eligible', 'name_initials', 'last_name')
    def _check_epf_required_fields(self):
        """
        Validate required fields for EPF-eligible employees.

        Ensures that EPF-eligible employees have both name_initials and last_name filled.
        These fields are mandatory for EPF registration and reporting purposes.

        Raises:
            ValidationError: If an EPF-eligible employee is missing name_initials or last_name

        Note:
            This constraint ensures compliance with EPF registration requirements which
            mandate proper name formatting for all registered employees.
        """
        for record in self:
            if record.is_provident_fund_eligible:
                if not record.name_initials:
                    raise ValidationError(_("Initials of the Name is required when employee is eligible for EPF."))
                if not record.last_name:
                    raise ValidationError(_("Last Name is required when employee is eligible for EPF."))

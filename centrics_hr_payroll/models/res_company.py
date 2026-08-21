from odoo import models, fields, api, _

NO_OF_DAYS = [
    ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'),
    ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('15', '15'),
    ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), ('21', '21'), ('22', '22'),
    ('23', '23'), ('24', '24'), ('25', '25'), ('26', '26'), ('27', '27'), ('28', '28'), ('29', '29'),
    ('30', '30'), ('31', '31')
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    is_standard_day_for_payroll = fields.Boolean(string="Is Standard Day for Payroll")
    standard_payroll_day = fields.Selection(selection=NO_OF_DAYS, string="Standard Payroll Day")
    skip_work_entry_validation = fields.Boolean(
        string='Skip Work Entry Validation',
        default=False,
        help='When enabled, payslip generation will not require work entries to be created. '
             'Worked days will be calculated based on the employee calendar instead.'
    )

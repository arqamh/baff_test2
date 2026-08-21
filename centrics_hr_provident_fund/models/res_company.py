from odoo import models, fields, api, _


class ResCompany(models.Model):
    """
    Company Model Extension for EPF Configuration

    Extends the base res.company model to add EPF (Employees' Provident Fund)
    specific configuration fields required for EPF contribution reporting.
    """
    _inherit = 'res.company'

    epf_employer_number = fields.Char(
        string="EPF Employer Number",
        help="Company's EPF employer registration number used in EPF contribution reports"
    )
    epf_zone_code = fields.Char(
        string="EPF Zone Code",
        help="EPF zone code assigned to the company for regional reporting"
    )

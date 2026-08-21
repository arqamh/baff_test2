from odoo import models, fields, api, _

MONTHS = [
    ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'), ('6', 'June'),
    ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')]


class EmployeeLoanInstallmentLine(models.Model):
    _name = "employee.loan.installment.line"
    _description = "Employee Loan Installment Line"

    def name_get(self):
        """
        Generates and returns a list of tuples containing contextual information about each loan record.

        This function constructs a display name for each loan record by concatenating the employee's name,
        the installment reference number, and the year/month of the record. These names are used for
        representing and identifying the records in a readable and meaningful way.

        Returns
        -------
        list of tuple of (int, str)
            A list where each element is a tuple. The first element of the tuple is the record ID, while the
            second element is the generated display name constructed from the employee's loan details.
        """
        result = []
        for record in self:
            name = record.employee_loan_id.employee_id.name + " - " + record.installment_ref_number + " - " + str(record.year) + "/ " + record.month
            result.append((record.id, name))
        return result

    employee_loan_id = fields.Many2one('employee.loan', string="Loan")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    installment_ref_number = fields.Char(string="Installment Number")
    year = fields.Integer(string="Year")
    month = fields.Selection(selection=MONTHS, string="Month")
    capital_amount = fields.Float(string="Capital Amount")
    interest_amount = fields.Float(string="Interest Amount")
    installment_amount = fields.Float(string="Installment Amount")

    paid_capital_amount = fields.Float(string="Paid Capital Amount", default=0.0)
    paid_interest_amount = fields.Float(string="Paid Interest Amount", default=0.0)

    running_balance = fields.Float(string="Running Balance")
    status = fields.Selection([('draft', 'Draft'), ('paid', 'Paid'), ('skip', 'Skipped')], string="Status",defualt='draft' )
    payment_method = fields.Selection([
        ('payroll', 'Payroll'),
        ('manual', 'Manual'),
        ('mixed', 'Mixed'),
    ], string="Payment Method", default='payroll')

from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class IncreaseCashFloatWizard(models.TransientModel):
    """
    Wizard for increase cash float
    """
    _name = 'petty.cash.increase.cashfloat.wizard'
    _description = 'Increase Cash Float Wizard'

    def default_get(self, fields):
        """Get default value from context petty cash id and float amount"""
        result = super(IncreaseCashFloatWizard, self).default_get(fields)
        result.update({
            'petty_cash_id': self._context.get('active_id'),
            'new_cash_float': self._context.get('cash_float_amount'),
        })
        return result

    user_id = fields.Many2one('res.users', string="User",  default=lambda self: self.env.user.id)
    petty_cash_id = fields.Many2one('petty.cash')
    current_cash_float = fields.Float(related="petty_cash_id.petty_cash_float", string="Current Cash Float")
    new_cash_float = fields.Float(string="New Cash Float")

    def confirm_submission(self):
        """Confirm the wizard"""
        if not self.new_cash_float or self.current_cash_float >= self.new_cash_float:
            raise ValidationError("New Cash Float amount must be greater than current amount")
        self.petty_cash_id.sudo().write({
            'petty_cash_float': self.new_cash_float,
            'increased_float_amount': self.new_cash_float - self.current_cash_float,
            'is_available_topup': True
        })

        message = _(
            '''
                <h5>Cash float is increased- %s</h5>
                Update By - %s <br/> 
                Date - %s  
            ''' % (self.new_cash_float, self.user_id.name, str(fields.Datetime.now())))

        self.petty_cash_id.sudo().message_post(body=message, message_type='comment')

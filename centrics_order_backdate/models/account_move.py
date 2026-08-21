from odoo import models, api, fields
import pytz
from datetime import datetime, timedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    def cron_action_update_move_backdate(self, user_tz=False):
        """Automation for update valuation entry with backdate"""

        for record in self:
            if record.stock_move_id:
                move_date = record.stock_move_id.date or record.stock_move_id.date_deadline
                # entry reset to draft and reset entry no to false
                record.button_draft()
                record.name = False
                if user_tz:
                    # update time stamp
                    user_tz = self.env.user.tz
                    new_tz = pytz.timezone(user_tz)
                    record.date = pytz.timezone('UTC').localize(move_date).astimezone(new_tz)
                else:
                    record.date = move_date + timedelta(hours=5, minutes=30)

                record._compute_name()
                record.action_post()

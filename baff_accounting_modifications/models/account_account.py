from odoo import models, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    def write(self, vals):
        """ Override write method to add custom validations and logic. """
        # Do not allow changing the company_id when account_move_line already exist
        if vals.get('company_id', False):
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            for account in self:
                if (account.company_id.id != vals['company_id']) and move_lines:
                    raise UserError(_('You cannot change the owner company of an account that already contains journal items.'))
        if 'reconcile' in vals:
            if vals['reconcile']:
                self.filtered(lambda r: not r.reconcile)._toggle_reconcile_to_true()
            else:
                self.filtered(lambda r: r.reconcile)._toggle_reconcile_to_false()

        # Store currency_id for later processing if bypass is enabled
        currency_id_to_set = None
        bypass_currency_validation = False

        if vals.get('currency_id'):
            for account in self:
                # Check if any related journal has bypass_currency_validation enabled
                journals = self.env['account.journal'].search([
                    '|', '|', '|', '|',
                    ('default_account_id', '=', account.id),
                    ('suspense_account_id', '=', account.id),
                    ('profit_account_id', '=', account.id),
                    ('loss_account_id', '=', account.id),
                    ('account_control_ids', 'in', account.id)
                ])

                # Also check payment method line accounts
                payment_method_lines = self.env['account.payment.method.line'].search([
                    ('payment_account_id', '=', account.id)
                ])
                journals |= payment_method_lines.mapped('journal_id')

                # Check if any of the journals have bypass enabled
                if journals and any(journal.bypass_currency_validation for journal in journals):
                    bypass_currency_validation = True
                    break

                # If bypass is not enabled, perform the standard validation
                if self.env['account.move.line'].search_count([
                    ('account_id', '=', account.id),
                    ('currency_id', 'not in', (False, vals['currency_id']))
                ]):
                    raise UserError(_(
                        'You cannot set a currency on this account as it already has '
                        'some journal entries having a different foreign currency.'
                    ))

        # If bypass is enabled, remove currency_id from vals to prevent core validation
        if bypass_currency_validation and vals.get('currency_id'):
            currency_id_to_set = vals.pop('currency_id')

        # Call super with modified vals
        result = super(AccountAccount, self).write(vals)

        # If we bypassed validation, now set the currency directly
        if bypass_currency_validation and currency_id_to_set:
            # Use SQL to bypass the constraint check in the core and avoid recursion
            self._cr.execute(
                "UPDATE account_account SET currency_id = %s WHERE id IN %s",
                (currency_id_to_set, tuple(self.ids))
            )
            self.invalidate_recordset(['currency_id'])

        return result

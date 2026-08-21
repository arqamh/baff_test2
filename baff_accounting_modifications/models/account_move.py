from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    bill_reference = fields.Char(string="Bill Reference", required=True)

    @api.onchange('bill_reference')
    def _onchange_bill_reference(self):
        """Automatically assign bill_reference to ref when bill_reference changes"""
        for record in self:
            record.ref = record.bill_reference

    @api.constrains('partner_id', 'bill_reference', 'move_type')
    def _check_unique_vendor_bill_reference(self):
        """Enforce (partner_id, bill_reference) uniqueness only for vendor
        bills. Debit notes (in_refund) and other move types legitimately
        reuse the same combination."""
        for rec in self:
            if rec.move_type != 'in_invoice':
                continue
            if not rec.partner_id or not rec.bill_reference:
                continue
            duplicate = self.search([
                ('id', '!=', rec.id),
                ('move_type', '=', 'in_invoice'),
                ('partner_id', '=', rec.partner_id.id),
                ('bill_reference', '=', rec.bill_reference),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    "The combination of Vendor and Bill Reference must be "
                    "unique for vendor bills.\n"
                    "Existing bill: %s") % duplicate.display_name)

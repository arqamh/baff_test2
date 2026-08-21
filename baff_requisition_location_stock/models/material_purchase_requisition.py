from odoo import _, api, models
from odoo.exceptions import UserError


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    def _check_header_location_required(self):
        for rec in self:
            if not rec.header_location_id:
                raise UserError(_(
                    "Please select a Source Location on requisition '%s' "
                    "before confirming. Material requests must be raised against "
                    "a specific location.",
                    rec.name or _('(new)')))

    def requisition_confirm(self):
        self._check_header_location_required()
        return super().requisition_confirm()

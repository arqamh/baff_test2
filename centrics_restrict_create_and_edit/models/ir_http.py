# -*- coding: utf-8 -*-
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """Expose the map of restricted Many2one fields to the web client.

        The JS patch in static/src/js/many2one_restrict.js reads
        `session.restrict_create_and_edit` and hides the 'Create' /
        'Create and Edit' dropdown options for matching fields.
        """
        result = super().session_info()
        if self.env.user._is_internal():
            result['restrict_create_and_edit'] = (
                self.env['restrict.create.and.edit']._get_active_restrictions()
            )
        return result

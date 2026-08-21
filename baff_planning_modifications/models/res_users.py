from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_sales_rep = fields.Boolean(string='Sales Rep', default=False)
    color_pick = fields.Integer(string='Color')

    @api.onchange('color_pick')
    def _colorpick(self):
        """
        Handles the onchange event for the 'color_pick' field.

        This method is triggered when the value of the 'color_pick' field changes.
        If a value for 'color_pick' is provided, the 'is_sales_rep' field is set to True.

        Fields:
        - color_pick: Field to track color selection.
        - is_sales_rep: Boolean field updated based on 'color_pick'.
        """
        if self.color_pick:
            self.is_sales_rep = True


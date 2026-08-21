from odoo import models, api, fields


class InheritMrpWorkorderAdditionalProduct(models.TransientModel):
    _inherit = "mrp_workorder.additional.product"

    def add_product(self):
        """ Overriding core method to call cost buffer calculating method and component approval method """
        super(InheritMrpWorkorderAdditionalProduct, self).add_product()
        values = self.workorder_id.production_id.calculate_cost_buffer()
        self.workorder_id.production_id.new_components_approval(values)
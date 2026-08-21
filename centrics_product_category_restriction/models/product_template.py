from odoo import api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    can_change_category = fields.Boolean(
        string='Can Change Category',
        compute='_compute_can_change_category'
    )

    @api.depends_context('uid', 'company')
    def _compute_can_change_category(self):
        """Compute if user can change product category based on company settings."""
        company = self.env.company
        for product in self:
            # If restriction is disabled, everyone can change
            if not company.restrict_product_category_change:
                product.can_change_category = True
            # If restriction is enabled, only users with the group can change
            elif self.user_has_groups(
                'centrics_product_category_restriction.group_change_product_category'
            ):
                product.can_change_category = True
            else:
                product.can_change_category = False

    def write(self, vals):
        """Override write to check permission for category change."""
        if 'categ_id' in vals:
            company = self.env.user.company_id
            if company.restrict_product_category_change:
                if not self.user_has_groups(
                    'centrics_product_category_restriction.group_change_product_category'
                ):
                    raise UserError(
                        'You do not have permission to change product '
                        'category. Please contact your administrator.'
                    )
        return super(ProductTemplate, self).write(vals)

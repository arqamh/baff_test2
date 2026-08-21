from odoo import fields, models, api, _
from odoo.exceptions import UserError


class InheritMrpBom(models.Model):
    _inherit = 'mrp.bom'

    def _parent_component_id_domain(self):
        """OPTIMIZED: Replaced search([]).filtered() with proper domain-based query"""
        domain = []
        if self._context.get('default_job_cost_id'):
            # Direct search with domain - much faster than loading all records
            job_cost_lines = self.env['job.cost.line'].search([
                ('job_costing_id', '=', self._context.get('default_job_cost_id'))
            ])
            boms = job_cost_lines.mapped('bom_id')
            if boms:
                domain = [('id', 'in', boms.ids)]
        return domain

    job_cost_id = fields.Many2one('job.costing', string="Job Cost No")
    analytic_plan_id = fields.Many2one('account.analytic.plan', string="Cost Center", tracking=True)
    name = fields.Char(string="Component")
    parent_component_id = fields.Many2one('mrp.bom', string="Parent Component", domain=_parent_component_id_domain)
    is_additional_component = fields.Boolean(string="Is Additional Component", default=False)
    boat_type_id = fields.Many2one('boat.type', string="Boat Type")

    @api.model_create_multi
    def create(self, vals):
        # OPTIMIZED: Resolve routes once outside the loop
        mto_route = self.env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)
        manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture', raise_if_not_found=False)
        for val in vals:
            product = False
            if val.get('is_additional_component'):
                lines = []
                if mto_route:
                    lines.append(mto_route.id)
                else:
                    raise UserError(_("Could not find the Make To Order route to create the product"))
                if manufacture_route:
                    lines.append(manufacture_route.id)
                else:
                    raise UserError(_("Could not find the Manufacture route to create the product"))
                product = self.env['product.template'].create({
                    'name': val.get('name'),
                    'detailed_type': 'product',
                    'sale_ok': True,
                    'route_ids': [(6, 0, lines)]
                })
                if product:
                    val['product_tmpl_id'] = product.id
        result = super().create(vals)
        if result.is_additional_component and result.job_cost_id:
            self.env['job.cost.line'].create({
                'job_costing_id': result.job_cost_id.id,
                'parent_bom_id': result.parent_component_id.id,
                'bom_id': result.id,
                'product_qty': result.product_qty,
                'product_id': product.id,
                'job_type': 'material'
            })
        return result

    def write(self, values):

        result = super().write(values)

        return result


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    jobcost_line_id = fields.Many2one('job.cost.line', string="Job Cost Line")

    @api.depends('product_id', 'bom_id')
    def _compute_child_bom_id(self):
        """Overwrite the core function for generate the sequence of subcomponents.

        OPTIMIZED: Eliminated duplicate conditional logic using helper method.
        """
        products = self.product_id
        bom_by_product = self.env['mrp.bom']._bom_find(products)

        def get_first_bom(bom_recordset):
            """Helper to get first BOM from recordset or return False"""
            if not bom_recordset:
                return False
            return bom_recordset[0].id if len(bom_recordset) > 1 else bom_recordset.id

        def find_standard_bom(product):
            """Helper to find standard BOM for a product"""
            if not product or not product.bom_ids:
                return False
            standard_boms = product.bom_ids.filtered(lambda x: x.is_this_standard_bom == True)
            return get_first_bom(standard_boms)

        for line in self:
            # Early exit if no product
            if not line.product_id:
                line.child_bom_id = False
                continue

            # If parent BOM has job_cost_id, try to find matching job cost BOM first
            if line.bom_id.job_cost_id:
                job_cost_bom = line.product_id.bom_ids.filtered(
                    lambda x: x.job_cost_id.id == line.bom_id.job_cost_id.id
                )
                if job_cost_bom:
                    line.child_bom_id = get_first_bom(job_cost_bom)
                    continue

            # Fall back to standard BOM lookup
            line.child_bom_id = find_standard_bom(line.product_id)
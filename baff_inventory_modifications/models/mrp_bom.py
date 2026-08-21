from odoo import fields, models, api, _


class InheritMrpBom(models.Model):
    _inherit = 'mrp.bom'

    boat_type_ids = fields.Many2many('boat.type', string="Boat Type", compute='_compute_boat_type_assign', store=True)
    is_this_standard_bom = fields.Boolean(string="Is this Standard BOM", tracking=True)
    bom_type = fields.Selection([('base_bom', 'Base BOM'), ('option_bom', 'Option BOM')], string="BOM Type", related='product_tmpl_id.bom_type')

    @api.depends('product_tmpl_id.bom_type', 'product_tmpl_id.boat_type_ids', 'product_tmpl_id.boat_type_id', )
    def _compute_boat_type_assign(self):
        """Assign the boat type"""
        for rec in self:
            if rec.bom_type == 'base_bom':
                rec.boat_type_ids = rec.product_tmpl_id.boat_type_id.ids
            else:
                if rec.bom_type == 'option_bom':
                    rec.boat_type_ids = rec.product_tmpl_id.boat_type_ids.ids

    @api.onchange('product_tmpl_id', 'product_id')
    def _onchange_product(self):
        """ Setting 'is standard bom' based on the product """
        for record in self:
            if record.product_tmpl_id and not record.job_cost_id:
                record.is_this_standard_bom = record.product_tmpl_id.is_this_standard_bom
            elif record.product_id and not record.job_cost_id:
                record.is_this_standard_bom = record.product_id.is_this_standard_bom

    def action_true_standard_bom(self):
        # This Function For Change bom type standard
        for line in self:
            line.is_this_standard_bom = True

    def action_false_standard_bom(self):
        # This Function For Change bom type not standard
        for line in self:
            line.is_this_standard_bom = False

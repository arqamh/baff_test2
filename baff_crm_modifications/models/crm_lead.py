from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    inquiry_number = fields.Char('Inquiry Number', readonly='1', index=True, default='New')
    product_name = fields.Char(string="Product Name")
    boat_type_id = fields.Many2one(comodel_name='boat.type', string="Boat Type")

    @api.model
    def create(self, vals):
        """Adding a sequence number(inquiry number) for each lead in the CRM module"""
        vals['inquiry_number'] = self.env['ir.sequence'].next_by_code('inquiry.number') or _('New')
        return super(CrmLead, self).create(vals)

    def name_get(self):
        """Show inquiry number and name values in many2one field in job costing sheet"""
        inquiry_list = []
        for lead in self:
            name = '[%s] %s' % (lead.inquiry_number, lead.name)
            inquiry_list.append((lead.id, name))
        return inquiry_list

    def prepare_opportunity_quotation_context_unique(self):
        """ Overriding core method to create a product when creating quotation from an opportunity. """
        self.ensure_one()
        order_lines = []
        quotation_context = {
            'opportunity_id': self.id,
            'partner_id': self.partner_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'origin': self.name,
            'source_id': self.source_id.id,
            'boat_type_id': self.boat_type_id.id,
            'company_id': self.company_id.id or self.env.company.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            # 'order_line': [(6, 0, order_lines)]
            'order_line': [(5, 0)]
        }
        if self.product_name:
            lines = []
            # Getting MTO and Manufacture product routes
            if self.env.ref('stock.route_warehouse0_mto'):
                lines.append(self.env.ref('stock.route_warehouse0_mto').id)
            else:
                UserError(_("Could not found the route %s to create the product", self.env.ref('stock.route_warehouse0_mto').name))
            if self.env.ref('mrp.route_warehouse0_manufacture'):
                lines.append(self.env.ref('mrp.route_warehouse0_manufacture').id)
            else:
                UserError(_("Could not found the route %s to create the product", self.env.ref('stock.route_warehouse0_manufacture').name))
            # Checking whether there is a existing product for the relevant inquery number
            product = self.env['product.product'].search([('name', '=', self.product_name)], limit=1)
            if product:
                # Updating the existing product
                quotation_context['order_line'].append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                }))
            else:
                # Creating a new product
                product = self.env['product.product'].create({
                    'name': self.product_name,
                    'detailed_type': 'product',
                    'sale_ok': True,
                    'route_ids': [(6, 0, lines)]
                })
                # Adding product to quotation lines
                if product:
                    quotation_context['order_line'].append((0, 0, {
                        'product_id': product.id,
                        'product_uom_qty': 1,
                    }))
        if self.team_id:
            quotation_context['team_id'] = self.team_id.id
        if self.user_id:
            quotation_context['user_id'] = self.user_id.id
        order = self.env['sale.order'].create(quotation_context)
        if order:
            action = {
                'name': 'Quotation',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': order.id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current'
            }
            return action

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MergeProcurementPlanWizard(models.Model):
    _name = 'merge.procurementplan.wizard'
    _description = 'Merge Procurement Plan Wizard'

    def default_get(self, fields):
        """Override default get method to add default value from context"""
        res = super().default_get(fields)
        if self.env.context.get('procurement_plan_ids'):
            res['procurement_plan_ids'] = self.env.context.get('procurement_plan_ids')
        return res

    merge_procurement_plans = fields.Boolean(default=False)
    vendor_ids = fields.Many2many('res.partner')
    procurement_tooltip = fields.Char(compute="compute_procurement_tooltip")
    is_single_order = fields.Boolean(default=True)
    procurement_plan_ids = fields.One2many('merge.procurementplan.wizard.line', 'wizard_id')

    @api.depends('merge_procurement_plans', 'vendor_ids')
    def compute_procurement_tooltip(self):
        """Compute tooltip field
            return summary when change fields value
        """
        for record in self:
            message = ''
            if record.merge_procurement_plans:
                message += 'Add all procurement lines into a single RFQ. \n'
                if record.vendor_ids:
                    message += 'These orders will be created for -( %s )' % ', '.join(record.vendor_ids.mapped('name'))
            else:
                message += 'Generate separate orders for the procurement lines.  \n'
                if record.vendor_ids:
                    message += 'These orders will be created for  -( %s )' % ', '.join(record.vendor_ids.mapped('name'))
            record.procurement_tooltip = message

    def create_rfq(self):
        """Create RFQ for selected records
            if user select multiple vendors this will create multiple orders for
        """
        if not self.vendor_ids:
            raise ValidationError("Select vendor(s) for create RFQ")

        purchase_order_obj = self.env['purchase.order']
        for vendor in self.vendor_ids:
            if self.merge_procurement_plans:
                # if merge all lines to single order
                order_vals = self.return_purchase_order_vals(vendor)
                order_lines_by_product = {}
                for line in self.procurement_plan_ids:
                    product_id, vals = self.return_purchase_order_line_vals(line)
                    if product_id not in order_lines_by_product.keys():
                        order_lines_by_product[product_id] = vals
                    else:
                        order_lines_by_product[product_id]['product_qty'] += vals['product_qty']
                        order_lines_by_product[product_id]['procurement_plan_ids'][0][2].extend(vals['procurement_plan_ids'][0][2])
                        order_lines_by_product[product_id]['date_planned'] = vals['date_planned'] if order_lines_by_product[product_id]['date_planned'] > vals['date_planned'] else order_lines_by_product[product_id]['date_planned']
                    # order_vals['origin'] += line.procurement_id.source + ', '
                order_lines_vals = [(0, 0, val) for val in order_lines_by_product.values()]
                order_vals['order_line'].extend(order_lines_vals)
                purchase_order_obj.create(order_vals)

            else:
                for line in self.procurement_plan_ids:
                    order_vals = self.return_purchase_order_vals(vendor)

                    order_lines_by_product = {}
                    product_id, vals = self.return_purchase_order_line_vals(line)
                    if product_id not in order_lines_by_product.keys():
                        order_lines_by_product[product_id] = vals
                    else:
                        order_lines_by_product[product_id]['product_qty'] += vals['product_qty']
                        order_lines_by_product[product_id]['procurement_plan_ids'][0][2].extend(vals['procurement_plan_ids'][0][2])
                        order_lines_by_product[product_id]['date_planned'] = vals['date_planned'] if order_lines_by_product[product_id]['date_planned'] > vals['date_planned'] else order_lines_by_product[product_id]['date_planned']

                    order_lines_vals = [(0, 0, val) for val in order_lines_by_product.values()]
                    order_vals['order_line'].extend(order_lines_vals)
                    order_vals['origin'] += 'Procurement Plan - ' + line.procurement_id.name
                    purchase_order_obj.create(order_vals)

    def return_purchase_order_vals(self, vendor):
        """Return values for 'purchase.order' """
        order_vals = {
                'partner_id': vendor.id,
                'origin': 'Procurement Plan - ',
                'order_line': [],
            }
        return order_vals

    def return_purchase_order_line_vals(self, procurement_plan):
        """Return values for 'purchase.order.line' """
        line_vals = (procurement_plan.product_id.id, {
            'procurement_plan_ids': [(6,0, [procurement_plan.procurement_id.id])],
            'product_id': procurement_plan.product_id.id,
            'product_qty': procurement_plan.order_qty,
            'product_uom': procurement_plan.product_uom.id,
            'date_planned': procurement_plan.scheduled_date,
        })
        return line_vals


class MergeProcurementPlanWizardLine(models.Model):
    _name = 'merge.procurementplan.wizard.line'
    _description = 'Merge Procurement Plan Wizard Lines'

    wizard_id = fields.Many2one('merge.procurementplan.wizard')
    procurement_id = fields.Many2one('procurement.plan', required=True)
    product_id = fields.Many2one('product.product', related='procurement_id.product_id')
    product_tml_id = fields.Many2one('product.template', related='procurement_id.product_tml_id')
    product_uom = fields.Many2one('uom.uom', related='procurement_id.product_uom')
    source = fields.Char(related='procurement_id.source')
    scheduled_date = fields.Date(related='procurement_id.scheduled_date')
    required_qty = fields.Float(related='procurement_id.required_qty')
    on_hand_qty = fields.Float(related='procurement_id.on_hand_qty')
    forecasted_qty = fields.Float(related='procurement_id.forecasted_qty')
    to_order_qty = fields.Float(related='procurement_id.to_order_qty')
    partner_id = fields.Many2one('res.partner', string="Vendor", related='procurement_id.partner_id')
    partner_ids = fields.Many2many('res.partner', string="Vendors", related='procurement_id.partner_ids')
    lead_time = fields.Float(related='procurement_id.lead_time')
    order_last_date = fields.Date(related='procurement_id.order_last_date')
    company_id = fields.Many2one('res.company', related='procurement_id.company_id')
    order_qty = fields.Float(default=0.00)

    def onchange_procurement_id(self):
        """run method when change procurement_id
            update order_qty
        """
        for record in self:
            if record.procurement_id:
                record.order_qty = record.procurement_id.remaining_to_order
            else:
                record.order_qty = 0.00

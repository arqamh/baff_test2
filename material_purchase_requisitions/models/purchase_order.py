from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    custom_requisition_id = fields.Many2one('material.purchase.requisition', string='Requisitions', copy=False)
    is_asset_purchase = fields.Boolean(string='Asset Purchase', copy=False, tracking=True)
    asset_location_id = fields.Many2one('stock.location', string='Asset Location', copy=False, tracking=True,
                                        domain="[('usage', '=', 'internal')]",
                                        help="Location where the purchased asset will be delivered/installed.")

    @api.model
    def _find_asset_picking_type(self, asset_location, company):
        """Return the incoming picking type for ``asset_location``.

        Preference order:
          1. Incoming picking type whose default destination *is* the asset location.
          2. Incoming picking type whose warehouse contains the asset location.
          3. Incoming picking type whose warehouse's view location is an ancestor
             of the asset location (parent_path containment).
        """
        PickingType = self.env['stock.picking.type']
        if not asset_location:
            return PickingType

        def _with_company(domain):
            if company:
                return domain + ['|', ('company_id', '=', company.id), ('company_id', '=', False)]
            return domain

        pt = PickingType.search(_with_company([
            ('code', '=', 'incoming'),
            ('default_location_dest_id', '=', asset_location.id),
        ]), limit=1)
        if pt:
            return pt

        warehouse = asset_location.warehouse_id
        if warehouse:
            pt = PickingType.search(_with_company([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', warehouse.id),
            ]), limit=1)
            if pt:
                return pt

        if asset_location.parent_path:
            warehouses = self.env['stock.warehouse'].search([])
            warehouses = warehouses.sorted(
                lambda w: len(w.view_location_id.parent_path or ''), reverse=True)
            for wh in warehouses:
                view_path = wh.view_location_id.parent_path or ''
                if view_path and asset_location.parent_path.startswith(view_path):
                    pt = PickingType.search(_with_company([
                        ('code', '=', 'incoming'),
                        ('warehouse_id', '=', wh.id),
                    ]), limit=1)
                    if pt:
                        return pt

        return PickingType

    @api.model_create_multi
    def create(self, vals_list):
        ProcurementPlan = self.env['procurement.plan']
        for vals in vals_list:
            requisition = False
            if vals.get('custom_requisition_id'):
                requisition = self.env['material.purchase.requisition'].browse(vals['custom_requisition_id'])
            elif vals.get('order_line'):
                plan_ids = set()
                for cmd in vals['order_line']:
                    if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and isinstance(cmd[2], dict):
                        for pcmd in cmd[2].get('procurement_plan_ids') or []:
                            if isinstance(pcmd, (list, tuple)):
                                if pcmd[0] in (4,) and pcmd[1]:
                                    plan_ids.add(pcmd[1])
                                elif pcmd[0] == 6 and len(pcmd) >= 3 and pcmd[2]:
                                    plan_ids.update(pcmd[2])
                if plan_ids:
                    plans = ProcurementPlan.browse(list(plan_ids)).exists()
                    reqs = plans.mapped('requisition_id').filtered(lambda r: r.is_asset_purchase)
                    if reqs:
                        requisition = reqs[0]

            if requisition and requisition.is_asset_purchase:
                vals.setdefault('is_asset_purchase', True)
                if requisition.asset_location_id and not vals.get('asset_location_id'):
                    vals['asset_location_id'] = requisition.asset_location_id.id
                if not vals.get('custom_requisition_id'):
                    vals['custom_requisition_id'] = requisition.id

            asset_location_id = vals.get('asset_location_id')
            if vals.get('is_asset_purchase') and asset_location_id:
                company = self.env['res.company'].browse(vals.get('company_id')) if vals.get('company_id') else self.env.company
                picking_type = self._find_asset_picking_type(
                    self.env['stock.location'].browse(asset_location_id), company)
                if picking_type:
                    vals['picking_type_id'] = picking_type.id

        orders = super().create(vals_list)
        orders._notify_asset_procurement_team()
        return orders

    @api.onchange('asset_location_id', 'is_asset_purchase')
    def _onchange_asset_location_set_picking_type(self):
        for order in self:
            if order.is_asset_purchase and order.asset_location_id:
                picking_type = self._find_asset_picking_type(order.asset_location_id, order.company_id)
                if picking_type:
                    order.picking_type_id = picking_type

    def _check_asset_picking_type(self):
        for order in self:
            if not order.is_asset_purchase or not order.asset_location_id:
                continue
            expected = self._find_asset_picking_type(order.asset_location_id, order.company_id)
            if not expected:
                raise UserError(_(
                    "No incoming operation type is configured for the warehouse of asset location '%s'. "
                    "Please configure a receipts operation type for that warehouse before sending "
                    "purchase order %s for approval.",
                    order.asset_location_id.display_name, order.name))
            if order.picking_type_id != expected:
                raise UserError(_(
                    "Purchase order %s is an Asset Purchase for location '%s', but its Deliver To "
                    "operation type ('%s') does not belong to that location's warehouse ('%s'). "
                    "Expected operation type: '%s'.",
                    order.name, order.asset_location_id.display_name,
                    order.picking_type_id.display_name or _('unset'),
                    order.asset_location_id.warehouse_id.display_name,
                    expected.display_name))

    def write(self, vals):
        res = super().write(vals)
        should_sync = ('asset_location_id' in vals or 'is_asset_purchase' in vals) \
            and 'picking_type_id' not in vals
        if should_sync:
            for order in self:
                if order.is_asset_purchase and order.asset_location_id:
                    picking_type = self._find_asset_picking_type(
                        order.asset_location_id, order.company_id)
                    if picking_type and picking_type != order.picking_type_id:
                        super(PurchaseOrder, order).write({'picking_type_id': picking_type.id})
        if vals.get('state') in ('to approve', 'purchase'):
            self.filtered('is_asset_purchase')._check_asset_picking_type()
        return res

    def _notify_asset_procurement_team(self):
        """Send notification to configured procurement users when an asset-purchase PO is created from a requisition."""
        template = self.env.ref(
            'material_purchase_requisitions.email_asset_purchase_po_notification',
            raise_if_not_found=False,
        )
        if not template:
            return
        for order in self:
            if not order.is_asset_purchase or not order.custom_requisition_id:
                continue
            recipients = order.company_id.procurement_notification_user_ids
            emails = [u.email for u in recipients if u.email]
            extra = (order.company_id.procurement_notification_emails or '').strip()
            if extra:
                emails.extend([e.strip() for e in extra.replace(';', ',').split(',') if e.strip()])
            email_to = ', '.join(dict.fromkeys(emails))
            if not email_to:
                continue
            template.with_context(email_to_override=email_to).send_mail(order.id, force_send=False)

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.is_asset_purchase:
            invoice_vals['is_asset_purchase'] = True
            if self.asset_location_id:
                invoice_vals['asset_location_id'] = self.asset_location_id.id
            if self.custom_requisition_id:
                invoice_vals['custom_requisition_id'] = self.custom_requisition_id.id
        return invoice_vals

    def _get_destination_location(self):
        self.ensure_one()
        if self.is_asset_purchase and self.asset_location_id:
            return self.asset_location_id.id
        return super()._get_destination_location()

    def _prepare_picking(self):
        vals = super()._prepare_picking()
        if self.is_asset_purchase and self.asset_location_id:
            vals['location_dest_id'] = self.asset_location_id.id
        return vals


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    custom_requisition_line_id = fields.Many2one('material.purchase.requisition.line', string='Requisitions Line',
                                                 copy=False)

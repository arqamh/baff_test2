from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class InventoryAsOnDateWizard(models.TransientModel):
    _name = 'inventory.as.on.date.wizard'
    _description = 'Inventory As on Date Wizard'

    as_on_date = fields.Date(
        string='As on Date', required=True,
        default=fields.Date.context_today)
    location_ids = fields.Many2many(
        'stock.location', string='Locations',
        domain="[('usage', '=', 'internal')]",
        help='Leave empty to include all internal locations of the current company.')
    product_ids = fields.Many2many(
        'product.product', string='Products',
        help='Leave empty to include all storable products.')
    category_id = fields.Many2one(
        'product.category', string='Product Category',
        help='Filter products by category (combined with the Products filter).')
    include_zero = fields.Boolean(
        string='Include Zero Quantities', default=False,
        help='If unchecked, only rows with non-zero quantity are shown.')
    result_line_ids = fields.One2many(
        'inventory.as.on.date.line', 'wizard_id',
        string='Results', readonly=True)

    @api.constrains('as_on_date')
    def _check_as_on_date(self):
        for rec in self:
            if not rec.as_on_date:
                raise UserError(_('As on Date is required.'))

    def _get_location_ids(self):
        self.ensure_one()
        if self.location_ids:
            return tuple(self.location_ids.ids)
        locations = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', 'in', (self.env.company.id, False)),
        ])
        return tuple(locations.ids) or (0,)

    def _get_product_domain(self):
        domain = [('type', '=', 'product')]
        if self.product_ids:
            domain = [('id', 'in', self.product_ids.ids)]
        if self.category_id:
            domain.append(('categ_id', 'child_of', self.category_id.id))
        return domain

    def _compute_qty_at_date(self, location_ids):
        """Return dict {(product_id, location_id): qty} for done moves up to as_on_date."""
        cutoff = datetime.combine(self.as_on_date, time.max)
        params = [cutoff, list(location_ids), cutoff, list(location_ids)]
        self.env.cr.execute("""
            WITH
            incoming AS (
                SELECT product_id, location_dest_id AS location_id,
                       SUM(product_qty) AS qty
                FROM stock_move
                WHERE state = 'done'
                  AND date <= %s
                  AND location_dest_id = ANY(%s)
                GROUP BY product_id, location_dest_id
            ),
            outgoing AS (
                SELECT product_id, location_id,
                       SUM(product_qty) AS qty
                FROM stock_move
                WHERE state = 'done'
                  AND date <= %s
                  AND location_id = ANY(%s)
                GROUP BY product_id, location_id
            )
            SELECT product_id, location_id,
                   COALESCE(i.qty, 0) - COALESCE(o.qty, 0) AS qty
            FROM (
                SELECT product_id, location_id FROM incoming
                UNION
                SELECT product_id, location_id FROM outgoing
            ) keys
            LEFT JOIN incoming i USING (product_id, location_id)
            LEFT JOIN outgoing o USING (product_id, location_id)
        """, params)
        return {(pid, lid): qty for pid, lid, qty in self.env.cr.fetchall()}

    def action_generate(self):
        self.ensure_one()
        self.result_line_ids.unlink()

        location_ids = self._get_location_ids()
        qty_by_key = self._compute_qty_at_date(location_ids)

        allowed_products = self.env['product.product'].search(self._get_product_domain())
        allowed_product_ids = set(allowed_products.ids)

        locations_by_id = {
            loc.id: loc for loc in
            self.env['stock.location'].browse(list(location_ids)).exists()
        }

        vals_list = []
        for (pid, lid), qty in qty_by_key.items():
            if pid not in allowed_product_ids:
                continue
            if not self.include_zero and not qty:
                continue
            loc = locations_by_id.get(lid)
            vals_list.append({
                'wizard_id': self.id,
                'user_id': self.env.user.id,
                'as_on_date': self.as_on_date,
                'product_id': pid,
                'location_id': lid,
                'company_id': loc.company_id.id if loc else False,
                'quantity': qty,
            })

        if vals_list:
            self.env['inventory.as.on.date.line'].create(vals_list)

        action = self.env['ir.actions.act_window']._for_xml_id(
            'baff_inventory_as_on_date.action_inventory_as_on_date_line')
        action['domain'] = [('wizard_id', '=', self.id)]
        action['context'] = {
            'search_default_group_location': 1,
            'as_on_date_label': fields.Date.to_string(self.as_on_date),
        }
        action['display_name'] = _('Inventory as on %s', self.as_on_date)
        return action

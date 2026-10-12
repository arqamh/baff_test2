# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare, float_round

AGING_COLUMNS = 6


class StockAgingReport(models.AbstractModel):
	_name = 'report.stock_ageing_report_app.report_stockaginginfo'
	_description = 'Stock Aging Report'

	def _get_columns(self, data):
		period_length = data.get('period_length')
		column_data = []
		current_period_lenth = 0
		for i in range(0, AGING_COLUMNS - 1):
			col = str(current_period_lenth) + "-" + str(current_period_lenth + period_length)
			current_period_lenth += period_length
			column_data.append(col)
		col = "> " + str(current_period_lenth)
		column_data.append(col)
		return column_data

	def _get_report_products(self, data):
		"""Selected products; every storable and consumable product of the
		company when none is selected; or the products of the selected categories."""
		company = data.get('company_id')
		if data.get('filter_type') == 'category':
			domain = [('categ_id', 'in', data.get('category_ids').ids)]
		elif data.get('product_ids'):
			return data.get('product_ids')
		else:
			domain = [('detailed_type', 'in', ('product', 'consu'))]
		domain += ['|', ('company_id', '=', False), ('company_id', '=', company.id)]
		return self.env['product.product'].search(domain)

	def _get_product_name(self, product):
		if product.product_template_attribute_value_ids:
			variant = product.product_template_attribute_value_ids._get_combination_name()
			return variant and "%s (%s)" % (product.name, variant) or product.name
		return product.name

	def _get_aging_details(self, data, locations):
		"""Age the stock held in ``locations`` at the report date, first in first out.

		Every done move line entering ``locations`` from outside them is an
		incoming quantity dated by the line; every done line leaving them
		(deliveries, manufacturing consumption, scrap, adjustments, vendor
		returns...) consumes the oldest incoming quantities first. Move lines are
		used, like stock.quant, because a move's own quantity can differ from what
		was actually done. What remains is split into the age columns and valued at
		the unit cost of the incoming move's valuation layers (landed costs
		included), or the product cost when it has none.
		"""
		company = data.get('company_id')
		end_date = fields.Datetime.to_datetime(data.get('date_from'))
		period_length = data.get('period_length') or 1
		products = self._get_report_products(data)
		product_data = []
		if not products or not locations:
			return [{'product_data': product_data}]

		move_lines = self.env['stock.move.line'].search_read([
			('product_id', 'in', products.ids),
			('state', '=', 'done'),
			('company_id', '=', company.id),
			('date', '<=', end_date),
			'|',
			'&', ('location_dest_id', 'in', locations.ids), ('location_id', 'not in', locations.ids),
			'&', ('location_id', 'in', locations.ids), ('location_dest_id', 'not in', locations.ids),
		], ['product_id', 'qty_done', 'product_uom_id', 'date', 'location_dest_id', 'move_id'], order='date, id')
		location_ids = set(locations.ids)
		uoms = self.env['uom.uom'].browse({line['product_uom_id'][0] for line in move_lines})
		uom_by_id = {uom.id: uom for uom in uoms}
		product_by_id = {product.id: product for product in products}
		incoming_by_product = defaultdict(list)
		outgoing_qty_by_product = defaultdict(float)
		for line in move_lines:
			product = product_by_id[line['product_id'][0]]
			line_uom = uom_by_id[line['product_uom_id'][0]]
			qty = line['qty_done'] if line_uom == product.uom_id \
				else line_uom._compute_quantity(line['qty_done'], product.uom_id, rounding_method='HALF-UP')
			if line['location_dest_id'][0] in location_ids:
				incoming_by_product[product.id].append((line, qty))
			else:
				outgoing_qty_by_product[product.id] += qty

		incoming_move_ids = list({line['move_id'][0] for lines in incoming_by_product.values()
								  for line, _qty in lines if line['move_id']})
		unit_cost_by_move = {}
		if incoming_move_ids:
			value_by_move = defaultdict(float)
			qty_by_move = defaultdict(float)
			move_by_layer = {}
			for layer in self.env['stock.valuation.layer'].search_read(
					[('stock_move_id', 'in', incoming_move_ids)], ['stock_move_id', 'value', 'quantity']):
				move_id = layer['stock_move_id'][0]
				move_by_layer[layer['id']] = move_id
				value_by_move[move_id] += layer['value']
				qty_by_move[move_id] += layer['quantity']
			# Landed costs and vendor bill price differences are booked as their
			# own valuation layer, linked to the original layer (not the move)
			# via stock_valuation_layer_id, so fold their value back into the
			# move they correct or they'd silently disappear from the report.
			if move_by_layer:
				for correction in self.env['stock.valuation.layer'].search_read(
						[('stock_valuation_layer_id', 'in', list(move_by_layer.keys())), ('stock_move_id', '=', False)],
						['stock_valuation_layer_id', 'value']):
					parent_id = correction['stock_valuation_layer_id'][0]
					value_by_move[move_by_layer[parent_id]] += correction['value']
			for move_id, qty in qty_by_move.items():
				if qty:
					unit_cost_by_move[move_id] = value_by_move[move_id] / qty

		currency = company.currency_id
		for product in products.filtered(lambda p: p.id in incoming_by_product):
			rounding = product.uom_id.rounding
			quantities = [0.0] * AGING_COLUMNS
			values = [0.0] * AGING_COLUMNS
			outgoing_qty = outgoing_qty_by_product.get(product.id, 0.0)
			for line, line_qty in incoming_by_product[product.id]:
				consumed_qty = min(line_qty, outgoing_qty)
				outgoing_qty -= consumed_qty
				remaining_qty = line_qty - consumed_qty
				if float_compare(remaining_qty, 0.0, precision_rounding=rounding) <= 0:
					continue
				move_id = line['move_id'] and line['move_id'][0]
				unit_cost = unit_cost_by_move.get(move_id, product.standard_price)
				age_days = (end_date - line['date']).days
				column = min(max(age_days, 0) // period_length, AGING_COLUMNS - 1)
				quantities[column] += remaining_qty
				values[column] += remaining_qty * unit_cost
			if float_compare(sum(quantities), 0.0, precision_rounding=rounding) <= 0:
				continue
			value = {
				'product_id': product.id,
				'product_name': self._get_product_name(product) or '',
				'product_code': product.default_code or '',
				'cost_price': product.standard_price or 0.00,
			}
			for column in range(AGING_COLUMNS):
				value['col_%s' % (column + 1)] = float_round(quantities[column], precision_rounding=rounding)
				value['col_cost_%s' % (column + 1)] = currency.round(values[column])
			product_data.append(value)
		return [{'product_data': product_data}]

	# Warehouse

	def _get_warehouse_details(self, data):
		locations = self.env['stock.location'].search([
			('usage', '=', 'internal'), ('company_id', '=', data.get('company_id').id)])
		return self._get_aging_details(data, locations)

	# Location

	def _get_location_details(self, data, location):
		if not location:
			return []
		locations = self.env['stock.location'].search([
			('id', 'child_of', location.id), ('usage', '=', 'internal')])
		return self._get_aging_details(data, locations)

	@api.model
	def _get_report_values(self, docids, data=None):
		company_id = self.env['res.company'].browse(data['form']['company_id'][0])
		period_length = data['form']['period_length']
		start_date = data['form']['end_date']
		filter_type = data['form']['filter_type']
		category_ids = self.env['product.category'].browse(data['form']['product_categ_ids'])
		product_ids = self.env['product.product'].browse(data['form']['product_ids'])
		location_ids = self.env['stock.location'].browse(data['form']['location_ids'])
		warehouse_ids = self.env['stock.warehouse'].browse(data['form']['warehouse_ids'])
		date_from = data['form']['end_date']
		data = {
			'filter_type': filter_type,
			'report_type': data['form']['report_type'],
			'start_date': start_date,
			'date_from': date_from,
			'warehouse_ids': warehouse_ids,
			'location_ids': location_ids,
			'product_ids': product_ids,
			'category_ids': category_ids,
			'period_length': period_length,
			'company_id': company_id
		}
		docargs = {
			'doc_model': 'stock.aging.report.wizard',
			'data': data,
			'get_columns': self._get_columns,
			'get_warehouse_details': self._get_warehouse_details,
			'get_location_details': self._get_location_details,
		}
		return docargs

# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.tools import pycompat, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.float_utils import float_round

import logging
_logger = logging.getLogger(__name__)

try:
	import xlsxwriter
except ImportError:
	_logger.debug('Cannot `import xlsxwriter`.')
try:
	import base64
except ImportError:
	_logger.debug('Cannot `import base64`.')


class StockAgingReportWizard(models.TransientModel):
	_name = 'stock.aging.report.wizard'
	_description = 'Stock Aging Report'

	end_date = fields.Datetime('End Date', required=True, default=fields.Datetime.now)
	warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouse")
	location_ids = fields.Many2many('stock.location', string="Location")
	product_ids = fields.Many2many('product.product', string="Product")
	product_categ_ids = fields.Many2many('product.category', string="Category")
	filter_type = fields.Selection([('product', 'Product'), ('category', 'Category')], default='product', string='Filter By')
	document = fields.Binary('File To Download')
	file = fields.Char('Report File Name', readonly=1)
	period_length = fields.Integer('Period Length (Days)', default=30)
	company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
	report_type = fields.Selection([('warehouse', 'Warehouse'), ('location', 'Location')], default='warehouse', string='Generate Report Based on')

	@api.onchange('filter_type')
	def _onchange_filter_type(self):
		if self.filter_type == 'product':
			self.product_categ_ids = False
		else:
			self.product_ids = False

	@api.onchange('report_type')
	def _onchange_report_type(self):
		if self.report_type == 'warehouse':
			self.location_ids = False
		else:
			self.warehouse_ids = False

	def print_pdf_report(self):
		self.ensure_one()
		[data] = self.read()
		datas = {
			'ids': [1],
			'model': 'stock.aging.report.wizard',
			'form': data
		}
		return self.env.ref('stock_ageing_report_app.action_report_stock_aging').report_action(self, data=datas)

	def get_columns(self, data):
		period_length = data.get('period_length')
		column_data = []
		current_period_lenth = 0
		for i in range(0, 5):
			col = str(current_period_lenth) + "-" + str(current_period_lenth + period_length)
			current_period_lenth += period_length
			column_data.append(col)
		col = "> " + str(current_period_lenth)
		column_data.append(col)
		return column_data

	def _get_report_data(self, data):
		"""Excel uses the PDF report's computation, so both always agree."""
		return dict(data, date_from=self.end_date, product_ids=self.product_ids,
					category_ids=self.product_categ_ids, company_id=self.company_id)

	def get_warehouse_details(self, data):
		report = self.env['report.stock_ageing_report_app.report_stockaginginfo']
		return report._get_warehouse_details(self._get_report_data(data))

	def get_location_details(self, data, location):
		report = self.env['report.stock_ageing_report_app.report_stockaginginfo']
		return report._get_location_details(self._get_report_data(data), location)

	def print_excel_report(self):
		self.ensure_one()
		[data] = self.read()
		file_path = 'Stock Aging Report' + '.xlsx'
		workbook = xlsxwriter.Workbook(file_path)
		worksheet = workbook.add_worksheet('Stock Aging Report')

		header_format = workbook.add_format({'bold': True, 'valign': 'vcenter', 'font_size': 16, 'align': 'center', 'bg_color': '#D8D8D8'})
		title_format = workbook.add_format({'border': 1, 'bold': True, 'valign': 'vcenter', 'align': 'center', 'font_size': 14, 'bg_color': '#D8D8D8'})
		cell_wrap_format = workbook.add_format({'border': 1, 'valign': 'vjustify', 'valign': 'vcenter', 'align': 'left', 'font_size': 12}) ##E6E6E6
		cell_wrap_format_right = workbook.add_format({'border': 1, 'valign': 'vjustify', 'valign': 'vcenter', 'align': 'right', 'font_size': 12, 'num_format': '#,##0.00'}) ##E6E6E6
		cell_wrap_format_val = workbook.add_format({'border': 1, 'valign': 'vjustify', 'valign': 'vcenter', 'align': 'right', 'font_size': 12, 'num_format': '#,##0.00'}) ##E6E6E6
		cell_wrap_format_val.set_font_color('#006600')
		cell_wrap_format_bold = workbook.add_format({'border': 1, 'bold': True, 'valign': 'vjustify', 'valign': 'vcenter', 'align': 'center', 'font_size': 12, 'bg_color': '#D8D8D8'}) ##E6E6E6
		cell_wrap_format_amount = workbook.add_format({'border': 1, 'valign': 'vjustify', 'valign': 'vcenter', 'align': 'right', 'font_size': 12, 'bold': True, 'num_format': '#,##0.00'}) ##E6E6E6
		cell_wrap_format_amount_val = workbook.add_format({'border': 1, 'valign': 'vjustify', 'valign': 'vcenter', 'align': 'right', 'font_size': 12, 'bold': True, 'num_format': '#,##0.00'}) ##E6E6E6
		cell_wrap_format_amount.set_font_color('#006600')

		worksheet.set_row(1, 20)  #Set row height
		#Merge Row Columns
		TITLEHEDER = 'Stock Aging Report'
		worksheet.set_column(0, 15, 20)

		data = {
			'filter_type': self.filter_type,
			'end_date': self.end_date,
			'warehouse_ids': self.warehouse_ids,
			'location_ids': self.location_ids,
			'product_ids': self.product_ids,
			'category_ids': self.product_categ_ids,
			'period_length': self.period_length,
			'company_id': self.company_id
		}

		worksheet.merge_range(1, 0, 1, 15, TITLEHEDER, header_format)
		rowscol = 1
		if self.report_type == "warehouse":
			# for warehouse in self.warehouse_ids:
				# Report Title
			worksheet.merge_range((rowscol + 2), 0, (rowscol + 2), 3, 'Warehouse/Location', title_format)
			worksheet.merge_range((rowscol + 2), 12, (rowscol + 2), 15, " ", title_format)

			worksheet.merge_range((rowscol + 4), 0, (rowscol + 4), 3, 'Company: ', title_format)
			worksheet.merge_range((rowscol + 5), 0, (rowscol + 5), 3, str(self.company_id.name), title_format)

			worksheet.merge_range((rowscol + 4), 6, (rowscol + 4), 9, 'As At: ', title_format)
			worksheet.merge_range((rowscol + 5), 6, (rowscol + 5), 9, str(self.end_date), title_format)

			worksheet.merge_range((rowscol + 4), 12, (rowscol + 4), 15, 'Period Length:', title_format)
			worksheet.merge_range((rowscol + 5), 12, (rowscol + 5), 15, str(self.period_length), title_format)

			# Report Content
			worksheet.write((rowscol + 7), 0, 'Code', cell_wrap_format_bold)
			worksheet.write((rowscol + 7), 1, 'Product Name', cell_wrap_format_bold)
			worksheet.write((rowscol + 7), 2, 'Total Qty', cell_wrap_format_bold)
			worksheet.write((rowscol + 7), 3, 'Total Value', cell_wrap_format_bold)
			col = 4
			for value in self.get_columns(data):
				colss = col + 1
				worksheet.merge_range((rowscol + 7), col, (rowscol + 7), colss, str(value), title_format)
				col += 2
			worksheet.write((rowscol + 8), 0, '', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 1, '', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 2, '', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 3, '', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 4, 'Qty', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 5, 'Value', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 6, 'Qty', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 7, 'Value', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 8, 'Qty', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 9, 'Value', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 10, 'Qty', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 11, 'Value', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 12, 'Qty', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 13, 'Value', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 14, 'Qty', cell_wrap_format_bold)
			worksheet.write((rowscol + 8), 15, 'Value', cell_wrap_format_bold)
			rows = (rowscol + 9)
			for records in self.get_warehouse_details(data):
				for record in records.get('product_data'):
					col_1_data = record.get('col_1')
					col_1_data_value = record.get('col_cost_1')
					col_2_data = record.get('col_2')
					col_2_data_value = record.get('col_cost_2')
					col_3_data = record.get('col_3')
					col_3_data_value = record.get('col_cost_3')
					col_4_data = record.get('col_4')
					col_4_data_value = record.get('col_cost_4')
					col_5_data = record.get('col_5')
					col_5_data_value = record.get('col_cost_5')
					col_6_data = record.get('col_6')
					col_6_data_value = record.get('col_cost_6')

					sub_total = col_1_data + col_2_data + col_3_data + col_4_data + col_5_data + col_6_data

					total_cost = col_1_data_value + col_2_data_value + col_3_data_value + col_4_data_value + col_5_data_value + col_6_data_value

					worksheet.write(rows, 0,  record.get('product_code'), cell_wrap_format)
					worksheet.write(rows, 1,  record.get('product_name'), cell_wrap_format)

					worksheet.write(rows, 2,  sub_total, cell_wrap_format_val)
					worksheet.write(rows, 3,  total_cost, cell_wrap_format_right)

					worksheet.write(rows, 4,  col_1_data, cell_wrap_format_amount)
					worksheet.write(rows, 5,  col_1_data_value, cell_wrap_format_amount_val)
					worksheet.write(rows, 6,  col_2_data, cell_wrap_format_amount)
					worksheet.write(rows, 7,  col_2_data_value, cell_wrap_format_amount_val)
					worksheet.write(rows, 8,  col_3_data, cell_wrap_format_amount)
					worksheet.write(rows, 9,  col_3_data_value, cell_wrap_format_amount_val)
					worksheet.write(rows, 10, col_4_data, cell_wrap_format_amount)
					worksheet.write(rows, 11, col_4_data_value, cell_wrap_format_amount_val)
					worksheet.write(rows, 12, col_5_data, cell_wrap_format_amount)
					worksheet.write(rows, 13, col_5_data_value, cell_wrap_format_amount_val)
					worksheet.write(rows, 14, col_6_data, cell_wrap_format_amount)
					worksheet.write(rows, 15, col_6_data_value, cell_wrap_format_amount_val)
					rows = rows + 1
				rows = rows
				rowscol = rows + 2
		else:
			for location in self.location_ids:
				if location.location_id:
					location_name = str(location.location_id.name or '') + '/' + str(location.name or '')
				else:
					location_name = str(location.name or '')
				# Report Title
				worksheet.merge_range((rowscol + 2), 0, (rowscol + 2), 3, 'Warehouse/Location', title_format)
				worksheet.merge_range((rowscol + 2), 12, (rowscol + 2), 15, str(location_name), title_format)

				worksheet.merge_range((rowscol + 4), 0, (rowscol + 4), 3, 'Company: ', title_format)
				worksheet.merge_range((rowscol + 5), 0, (rowscol + 5), 3, str(self.company_id.name), title_format)

				worksheet.merge_range((rowscol + 4), 6, (rowscol + 4), 9, 'As At', title_format)
				worksheet.merge_range((rowscol + 5), 6, (rowscol + 5), 9, str(self.end_date), title_format)

				worksheet.merge_range((rowscol + 4), 12, (rowscol + 4), 15, 'Period Length:', title_format)
				worksheet.merge_range((rowscol + 5), 12, (rowscol + 5), 15, str(self.period_length), title_format)

				# Report Content
				worksheet.write((rowscol + 7), 0, 'Code', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 1, 'Product Name', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 2, 'Total Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 7), 3, 'Total Value', cell_wrap_format_bold)
				col = 4
				for value in self.get_columns(data):
					colss = col + 1
					worksheet.merge_range((rowscol + 7), col, (rowscol + 7), colss, str(value), title_format)
					col += 2
				worksheet.write((rowscol + 8), 0, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 1, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 2, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 3, '', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 4, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 5, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 6, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 7, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 8, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 9, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 10, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 11, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 12, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 13, 'Value', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 14, 'Qty', cell_wrap_format_bold)
				worksheet.write((rowscol + 8), 15, 'Value', cell_wrap_format_bold)
				rows = (rowscol + 9)
				for records in self.get_location_details(data, location):
					for record in records.get('product_data'):
						col_1_data = record.get('col_1')
						col_1_data_value = record.get('col_cost_1')
						col_2_data = record.get('col_2')
						col_2_data_value = record.get('col_cost_2')
						col_3_data = record.get('col_3')
						col_3_data_value = record.get('col_cost_3')
						col_4_data = record.get('col_4')
						col_4_data_value = record.get('col_cost_4')
						col_5_data = record.get('col_5')
						col_5_data_value = record.get('col_cost_5')
						col_6_data = record.get('col_6')
						col_6_data_value = record.get('col_cost_6')

						sub_total = col_1_data + col_2_data + col_3_data + col_4_data + col_5_data + col_6_data

						total_cost = col_1_data_value + col_2_data_value + col_3_data_value + col_4_data_value + col_5_data_value + col_6_data_value

						worksheet.write(rows, 0,  record.get('product_code'), cell_wrap_format)
						worksheet.write(rows, 1,  record.get('product_name'), cell_wrap_format)

						worksheet.write(rows, 2,  sub_total, cell_wrap_format_val)
						worksheet.write(rows, 3,  total_cost, cell_wrap_format_right)

						worksheet.write(rows, 4,  col_1_data, cell_wrap_format_amount)
						worksheet.write(rows, 5,  col_1_data_value, cell_wrap_format_amount_val)
						worksheet.write(rows, 6,  col_2_data, cell_wrap_format_amount)
						worksheet.write(rows, 7,  col_2_data_value, cell_wrap_format_amount_val)
						worksheet.write(rows, 8,  col_3_data, cell_wrap_format_amount)
						worksheet.write(rows, 9,  col_3_data_value, cell_wrap_format_amount_val)
						worksheet.write(rows, 10, col_4_data, cell_wrap_format_amount)
						worksheet.write(rows, 11, col_4_data_value, cell_wrap_format_amount_val)
						worksheet.write(rows, 12, col_5_data, cell_wrap_format_amount)
						worksheet.write(rows, 13, col_5_data_value, cell_wrap_format_amount_val)
						worksheet.write(rows, 14, col_6_data, cell_wrap_format_amount)
						worksheet.write(rows, 15, col_6_data_value, cell_wrap_format_amount_val)
						rows = rows + 1
					rows = rows
				rowscol = rows + 2
		workbook.close()
		document = open(file_path, 'rb+').read()
		values = {
			'name': 'Stock Aging Report'+'.xlsx',
			'res_model': 'ir.ui.view',
			'res_id': False,
			'type': 'binary',
			'public': True,
			'datas': base64.b64encode(document),
		}
		attachment_id = self.env['ir.attachment'].sudo().create(values)
		download_url = '/web/content/' + str(attachment_id.id) + '?download=True'
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
		return {
			"type": "ir.actions.act_url",
			"url": str(base_url) + str(download_url),
			"target": "new",
		}
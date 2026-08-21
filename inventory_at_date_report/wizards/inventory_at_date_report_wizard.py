from odoo import fields, models, api
import base64
import xlsxwriter
from datetime import datetime


class InventoryAtDateReportWizard(models.Model):
    _name = 'inventory.at.date.report.wizard'
    _description = 'Inventory At Date Report'

    def _get_financial_year_start_date(self):
        company = self.env.company
        today = fields.Date.today()
        fiscalyear_dates = company.compute_fiscalyear_dates(today)
        return fields.Datetime.to_datetime(fiscalyear_dates['date_from'])

    initial_lock_datetime = fields.Datetime(string="Initial Lock Datetime", readonly=True,
                                            default=_get_financial_year_start_date)

    inventory_datetime = fields.Datetime(string="Inventory at Date", required=True, default=fields.Datetime.now)
    location_id = fields.Many2one('stock.location', string="Location")

    def download_report(self):
        """Inventory At Date report"""
        file = self.generate_inventory_at_date_report()

        report_data = open(file, 'rb+')
        read_file = report_data.read()
        values = {
            'name': 'Inventory At Date' + '.xlsx',
            'res_model': 'ir.ui.view',
            'res_id': False,
            'type': 'binary',
            'public': True,
            'datas': base64.b64encode(read_file),
        }
        attachment_id = self.env['ir.attachment'].sudo().create(values)
        download_url = '/web/content/' + str(attachment_id.id) + '?download=True'
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }

    def generate_inventory_at_date_report(self):
        """Generating collection report"""
        # "Setting name for the report"
        report = 'Inventory At Date Report' + '.xlsx'
        workbook = xlsxwriter.Workbook(report)

        # Create worksheet 1
        worksheet = workbook.add_worksheet('Inventory At Date Report')
        worksheet.set_landscape()

        heading = workbook.add_format({'bold': True, 'align': 'left', 'font_size': '14'})
        heading_2 = workbook.add_format({'bold': True, 'align': 'left', 'font_size': '12'})
        font_right = workbook.add_format(
            {'align': 'right', 'valign': 'vcenter', 'font_size': 10, 'num_format': '#,##0.00', 'border': 1})
        font_left = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'font_size': 10, 'border': 1})
        font_center = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'border': 1})
        font_center_bold = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'bold': True, 'border': 1})

        worksheet.set_column('A:S', 16)
        worksheet.set_row(0, 20)

        row = 0
        col = 0

        # Write data on the worksheet
        worksheet.write(row, col, self.env.company.name, heading)
        # worksheet.write(row + 1, col, "Inventory At %s" % (str(self.inventory_datetime)))
        if self.location_id:
            worksheet.write(row + 1, col, "Stock At %s - In %s" % (str(self.inventory_datetime), self.location_id.name))
        else:
            worksheet.write(row + 1, col, "Stock At %s - %s" % (str(self.inventory_datetime), "In All Locations"))

        col = 0
        row = 3

        # setting headings
        worksheet.write(row, col, "Category", font_center_bold)
        worksheet.write(row, col + 1, "Sub Category", font_center_bold)
        worksheet.write(row, col + 2, "Internal Reference No", font_center_bold)
        worksheet.write(row, col + 3, "Product Name", font_center_bold)
        worksheet.write(row, col + 4, "Quantity", font_center_bold)
        worksheet.write(row, col + 5, "UOM", font_center_bold)
        worksheet.write(row, col + 6, "Product Value", font_center_bold)
        worksheet.write(row, col + 7, "Total Value", font_center_bold)

        row += 1

        # printing report data
        all_quants = self.env['product.product'].search([('active', '=', True), ('type', 'in', ['product', 'product'])])
        # records = self.get_report_data(all_quants.mapped("lot_id"), self.inventory_datetime)
        records = self.get_report_data(all_quants, self.inventory_datetime)
        for record in records:
            worksheet.write(row, col, record['parent_category'], font_left)
            worksheet.write(row, col + 1, record.get('sub_category'), font_left)
            worksheet.write(row, col + 2, record.get('default_code'), font_left)
            worksheet.write(row, col + 3, record.get('product_name'), font_left)
            worksheet.write(row, col + 4, record.get('quantity_available'), font_right)
            worksheet.write(row, col + 5, record.get('uom_id'), font_right)
            worksheet.write(row, col + 6, record.get('standard_price'), font_right)
            worksheet.write(row, col + 7, record.get('total_valuation'), font_right)
            row += 1
        workbook.close()
        return report

    def get_report_data(self, product_ids, date):
        """this function returns the dataset based on the calculation by subtracting out moves from in moves"""
        locations = self.get_locations()
        # cutoff_date = date
        # cutoff_datetime = datetime.strptime(cutoff_date, "%Y-%m-%d %H:%M:%S")
        current_date = datetime.now()
        values = []
        for product in product_ids:
            # setting domain for in and out moves

            in_move_domain = [('product_id', '=', product.id), ('date', '<=', date), ('date', '>=', self.initial_lock_datetime),
                              ('location_dest_id', 'in', locations.ids), ('state', '=', 'done')]
            out_move_domain = [('product_id', '=', product.id), ('date', '<=', date), ('date', '>=', self.initial_lock_datetime),
                               ('location_id', 'in', locations.ids), ('state', '=', 'done')]

            valuations = self.env['stock.valuation.layer'].search(
                [('product_id', '=', product.id), ('create_date', '<=', date),
                 ('create_date', '>=', self.initial_lock_datetime)])
            hardcoded_valuation_layers = self.env['stock.valuation.layer'].search(
                [('product_id', '=', product.id),
                 ('stock_move_id.picking_id.name', 'in', ['WH/IN/00787','WH/IN/00782','WH/IN/00781','WH/IN/00780'])])
            valuations |= hardcoded_valuation_layers
            in_moves = self.env['stock.move.line'].search(in_move_domain, order='id desc')
            out_moves = self.env['stock.move.line'].search(out_move_domain, order='id desc')

            if in_moves or out_moves or valuations:
                total_quantity_available = sum(valuations.mapped('quantity'))
                valuation_cost = sum(valuations.mapped('value'))
                valuation_per_quantity = valuation_cost / total_quantity_available if total_quantity_available != 0 else 1

                in_quantity = sum(in_moves.mapped('qty_done')) if sum(in_moves.mapped('qty_done')) != 0 else 0
                out_quantity = sum(out_moves.mapped('qty_done')) if sum(out_moves.mapped('qty_done')) != 0 else 0
                quantity_available = in_quantity - out_quantity

                stock_picking_ids = self.env['stock.picking'].search([('name', 'in', ['WH/IN/00787','WH/IN/00782','WH/IN/00781','WH/IN/00780']),('location_dest_id', 'in', locations.ids),('state', '=', 'done')])
                stock_move_ids = self.env['stock.move'].search([('picking_id', 'in', stock_picking_ids.ids),('product_id', '=', product.id),('state', '=', 'done')])
                updated_valuation_quantity = sum(stock_move_ids.mapped('stock_valuation_layer_ids').mapped('quantity'))

                quantity_available += updated_valuation_quantity

                # returning the dataset of each product
                if quantity_available != 0:
                    values.append({
                        "parent_category": product.categ_id.parent_id.name or " ",
                        "sub_category": product.categ_id.name,
                        "default_code": product.default_code,
                        "product_name": product.display_name,
                        "quantity_available": quantity_available,
                        "uom_id": product.uom_id.name,
                        "standard_price": valuation_per_quantity,
                        "total_valuation": valuation_per_quantity * quantity_available,
                    })
        return values

    def get_locations(self):
        """This function returns all internal locations if no location is selected,
        or only the selected locations (and their children) if a location is chosen."""
        internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        if self.location_id:
            internal_locations = self.env['stock.location'].search(['|', ('id', 'in', self.location_id.ids), ('id', 'child_of', self.location_id.ids), ('usage', '=', 'internal')])
            return internal_locations
        return internal_locations

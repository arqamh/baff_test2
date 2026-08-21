from odoo import models, fields, api, _
from datetime import datetime


class ShipmentsDetails(models.Model):
    _name = 'shipments.details'
    _description = 'Shipments Details'
    _rec_name = 'number'

    number = fields.Char(string='Serial Number', index=True, readonly=False, default="New")
    shipments_lines = fields.One2many('shipments.details.lines', 'shipments_details_id', string='Shipments Details Lines')
    project = fields.Char(string="Project")
    shipment_number = fields.Char(string="Shipment Number")
    tt_number = fields.Char(string="TT Number")
    description = fields.Char(string="Description")
    amount = fields.Float(string="Amount")
    payment_date = fields.Date(string="Payment Date")
    boi_approval = fields.Char(string="Boi Approval")
    shipper_supplier = fields.Char(string="Shipper/Supplier")
    country = fields.Many2one('res.country', string="Country")
    mode_of_transport = fields.Selection([('air', 'Air'), ('sea', 'Sea')], string="Mod of Transport")
    incoterm = fields.Char(string="Incoterm")

    etd = fields.Char(string="ETD String")
    revised_etd = fields.Char(string="Revised ETD String")
    eta = fields.Char(string="ETA String")

    etd_date = fields.Date(string="ETD")
    revised_etd_date = fields.Date(string="Revised ETD")
    eta_date = fields.Date(string="ETA")

    pick_up_local_agent = fields.Char(string="Pick Up/Local Agent")
    freight_cost = fields.Float(string="Freight Cost")
    finalized_date = fields.Date(string="Finalized Date")
    port_airport = fields.Char(string="Port/Airport")
    vessel_flight = fields.Char(string="Vessel/Flight")
    clearance_agent = fields.Char(string="Clearance Agent")
    date = fields.Date(string="Date")
    cus_dec_no = fields.Char(string="Cus Dec No")
    koggala_delivery_date = fields.Date(string="Koggala Delivery Date")
    type_of_vehicle = fields.Char(string="Type Of Vehicle")
    package_size = fields.Float(string="Package Size")
    remarks_notes = fields.Char(string="Remarks/Notes")
    freight_invoice_no = fields.Char(string="Freight Invoice No")
    clearance_invoice_no = fields.Char(string="Clearance Invoice No")
    state = fields.Selection([('draft', 'Draft'), ('arrived', 'Arrived'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='draft')


    def pending_approve(self):
        """Approving shipment"""
        self.write({"state": "arrived"})


    def confirm_shipment(self):
        """Confirm shipment"""
        self.write({"state": "completed"})


    def cancel_shipment(self):
        """Cancel shipment"""
        self.write({"state": "cancelled"})


    @api.model
    def create(self, vals):
        """Override the create method and generate a sequence when record is create"""
        if vals.get('number', 'New') == 'New':
            vals['number'] = self.env['ir.sequence'].next_by_code('shipments.details.sequence') or 'New'
        return_obj = super(ShipmentsDetails, self).create(vals)
        return return_obj


    def convert_etd_str_to_date(self):
        records = self.env['shipments.details'].search([('etd', '!=', False),('etd_date', '=', False)])
        for rec in records:
            parsed_date = datetime.strptime(rec.etd.strip(), '%d/%m/%Y').date()
            rec.write({'etd_date': parsed_date})


    def convert_revised_etd_str_to_date(self):
        records = self.env['shipments.details'].search([('revised_etd', '!=', False),('revised_etd_date', '=', False)])
        for rec in records:
            parsed_date = datetime.strptime(rec.revised_etd.strip(), '%d/%m/%Y').date()
            rec.write({'revised_etd_date': parsed_date})


    def convert_eta_str_to_date(self):
        records = self.env['shipments.details'].search([('eta', '!=', False),('eta_date', '=', False)])
        for rec in records:
            parsed_date = datetime.strptime(rec.eta.strip(), '%d/%m/%Y').date()
            rec.write({'eta_date': parsed_date})


class ShipmentsDetailsLines(models.Model):
    _name = 'shipments.details.lines'

    shipments_details_id = fields.Many2one('shipments.details')
    po_number = fields.Many2one('purchase.order', string="PO Number")
    date = fields.Date(string="Date")
    proforma_invoice_no = fields.Char(string="Proforma Invoice No.")
    proforma_invoice_date = fields.Char(string="Proforma Invoice Date")
    currency = fields.Many2one('res.currency', related='po_number.currency_id' , string="Currency")
    amount = fields.Float(string='Amount')
    payment_date = fields.Date(string="Date")


    @api.onchange('po_number')
    def onchange_po_number(self):
        """Onchange po number, amount"""
        self.amount = self.po_number.amount_total
        self.date = self.po_number.create_date

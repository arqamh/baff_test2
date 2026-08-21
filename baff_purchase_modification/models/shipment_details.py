from odoo import models, fields, api

class PurchaseShipmentDetails(models.Model):
    _name ='purchase.shipment.details'
    _description ='Purchase Shipment details'

    purchase_id = fields.Many2one('purchase.order', string="Purchase Order")
    date = fields.Date()
    project = fields.Char()
    partner_id = fields.Many2one('res.partner', string="Shipper/Supplier")
    proforma_invoice_no = fields.Char()
    proforma_invoice_date = fields.Date()
    description = fields.Char()
    amount = fields.Float()
    tt_number = fields.Char(string="TT Number")
    payment_date = fields.Date()
    boi_approval = fields.Char()
    mode_of_transport = fields.Char()
    incoterm = fields.Char()
    etd = fields.Char(string="ETD")
    revised_etd= fields.Char(string="Revised ETD")
    eta= fields.Char(string="ETA")
    local_agent= fields.Char(string="Pick Up/Local Agent")
    freight_cost= fields.Float(string="Freight Cost")
    finalized_date= fields.Date(string="Finalized Date")
    airport= fields.Char(string="Port/Airport")
    flight= fields.Char(string="Vessel/Flight")
    clearance_agent = fields.Char(string="Vessel/Flight")
    cus_dec_no = fields.Char(string="Cus Dec No")
    koggala_delivery_date = fields.Date(string="Koggala Delivery Date ")
    type_of_vehicle = fields.Char(string="Type of Vehicle ")
    package_size = fields.Char(string="Package SIze ")
    remarks = fields.Char(string="Remarks ")
    clearance_invoice_no = fields.Char(string="Clearance Invoice No ")
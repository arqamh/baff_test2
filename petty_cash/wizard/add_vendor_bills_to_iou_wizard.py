from odoo import fields, models, api
from datetime import datetime
from datetime import timedelta


class AddVendorBillToIOU(models.TransientModel):
    _name = 'vendorbill.iourequest'
    _description = 'Vendor Bill to IOU Request'

    iou_request = fields.Many2one('petty.cash.release', string="IOU Request")
    partner_id = fields.Many2one('res.partner', string="Vendor", required=True)

    vendor_bill_ids = fields.Many2many('vendorbill.iourequest.line', string="Vendor Bills")

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """ Get unpaid vendor bills when change the partner id"""
        if self.partner_id:
            vendor_bils = self.env['account.move'].search([('partner_id', '=', self.partner_id.id), ('move_type', '=', 'in_invoice'), ('amount_residual', '>', 0.00), ('state', '=', 'posted')])
            if vendor_bils:
                self.vendor_bill_ids = False
                bill_value = []
                for rec in vendor_bils:
                    vals = (0, 0, {
                        'iou_request_id': self.iou_request.id,
                        'partner_id': rec.partner_id.id,
                        'vendor_bill_id': rec.id,
                        'amount_total': abs(rec.amount_total_signed),
                        'amount_residual': abs(rec.amount_residual_signed),
                        'paid_amount': abs(rec.amount_residual_signed),
                    })
                    bill_value.append(vals)

                self.vendor_bill_ids = bill_value
            else:
                self.vendor_bill_ids = False

    def approval_submission(self):
        """Update vendor bill lines with petty cash"""
        if self.vendor_bill_ids:
            bill_list = []
            for rec in self.vendor_bill_ids:
                vals = (0, 0, {
                    'partner_id': rec.partner_id.id,
                    'vendor_bill_id': rec.vendor_bill_id.id,
                    'amount_total': rec.amount_total,
                    'amount_residual': rec.amount_residual,
                    'paid_amount': rec.paid_amount,
                })
                bill_list.append(vals)
            self.iou_request.write({
                'vendor_bills': bill_list
            })


class AddVendorBillToIOULine(models.TransientModel):
    _name = 'vendorbill.iourequest.line'
    _description = 'Vendor Bill to IOU Request Lines'

    iou_request_id = fields.Many2one('petty.cash.release', string="IOU Request")
    partner_id = fields.Many2one('res.partner', string='Vendor', )
    vendor_bill_id = fields.Many2one('account.move', string="Vendor Bill")
    amount_total = fields.Float(string='Total', store=True,)
    amount_residual = fields.Float(string='Due Amount', store=True, )
    paid_amount = fields.Float(string='Paid Amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='iou_request_id.currency_id')

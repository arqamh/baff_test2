from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    margin = fields.Monetary(
        string="Margin",
        compute="_compute_margin",
        store=True,
        currency_field="currency_id",
    )

    margin_signed = fields.Monetary(
        string="Margin Signed",
        compute="_compute_margin",
        store=True,
        currency_field="currency_id",
    )

    margin_percent = fields.Float(
        string="Margin (%)",
        digits="Product Price",
        compute="_compute_margin",
        store=True,
    )

    gp_approved_by = fields.Many2one('res.users', string="GP Approved By", readonly=1)
    credit_approved_by = fields.Many2one('res.users', string="Credit Limit Approved By", readonly=1)
    pt_approved_by = fields.Many2one('res.users', string="Payment Term Approved By", readonly=1)

    def _get_margin_applicable_lines(self):
        """return invoice lines"""
        self.ensure_one()
        return self.invoice_line_ids

    @api.depends(
        "invoice_line_ids.margin",
        "invoice_line_ids.margin_signed",
        "invoice_line_ids.price_subtotal",
    )
    def _compute_margin(self):
        """compute margin of the invoice"""
        for invoice in self:
            margin = 0.0
            margin_signed = 0.0
            price_subtotal = 0.0
            for line in invoice._get_margin_applicable_lines():
                margin += line.margin
                margin_signed += line.margin_signed
                price_subtotal += line.price_subtotal
            invoice.margin = margin
            invoice.margin_signed = margin_signed
            invoice.margin_percent = (
                price_subtotal and margin_signed / price_subtotal * 100 or 0.0
            )

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        if any('state' in vals and vals.get('state') == 'posted' for vals in vals_list):
            raise UserError(_('You cannot create a move already in the posted state. Please create a draft move and post it after.'))

        # vals_list = self._move_autocomplete_invoice_lines_create(vals_list)
        # # get approver and update invoice
        # if vals_list:
        #     invoice_origin = vals_list[0].get('invoice_origin')
        #     if invoice_origin:
        #         sales_obj = self.env['sale.order'].search([('name', '=', invoice_origin)])
        #         if sales_obj:
        #             vals_list[0].update({'gp_approved_by': sales_obj.gp_approved_by.id,
        #                                  'credit_approved_by': sales_obj.credit_approved_by.id,
        #                                  'pt_approved_by': sales_obj.pt_approved_by.id})
        rslt = super(AccountMove, self).create(vals_list)
        # for i, vals in enumerate(vals_list):
        #     if 'line_ids' in vals:
        #         rslt[i].update_lines_tax_exigibility()
        return rslt


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    margin = fields.Float(
        compute="_compute_margin", digits="Product Price", store=True, string="Margin"
    )
    margin_signed = fields.Float(
        compute="_compute_margin",
        digits="Product Price",
        store=True,
        string="Margin Signed",
    )
    margin_percent = fields.Float(
        string="Margin (%)", compute="_compute_margin", store=True, readonly=True
    )
    purchase_price = fields.Float(
        string="Cost",
        compute="_compute_purchase_price",
        store=True,
        readonly=False,
        digits="Product Price",
    )

    @api.depends("purchase_price", "price_subtotal")
    def _compute_margin(self):
        """get purchase margin amount"""
        for line in self:
            if line.move_id and line.move_id.move_type[:2] == "in":
                line.update(
                    {"margin": 0.0, "margin_signed": 0.0, "margin_percent": 0.0}
                )
                continue
            tmp_margin = line.price_subtotal - (line.purchase_price * line.quantity)
            sign = line.move_id.move_type in ["in_refund", "out_refund"] and -1 or 1
            line.update(
                {
                    "margin": tmp_margin,
                    "margin_signed": tmp_margin * sign,
                    "margin_percent": (
                        tmp_margin / line.price_subtotal * 100.0
                        if line.price_subtotal
                        else 0.0
                    ),
                }
            )

    def _get_purchase_price(self):
        # Overwrite this function if you don't want to base your
        # purchase price on the product standard_price
        self.ensure_one()
        return self.product_id.standard_price

    @api.depends("product_id", "product_uom_id")
    def _compute_purchase_price(self):
        """compute purchase price"""
        for line in self:
            if line.move_id.move_type in ["out_invoice", "out_refund"]:
                purchase_price = line._get_purchase_price()
                if line.product_uom_id != line.product_id.uom_id and line.product_id:
                    purchase_price = line.product_id.uom_id._compute_price(
                        purchase_price, line.product_uom_id
                    )
                line.purchase_price = purchase_price
            else:
                line.purchase_price = 0.0

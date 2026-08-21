# -*- Coding: utf-8 -*-

from odoo import fields, models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoiceable_line_ids = fields.One2many('invoiceable.lines', 'invoice_move_id', string='Invoice')
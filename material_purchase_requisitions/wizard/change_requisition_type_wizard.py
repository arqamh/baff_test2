# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ChangeRequisitionTypeWizard(models.TransientModel):
    _name = 'change.requisition.type.wizard'
    _description = 'Change Requisition Type Wizard'

    # Main fields
    requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Requisition',
        required=True,
        readonly=True
    )

    line_ids = fields.One2many(
        'change.requisition.type.wizard.line',
        'wizard_id',
        string='Requisition Lines'
    )

    requisition_type_new = fields.Selection(
        [('internal', 'Internal Picking'), ('purchase', 'Purchase Order')],
        string='New Requisition Type',
        required=True,
        help='Select the new requisition type for selected lines'
    )

    # Informational fields
    total_lines = fields.Integer(
        string='Total Lines',
        compute='_compute_lines_count'
    )

    valid_lines_count = fields.Integer(
        string='Valid Lines',
        compute='_compute_lines_count'
    )

    invalid_lines_count = fields.Integer(
        string='Invalid Lines',
        compute='_compute_lines_count'
    )

    @api.depends('line_ids', 'line_ids.is_changeable')
    def _compute_lines_count(self):
        for wizard in self:
            wizard.total_lines = len(wizard.line_ids)
            wizard.valid_lines_count = len(wizard.line_ids.filtered(lambda l: l.is_changeable))
            wizard.invalid_lines_count = len(wizard.line_ids.filtered(lambda l: not l.is_changeable))

    @api.model
    def default_get(self, fields_list):
        """Initialize wizard with selected or all lines from the requisition"""
        res = super(ChangeRequisitionTypeWizard, self).default_get(fields_list)

        # Get context
        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')

        if active_model != 'material.purchase.requisition':
            raise UserError(_('This wizard can only be called from Purchase Requisition.'))

        if not active_id:
            raise UserError(_('No requisition selected.'))

        requisition = self.env['material.purchase.requisition'].browse(active_id)

        # Check requisition state
        if requisition.state != 'approve':
            raise UserError(_('Requisition type can only be changed in Approved state.'))

        if not requisition.requisition_line_ids:
            raise UserError(_('No requisition lines found to change.'))

        res.update({
            'requisition_id': requisition.id,
        })

        return res

    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        """Populate wizard lines when requisition is set"""
        if self.requisition_id:
            # Clear existing lines
            self.line_ids = [(5, 0, 0)]

            # Create new lines for each requisition line
            line_vals = []
            for req_line in self.requisition_id.requisition_line_ids:
                line_vals.append((0, 0, {
                    'requisition_line_id': req_line.id,
                }))

            self.line_ids = line_vals

    def action_confirm(self):
        """Update the requisition type for valid lines"""
        self.ensure_one()

        # Get only selected AND changeable lines
        lines_to_change = self.line_ids.filtered(lambda l: l.selected and l.is_changeable)

        if not lines_to_change:
            raise UserError(_(
                'No valid lines to change. Please select lines that do not have '
                'pickings or purchase orders already created.'
            ))

        # Update requisition type
        requisition_line_ids = lines_to_change.mapped('requisition_line_id')

        # Clear vendor selection if changing to internal
        if self.requisition_type_new == 'internal':
            requisition_line_ids.write({
                'requisition_type': self.requisition_type_new,
                'partner_id': [(5, 0, 0)],  # Clear all vendors
            })
            message = _('Requisition type changed to Internal Picking for %d line(s).') % len(requisition_line_ids)
        else:
            requisition_line_ids.write({
                'requisition_type': self.requisition_type_new,
            })
            message = _('Requisition type changed to Purchase Order for %d line(s).') % len(requisition_line_ids)

        # Log message on requisition
        self.requisition_id.message_post(
            body=message,
            subject=_('Requisition Type Changed'),
            message_type='notification'
        )


class ChangeRequisitionTypeWizardLine(models.TransientModel):
    _name = 'change.requisition.type.wizard.line'
    _description = 'Change Requisition Type Wizard Line'

    wizard_id = fields.Many2one(
        'change.requisition.type.wizard',
        string='Wizard',
        ondelete='cascade'
    )

    requisition_line_id = fields.Many2one(
        'material.purchase.requisition.line',
        string='Requisition Line',
        required=True
    )

    # Related fields for display
    product_id = fields.Many2one(
        related='requisition_line_id.product_id',
        string='Product',
        readonly=True
    )

    description = fields.Char(
        related='requisition_line_id.description',
        string='Description',
        readonly=True
    )

    qty = fields.Float(
        related='requisition_line_id.qty',
        string='Quantity',
        readonly=True
    )

    uom = fields.Many2one(
        related='requisition_line_id.uom',
        string='UoM',
        readonly=True
    )

    current_requisition_type = fields.Selection(
        related='requisition_line_id.requisition_type',
        string='Current Type',
        readonly=True
    )

    partner_id = fields.Many2many(
        related='requisition_line_id.partner_id',
        string='Vendors',
        readonly=True
    )

    # Selection field for user to choose which lines to change
    selected = fields.Boolean(
        string='Change',
        default=True,
        help='Check this to change the requisition type for this line'
    )

    # Computed fields for validation
    is_changeable = fields.Boolean(
        string='Changeable',
        compute='_compute_is_changeable',
        help='Indicates if this line can be changed (no PO or picking created)'
    )

    change_status = fields.Char(
        string='Status',
        compute='_compute_is_changeable'
    )

    has_picking = fields.Boolean(
        string='Has Picking',
        compute='_compute_is_changeable'
    )

    has_purchase_order = fields.Boolean(
        string='Has Purchase Order',
        compute='_compute_is_changeable'
    )

    @api.depends('requisition_line_id')
    def _compute_is_changeable(self):
        """OPTIMIZED: Batch search instead of N+1 per-line searches"""
        # Initialize defaults
        for line in self:
            line.is_changeable = False
            line.change_status = 'No line selected'
            line.has_picking = False
            line.has_purchase_order = False

        lines_with_req = self.filtered(lambda l: l.requisition_line_id)
        if not lines_with_req:
            return

        req_line_ids = lines_with_req.mapped('requisition_line_id').ids

        # Batch search: all stock moves for these requisition lines
        moves = self.env['stock.move'].search([
            ('custom_requisition_line_id', 'in', req_line_ids)
        ])
        lines_with_moves = set(moves.mapped('custom_requisition_line_id').ids)

        # Batch search: all PO lines for these requisition lines
        po_lines = self.env['purchase.order.line'].search([
            ('custom_requisition_line_id', 'in', req_line_ids)
        ])
        lines_with_po = set(po_lines.mapped('custom_requisition_line_id').ids)

        for line in lines_with_req:
            req_id = line.requisition_line_id.id
            has_picking = req_id in lines_with_moves
            has_po = req_id in lines_with_po
            line.has_picking = has_picking
            line.has_purchase_order = has_po

            if has_picking and has_po:
                line.is_changeable = False
                line.change_status = 'Has both Picking and PO'
            elif has_picking:
                line.is_changeable = False
                line.change_status = 'Picking created'
            elif has_po:
                line.is_changeable = False
                line.change_status = 'Purchase Order created'
            else:
                line.is_changeable = True
                line.change_status = 'Can be changed'

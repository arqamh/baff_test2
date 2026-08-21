# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models


class RestrictCreateAndEditConfig(models.Model):
    """Config record: for a given model, which Many2one fields should hide
    their 'Create' and 'Create and Edit' options in the web client?

    One config = one model + one-or-many Many2one fields on that model.
    Multiple configs can target the same model (additive).
    """
    _name = 'restrict.create.and.edit'
    _description = 'Restrict Create and Edit Configuration'
    _order = 'model_id, id'

    name = fields.Char(
        string='Name',
        required=True,
        help="Human-readable label for this restriction rule.",
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        help="Model whose Many2one fields you want to restrict.",
    )
    model_name = fields.Char(
        related='model_id.model',
        store=True,
        index=True,
        string='Model Technical Name',
    )
    field_ids = fields.Many2many(
        'ir.model.fields',
        'restrict_create_and_edit_field_rel',
        'config_id',
        'field_id',
        string='Restricted Many2one Fields',
        domain="[('model_id', '=', model_id), ('ttype', '=', 'many2one')]",
        help="Many2one fields on the selected model that should hide "
             "their 'Create' / 'Create and Edit' dropdown options.",
    )
    restrict_enabled = fields.Boolean(
        string='Enable Restriction',
        default=True,
        help="Turn this rule on or off without deleting it.",
    )
    active = fields.Boolean(default=True)

    @api.onchange('model_id')
    def _onchange_model_id(self):
        """Clear field_ids when the model changes — fields from the old model
        would no longer satisfy the domain."""
        self.field_ids = [(5, 0, 0)]

    # ------------------------------------------------------------------
    # Public helper — consumed by ir.http.session_info
    # ------------------------------------------------------------------
    @api.model
    def _get_active_restrictions(self):
        """Return a map {model_technical_name: [field_name, ...]} of every
        currently-active restriction. Used by the JS patch to decide which
        Many2one widgets should hide their create options.
        """
        result = defaultdict(set)
        configs = self.sudo().search([
            ('restrict_enabled', '=', True),
            ('active', '=', True),
        ])
        for config in configs:
            model = config.model_name
            if not model:
                continue
            for field in config.field_ids:
                # Guard against stale records where field's model drifted
                # away from config.model_id (shouldn't happen via the UI,
                # but protects against direct DB edits).
                if field.model == model and field.ttype == 'many2one':
                    result[model].add(field.name)
        return {model: sorted(fields) for model, fields in result.items()}

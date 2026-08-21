# -*- coding: utf-8 -*-
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestRestrictFrontend(HttpCase):
    """Frontend tour tests for the restrict_create_and_edit module.

    These tests launch a real browser via Odoo's tour framework to verify
    that the JS patch correctly hides 'Create' / 'Create and Edit' options
    and the 'New' button in the Search More dialog.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Ensure there is a customer to select in the tour.
        cls.env['res.partner'].create({
            'name': 'Restrict Test Partner',
            'email': 'restrict_test@example.com',
        })

        # Create restriction: sale.order → partner_id
        IrModel = cls.env['ir.model']
        IrModelFields = cls.env['ir.model.fields']

        sale_order_model = IrModel.search([('model', '=', 'sale.order')], limit=1)
        partner_field = IrModelFields.search([
            ('model', '=', 'sale.order'),
            ('name', '=', 'partner_id'),
            ('ttype', '=', 'many2one'),
        ], limit=1)

        cls.env['restrict.create.and.edit'].create({
            'name': 'Test SO Partner Restriction',
            'model_id': sale_order_model.id,
            'field_ids': [(6, 0, [partner_field.id])],
            'restrict_enabled': True,
        })

    def test_m2o_create_hidden_on_restricted_field(self):
        """B.8/B.9/B.10 — Verify Create options are hidden and selection works."""
        if self.env['ir.module.module']._get('sale').state != 'installed':
            self.skipTest("Sale module is not installed — tour requires Sale Order form.")
        self.start_tour(
            '/odoo/sales',
            'test_restrict_m2o_create_hidden',
            login='admin',
        )

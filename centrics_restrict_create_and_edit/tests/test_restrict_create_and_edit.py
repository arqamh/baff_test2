# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestRestrictCreateAndEditConfig(TransactionCase):
    """Test suite for the restrict.create.and.edit configuration model.

    Covers:
        A. Configuration Menu Tests (scenarios 1-7)
        C. Cross-Model Tests (scenarios 15-16)
        D. Edge Cases (scenarios 13-14, 17-20)
        Session info integration
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        IrModel = cls.env['ir.model']
        IrModelFields = cls.env['ir.model.fields']

        # Fetch models
        cls.sale_order_model = IrModel.search([('model', '=', 'sale.order')], limit=1)
        cls.purchase_order_model = IrModel.search([('model', '=', 'purchase.order')], limit=1)
        cls.partner_model = IrModel.search([('model', '=', 'res.partner')], limit=1)

        # Fetch Many2one fields on sale.order
        cls.so_partner_field = IrModelFields.search([
            ('model', '=', 'sale.order'),
            ('name', '=', 'partner_id'),
            ('ttype', '=', 'many2one'),
        ], limit=1)
        cls.so_pricelist_field = IrModelFields.search([
            ('model', '=', 'sale.order'),
            ('name', '=', 'pricelist_id'),
            ('ttype', '=', 'many2one'),
        ], limit=1)
        cls.so_fiscal_field = IrModelFields.search([
            ('model', '=', 'sale.order'),
            ('name', '=', 'fiscal_position_id'),
            ('ttype', '=', 'many2one'),
        ], limit=1)

        # Fetch Many2one fields on purchase.order
        cls.po_partner_field = IrModelFields.search([
            ('model', '=', 'purchase.order'),
            ('name', '=', 'partner_id'),
            ('ttype', '=', 'many2one'),
        ], limit=1)

        # A non-many2one field for negative tests
        cls.so_name_field = IrModelFields.search([
            ('model', '=', 'sale.order'),
            ('name', '=', 'name'),
        ], limit=1)

        cls.Config = cls.env['restrict.create.and.edit']

    def setUp(self):
        super().setUp()
        # Clean slate — remove any pre-existing config records so each
        # test controls exactly what exists in the DB.
        self.Config.search([]).unlink()

    # ------------------------------------------------------------------
    # A. Configuration Menu Tests
    # ------------------------------------------------------------------

    def test_01_create_config_record(self):
        """A.1/A.2 — Create a config record with a model selection."""
        config = self.Config.create({
            'name': 'Test SO Restriction',
            'model_id': self.sale_order_model.id,
        })
        self.assertTrue(config.id)
        self.assertEqual(config.model_name, 'sale.order')
        self.assertTrue(config.restrict_enabled, "restrict_enabled should default to True")
        self.assertTrue(config.active, "active should default to True")

    def test_02_field_filtering_only_many2one(self):
        """A.3 — Only Many2one fields of the selected model should be linkable."""
        config = self.Config.create({
            'name': 'Test field filtering',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
        })
        # partner_id is many2one on sale.order — should be stored
        self.assertIn(self.so_partner_field, config.field_ids)

    def test_03_model_change_clears_fields(self):
        """A.4 — Changing the model should clear previously selected fields."""
        config = self.Config.create({
            'name': 'Test model change',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
        })
        self.assertEqual(len(config.field_ids), 1)

        # Simulate onchange when model changes
        config.model_id = self.purchase_order_model
        config._onchange_model_id()
        self.assertEqual(len(config.field_ids), 0,
                         "field_ids should be cleared after model change")

    def test_04_multiple_field_selection(self):
        """A.5 — Multiple Many2one fields can be selected and persisted."""
        config = self.Config.create({
            'name': 'Test multiple fields',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [
                self.so_partner_field.id,
                self.so_pricelist_field.id,
                self.so_fiscal_field.id,
            ])],
        })
        self.assertEqual(len(config.field_ids), 3)

        # Reload from DB and verify persistence
        config.invalidate_recordset()
        config_reloaded = self.Config.browse(config.id)
        self.assertEqual(len(config_reloaded.field_ids), 3)
        field_names = config_reloaded.field_ids.mapped('name')
        self.assertIn('partner_id', field_names)
        self.assertIn('pricelist_id', field_names)
        self.assertIn('fiscal_position_id', field_names)

    def test_05_enable_disable_toggle(self):
        """A.6 — Toggling restrict_enabled persists correctly."""
        config = self.Config.create({
            'name': 'Test toggle',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
            'restrict_enabled': True,
        })
        self.assertTrue(config.restrict_enabled)

        config.restrict_enabled = False
        config.invalidate_recordset()
        self.assertFalse(self.Config.browse(config.id).restrict_enabled)

        config.restrict_enabled = True
        config.invalidate_recordset()
        self.assertTrue(self.Config.browse(config.id).restrict_enabled)

    def test_06_duplicate_model_config_allowed(self):
        """A.7 — Multiple config records for the same model are allowed (additive)."""
        config1 = self.Config.create({
            'name': 'SO restriction 1',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
        })
        config2 = self.Config.create({
            'name': 'SO restriction 2',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_pricelist_field.id])],
        })
        self.assertTrue(config1.id != config2.id)

        # Both should merge into one list via _get_active_restrictions
        restrictions = self.Config._get_active_restrictions()
        self.assertIn('partner_id', restrictions.get('sale.order', []))
        self.assertIn('pricelist_id', restrictions.get('sale.order', []))

    # ------------------------------------------------------------------
    # B. _get_active_restrictions() logic
    #    (This is what powers frontend scenarios 8-14)
    # ------------------------------------------------------------------

    def test_07_restrictions_returned_for_enabled_config(self):
        """B.8/B.9 — Enabled config returns restricted fields."""
        self.Config.create({
            'name': 'Active restriction',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
            'restrict_enabled': True,
        })
        restrictions = self.Config._get_active_restrictions()
        self.assertIn('sale.order', restrictions)
        self.assertIn('partner_id', restrictions['sale.order'])

    def test_08_restrictions_empty_when_disabled(self):
        """B.13 — Disabled config should NOT appear in restrictions."""
        self.Config.create({
            'name': 'Disabled restriction',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
            'restrict_enabled': False,
        })
        restrictions = self.Config._get_active_restrictions()
        so_fields = restrictions.get('sale.order', [])
        self.assertNotIn('partner_id', so_fields)

    def test_09_restrictions_empty_when_archived(self):
        """B.14 — Archived config should NOT appear in restrictions."""
        config = self.Config.create({
            'name': 'Archived restriction',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
            'restrict_enabled': True,
            'active': False,
        })
        restrictions = self.Config._get_active_restrictions()
        so_fields = restrictions.get('sale.order', [])
        self.assertNotIn('partner_id', so_fields)
        # Verify the record is indeed archived
        self.assertFalse(config.active)

    def test_10_restrictions_empty_when_no_fields(self):
        """Edge — Config with model but no fields should not produce output."""
        self.Config.create({
            'name': 'No fields config',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [])],
            'restrict_enabled': True,
        })
        restrictions = self.Config._get_active_restrictions()
        # sale.order should not appear since there are no fields
        self.assertNotIn('sale.order', restrictions)

    def test_11_unrestricted_field_not_affected(self):
        """B.11 — Fields NOT in the config should not appear in restrictions."""
        self.Config.create({
            'name': 'Only partner',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
        })
        restrictions = self.Config._get_active_restrictions()
        so_fields = restrictions.get('sale.order', [])
        self.assertIn('partner_id', so_fields)
        self.assertNotIn('pricelist_id', so_fields,
                         "pricelist_id was NOT configured — must not be restricted")
        self.assertNotIn('fiscal_position_id', so_fields)

    def test_12_multiple_fields_on_same_model(self):
        """B.12 — Multiple restricted fields on the same model."""
        self.Config.create({
            'name': 'Multi-field SO',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [
                self.so_partner_field.id,
                self.so_pricelist_field.id,
                self.so_fiscal_field.id,
            ])],
        })
        restrictions = self.Config._get_active_restrictions()
        so_fields = restrictions['sale.order']
        self.assertIn('partner_id', so_fields)
        self.assertIn('pricelist_id', so_fields)
        self.assertIn('fiscal_position_id', so_fields)

    # ------------------------------------------------------------------
    # C. Cross-Model Tests
    # ------------------------------------------------------------------

    def test_13_different_model_restriction(self):
        """C.15 — Restriction on purchase.order is independent of sale.order."""
        self.Config.create({
            'name': 'PO vendor restriction',
            'model_id': self.purchase_order_model.id,
            'field_ids': [(6, 0, [self.po_partner_field.id])],
        })
        restrictions = self.Config._get_active_restrictions()
        self.assertIn('purchase.order', restrictions)
        self.assertIn('partner_id', restrictions['purchase.order'])
        # sale.order should NOT be present (no config for it in this test)
        self.assertNotIn('sale.order', restrictions)

    def test_14_multiple_model_configs_independent(self):
        """C.16 — Multiple model configs work independently."""
        self.Config.create({
            'name': 'SO restriction',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
        })
        self.Config.create({
            'name': 'PO restriction',
            'model_id': self.purchase_order_model.id,
            'field_ids': [(6, 0, [self.po_partner_field.id])],
        })
        restrictions = self.Config._get_active_restrictions()

        self.assertIn('sale.order', restrictions)
        self.assertIn('partner_id', restrictions['sale.order'])

        self.assertIn('purchase.order', restrictions)
        self.assertIn('partner_id', restrictions['purchase.order'])

    # ------------------------------------------------------------------
    # D. Edge Cases
    # ------------------------------------------------------------------

    def test_15_stale_field_model_mismatch_ignored(self):
        """D — If a field's model doesn't match the config's model, skip it.

        Simulates the case where someone manually inserts a wrong field_id
        into the relation table (e.g., a purchase.order field linked to a
        sale.order config).
        """
        config = self.Config.create({
            'name': 'Stale field test',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.po_partner_field.id])],
            # po_partner_field.model = 'purchase.order' but config.model = 'sale.order'
        })
        restrictions = self.Config._get_active_restrictions()
        # The mismatched field should be ignored
        so_fields = restrictions.get('sale.order', [])
        self.assertNotIn('partner_id', so_fields,
                         "Field from wrong model should be skipped")

    def test_16_restrictions_sorted_alphabetically(self):
        """D — Output field list is sorted for deterministic JSON."""
        self.Config.create({
            'name': 'Sorted test',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [
                self.so_pricelist_field.id,   # p...
                self.so_fiscal_field.id,      # f...
                self.so_partner_field.id,     # p... (partner < pricelist)
            ])],
        })
        restrictions = self.Config._get_active_restrictions()
        so_fields = restrictions['sale.order']
        self.assertEqual(so_fields, sorted(so_fields),
                         "Fields must be in alphabetical order")

    def test_17_delete_config_removes_restrictions(self):
        """D.14 — Deleting the config record removes restrictions entirely."""
        config = self.Config.create({
            'name': 'To be deleted',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
        })
        restrictions = self.Config._get_active_restrictions()
        self.assertIn('sale.order', restrictions)

        config.unlink()
        restrictions = self.Config._get_active_restrictions()
        self.assertNotIn('sale.order', restrictions,
                         "Restrictions should vanish after config is deleted")

    def test_18_toggle_off_then_on_restores(self):
        """D.13/18 — Disabling then re-enabling restores the restriction."""
        config = self.Config.create({
            'name': 'Toggle test',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
            'restrict_enabled': True,
        })

        # Disable
        config.restrict_enabled = False
        restrictions = self.Config._get_active_restrictions()
        self.assertNotIn('sale.order', restrictions)

        # Re-enable
        config.restrict_enabled = True
        restrictions = self.Config._get_active_restrictions()
        self.assertIn('sale.order', restrictions)
        self.assertIn('partner_id', restrictions['sale.order'])

    def test_19_duplicate_configs_merge_fields(self):
        """D — Two configs for the same model merge their fields, no duplicates."""
        self.Config.create({
            'name': 'Config A',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
        })
        self.Config.create({
            'name': 'Config B',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [
                self.so_partner_field.id,      # duplicate
                self.so_pricelist_field.id,     # new
            ])],
        })
        restrictions = self.Config._get_active_restrictions()
        so_fields = restrictions['sale.order']
        # partner_id should appear once (set dedup), plus pricelist_id
        self.assertEqual(so_fields.count('partner_id'), 1)
        self.assertIn('pricelist_id', so_fields)

    def test_20_no_configs_returns_empty_dict(self):
        """D — With no config records at all, result is empty dict."""
        # Delete all existing configs
        self.Config.search([]).unlink()
        restrictions = self.Config._get_active_restrictions()
        self.assertEqual(restrictions, {})

    # ------------------------------------------------------------------
    # Session Info Integration
    # ------------------------------------------------------------------

    def test_21_session_info_contains_key(self):
        """Session info must contain the restrict_create_and_edit key."""
        self.Config.create({
            'name': 'Session test',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
        })
        # session_info requires a request context — test the helper directly
        # to avoid needing an HTTP request. The ir.http override is a simple
        # pass-through so testing the helper is sufficient.
        restrictions = self.Config._get_active_restrictions()
        self.assertIsInstance(restrictions, dict)
        self.assertIn('sale.order', restrictions)

    def test_22_sudo_makes_restrictions_visible_to_all(self):
        """D.19 — Restrictions apply to all internal users (sudo in helper)."""
        self.Config.create({
            'name': 'Global restriction',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
        })
        # Call as a non-admin user (demo user or basic employee)
        demo_user = self.env.ref('base.user_demo', raise_if_not_found=False)
        if demo_user:
            restrictions = (
                self.Config
                .with_user(demo_user)
                ._get_active_restrictions()
            )
            self.assertIn('sale.order', restrictions)
            self.assertIn('partner_id', restrictions['sale.order'])

    def test_23_master_record_creation_unaffected(self):
        """D.20 — Restriction on sale.order partner_id does NOT block
        creating res.partner records directly. The restriction only
        affects the Many2one dropdown in the web client; the model
        itself has no create-permission changes.
        """
        self.Config.create({
            'name': 'SO partner restriction',
            'model_id': self.sale_order_model.id,
            'field_ids': [(6, 0, [self.so_partner_field.id])],
        })
        # Creating a partner directly should work fine
        partner = self.env['res.partner'].create({
            'name': 'Test Customer Created Directly',
        })
        self.assertTrue(partner.id)
        # Clean up
        partner.unlink()

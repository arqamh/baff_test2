# -*- coding: utf-8 -*-
from odoo import models


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    def default_get(self, fields_list):
        """Create new salary structures with no auto-added salary rules.

        Core ``hr.payroll.structure`` declares the ``rule_ids`` One2many with
        ``default=_get_default_rule_ids``, which injects eight generic rules
        (Basic, Gross, Net, Deduction, Attachment/Assignment of Salary, Child
        Support, Reimbursement) into every new structure. We strip that default
        here so a freshly created structure starts empty. Only the rules a user
        adds in the UI, or the rules an XML data file defines, end up linked to
        the structure -- which removes the duplicate/unwanted rules.

        This also covers ORM/XML creation: ``create`` resolves missing field
        defaults through ``_add_missing_default_values`` -> ``default_get``, so
        a ``<record model="hr.payroll.structure">`` that omits ``rule_ids`` no
        longer receives the generic rules either.
        """
        defaults = super().default_get(fields_list)
        # Drop the auto-injected salary rules, if any were proposed.
        defaults.pop('rule_ids', None)
        return defaults

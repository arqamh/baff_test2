# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Codes of the generic salary rules Odoo auto-injects through the core
# hr.payroll.structure ``rule_ids`` default (_get_default_rule_ids). None of the
# BAFF XML rules use these codes (they use BAFF_BASIC / BAFF_GROSS / BAFF_NET,
# etc.), so these codes uniquely identify the unwanted rules.
DEFAULT_RULE_CODES = [
    'BASIC', 'GROSS', 'DEDUCTION', 'ATTACH_SALARY',
    'ASSIG_SALARY', 'CHILD_SUPPORT', 'REIMBURSEMENT', 'NET',
]

# External IDs of the structures created by this module's XML data file.
STRUCTURE_XML_IDS = [
    'baff_hr_payroll_extend.baff_hr_payroll_structure_ocean_voyager',
    'baff_hr_payroll_extend.baff_hr_payroll_structure_staff',
    'baff_hr_payroll_extend.baff_hr_payroll_structure_non_staff',
]


def migrate(cr, version):
    """Remove the generic salary rules Odoo auto-added to the BAFF structures.

    Installs done before this version created the three Ocean Voyager
    structures without an explicit ``rule_ids`` value, so the core default
    injected eight generic rules (Basic, Gross, Net, ...) into each one
    alongside the intended BAFF_* rules. This one-off cleanup deletes only
    those auto-injected rules; rules created from an XML data file (which all
    carry an external ID) are never touched.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Resolve only the structures that actually exist in this database.
    structures = env['hr.payroll.structure']
    for xml_id in STRUCTURE_XML_IDS:
        structure = env.ref(xml_id, raise_if_not_found=False)
        if structure:
            structures |= structure

    if not structures:
        return

    # Candidate rules: generic-coded rules linked to the BAFF structures.
    candidates = env['hr.salary.rule'].search([
        ('struct_id', 'in', structures.ids),
        ('code', 'in', DEFAULT_RULE_CODES),
    ])

    # Keep any rule created from an XML data file (it has an external ID);
    # delete only the runtime-injected defaults (no external ID).
    external_ids = candidates.get_external_id()
    rules_to_remove = candidates.filtered(lambda r: not external_ids.get(r.id))

    if rules_to_remove:
        _logger.info(
            "baff_hr_payroll_extend: removing %s auto-injected default salary "
            "rule(s) %s from BAFF structures %s",
            len(rules_to_remove),
            rules_to_remove.mapped('code'),
            structures.mapped('name'),
        )
        rules_to_remove.unlink()

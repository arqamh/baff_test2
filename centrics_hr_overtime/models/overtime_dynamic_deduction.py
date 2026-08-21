# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OvertimeDynamicDeduction(models.Model):
    _name = 'overtime.dynamic.deduction'
    _description = 'Overtime Dynamic Deduction'

    name = fields.Char(string='Deduction Name', required=True)
    deduction_time = fields.Integer(string='Deduction Time (Minutes)', required=True,
                                    help='Number of minutes to deduct from overtime when this deduction is applicable')
    start_time = fields.Float(string='Start Time',
                             help='Start time in 24-hour format (e.g., 9.0 for 09:00, 14.5 for 14:30). '
                                  'Deduction will only be applied if this time falls within the attendance check-in and check-out period. '
                                  'Leave empty to apply deduction regardless of time.')
    end_time = fields.Float(string='End Time',
                           help='End time in 24-hour format (e.g., 17.0 for 17:00, 18.5 for 18:30). '
                                'Deduction will only be applied if this time falls within the attendance check-in and check-out period. '
                                'Leave empty to apply deduction regardless of time.')

    def unlink(self):
        """
        Override unlink to prevent deletion of deductions that are in use by overtime rules.

        Raises:
            UserError: If any deduction is referenced in overtime rules
        """
        for deduction in self:
            # Check if this deduction is used in any overtime rule
            rules_using_deduction = self.env['hr.overtime.rule'].search([
                ('deduction_ids', 'in', deduction.id)
            ])

            if rules_using_deduction:
                # Get the templates associated with these rules
                template_names = []
                for rule in rules_using_deduction:
                    if rule.template_id and rule.template_id.name not in template_names:
                        template_names.append(rule.template_id.name)
                    if rule.secondary_template_id and rule.secondary_template_id.name not in template_names:
                        template_names.append(rule.secondary_template_id.name)

                template_list = ", ".join(template_names) if template_names else _("Unknown templates")

                raise UserError(_(
                    "Cannot delete deduction '%s' because it is currently being used in %d overtime rule(s).\n\n"
                    "Templates using this deduction:\n%s\n\n"
                    "Please remove this deduction from all overtime rules before deleting it."
                ) % (deduction.name, len(rules_using_deduction), template_list))

        return super(OvertimeDynamicDeduction, self).unlink()

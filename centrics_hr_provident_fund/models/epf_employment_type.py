# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EpfEmploymentType(models.Model):
    """
    EPF Employment Type

    Defines employment type categories for EPF (Employees' Provident Fund) purposes.
    Each type is identified by a unique code and name, displayed in dropdowns as '[code] name'.

    This model helps categorize employees based on their employment type for EPF calculations
    and reporting requirements.
    """
    _name = 'epf.employment.type'
    _description = 'EPF Employment Type'
    _order = 'code, name'

    name = fields.Char(
        string='Name',
        required=True,
        help='Full name of the EPF employment type (e.g., "Permanent", "Contract", "Trainee")'
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Short code for the employment type (e.g., "PERM", "CONT", "TRNE")'
    )

    @api.depends('code', 'name')
    def name_get(self):
        """
        Override name_get to display records as '[code] name' in dropdowns.

        Returns:
            list: List of tuples (id, display_name) where display_name is formatted as '[code] name'
        """
        result = []
        for record in self:
            if record.code and record.name:
                display_name = f'[{record.code}] {record.name}'
            elif record.code:
                display_name = f'[{record.code}]'
            elif record.name:
                display_name = record.name
            else:
                display_name = f'ID: {record.id}'
            result.append((record.id, display_name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        Override _name_search to allow searching by both code and name.

        This enables users to search for EPF employment types by either code or name
        when selecting from dropdowns.
        """
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

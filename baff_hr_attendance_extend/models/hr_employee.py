from odoo import models,fields,api,_


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def name_get(self):
        """Custom display name with EPF number"""
        result = []
        for rec in self:
            name = f"{rec.name} [{rec.epf_number}]" if rec.epf_number else rec.name
            result.append((rec.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Support searching by name or EPF number"""
        args = args or []
        if name:
            domain = ['|', ('name', operator, name), ('epf_number', operator, name)]
        else:
            domain = []
        return self.search(domain + args, limit=limit).name_get()

from odoo import models,fields,api,_


class CertificationLevel(models.Model):
    _name = 'certification.level'
    _description = 'Certification Level'

    name = fields.Char(string="Certification Level")
    description = fields.Text(string="Description")

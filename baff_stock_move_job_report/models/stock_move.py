from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    job_costing_id = fields.Many2one(
        'job.costing', string='Job Costing',
        compute='_compute_job_costing_id', store=True, index=True,
        help='Resolved from the linked manufacturing order (raw material or finished).')
    project_id = fields.Many2one(
        'project.project', string='Project',
        related='job_costing_id.project_id', store=True, index=True)
    project_name = fields.Char(
        string='Project / Job Name',
        related='project_id.name', store=True)
    job_costing_number = fields.Char(
        string='Job Costing No.',
        related='job_costing_id.number', store=True)
    job_number = fields.Char(
        string='Job Number',
        related='job_costing_id.job_number', store=True)

    @api.depends('raw_material_production_id', 'raw_material_production_id.job_cost_id',
                 'production_id', 'production_id.job_cost_id')
    def _compute_job_costing_id(self):
        for move in self:
            jc = False
            if move.raw_material_production_id:
                jc = move.raw_material_production_id.job_cost_id
            if not jc and move.production_id:
                jc = move.production_id.job_cost_id
            move.job_costing_id = jc or False

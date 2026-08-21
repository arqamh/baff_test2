from odoo import fields, models, api


class Project(models.Model):
    _inherit = "project.project"

    job_cost_count = fields.Integer(compute='_compute_jobcost_count')
    job_cost_ids = fields.One2many('job.costing', 'project_id')
    state = fields.Selection([('draft', 'Draft'), ('ongoing', 'Ongoing'), ('on_hold', 'On Hold'), ('declined', 'Declined')], default='draft')

    def _compute_jobcost_count(self):
        """FIXED: was mapping ALL records' job_cost_ids then giving same count to every project"""
        for project in self:
            project.job_cost_count = len(project.job_cost_ids)

    def project_to_jobcost_action(self):
        """inbuilt function from the vendor"""
        self.ensure_one()
        job_cost = self.mapped('job_cost_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("odoo_job_costing_management.action_job_costing")
        action['domain'] = [('id', 'in', job_cost.ids)]
        action['context'] = {'default_project_id': self.id, 'default_analytic_id': self.analytic_account_id.id,
                             'default_user_id': self.user_id.id}
        return action


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def _compute_jobcost_count(self):
        """FIXED: was mapping ALL records' job_cost_ids then giving same count to every task"""
        for task in self:
            task.job_cost_count = len(task.job_cost_ids)

    job_cost_count = fields.Integer(compute='_compute_jobcost_count')
    job_cost_ids = fields.One2many('job.costing', 'task_id')

    def task_to_jobcost_action(self):
        """inbuilt function from the vendor"""
        self.ensure_one()
        job_cost = self.mapped('job_cost_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("odoo_job_costing_management.action_job_costing")
        action['domain'] = [('id', 'in', job_cost.ids)]
        action['context'] = {'default_task_id': self.id, 'default_project_id': self.project_id.id,
                             'default_analytic_id': self.project_id.analytic_account_id.id, 'default_user_id':
                                 self.env.user.id}
        return action


        
        

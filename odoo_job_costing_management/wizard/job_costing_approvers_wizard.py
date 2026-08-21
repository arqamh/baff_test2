from odoo import fields, models, api, _
from datetime import datetime


class JobCostingApproversWizard(models.TransientModel):
    _name = 'job.costing.approvers.wizard'

    name = fields.Char(string="Name", default="Prioritize the users that you need to send this RFQ.")
    job_costing_approver_line_ids = fields.One2many('job.costing.approvers.lines.wizard', 'line_id')
    type = fields.Selection([('add', 'Add'), ('update', 'Update')], string="Type", default='add')
    approval_type = fields.Selection([('review', 'Review'), ('approve', 'Approve')], string="Approval Type")

    def send_for_approval(self):
        """Send for approval button. Function sets approval list in PO"""

        job_costing = self.env['job.costing'].browse(self.env.context.get('active_id'))
        if job_costing and self.type == 'add':
            # job_costing.write({'job_costing_approval_line_ids': False})
            vals = []
            for record in self.job_costing_approver_line_ids:
                vals.append((0, 0, {
                    'sequence': record.sequence,
                    'user_id': record.user_id.id,
                }))
            job_costing.job_costing_approval_line_ids = vals
            job_costing.send_to_next_approver()
        else:
            confirmed_lines = job_costing.job_costing_approval_line_ids.filtered(lambda x: x.state in ['approved', 'rejected', 'reviewed']).mapped('sequence')
            last_sequence = confirmed_lines[-1] if confirmed_lines else 0
            vals = []
            count = 1
            if job_costing.state == 'waiting_first_approval':
                for record in self.job_costing_approver_line_ids:
                    vals.append((0, 0, {
                        'sequence': count + last_sequence,
                        'user_id': record.user_id.id,
                        'type': 'review'
                    }))
                    count += 1
            elif job_costing.state in ['waiting_second_approval', 'waiting_production_approval']:
                for record in self.job_costing_approver_line_ids:
                    vals.append((0, 0, {
                        'sequence': count + last_sequence,
                        'user_id': record.user_id.id,
                        'type': 'approval'
                    }))
                    count += 1
            job_costing.job_costing_approval_line_ids.filtered(lambda x: x.state not in ['approved', 'rejected', 'reviewed']).unlink()
            job_costing.job_costing_approval_line_ids = vals
            job_costing.send_to_next_approver()


class JobCostingApproversLinesWizard(models.TransientModel):
    _name = 'job.costing.approvers.lines.wizard'
    _order = 'sequence'

    line_id = fields.Many2one('job.costing.approvers.wizard')
    job_costing_line_id = fields.Many2one('job.costing.approval.lines')
    sequence = fields.Integer(string="Sequence", default=1)
    user_id = fields.Many2one('res.users', string="Users")




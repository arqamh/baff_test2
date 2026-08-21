from odoo import models, fields, api


class QualityPoint(models.Model):
    _inherit = "quality.point"

    # Link analytic account from BOM's job costing
    analytic_account_id = fields.Many2one(
        related='operation_id.bom_id.job_cost_id.analytic_id',
        string='Analytic Account',
        store=True,
        readonly=True
    )


class QualityCheck(models.Model):
    _inherit = "quality.check"

    is_required_approval = fields.Boolean(string="Is Required Approval", compute='_compute_is_required_approval')

    # Related fields for better visibility in tree view
    operation_name = fields.Char(related='workorder_id.name', string='Operation', store=True, readonly=True)
    mo_number = fields.Char(related='production_id.name', string='MO Number', store=True, readonly=True)
    analytic_account_id = fields.Many2one(related='production_id.analytic_account_id', string='Analytic Account', store=True, readonly=True)

    def _compute_is_required_approval(self):
        """ Computing whether the manufacturing order needs to be approved"""
        for record in self:
            if record.workorder_id.production_id.approval_state == False:
                record.is_required_approval = False
            else:
                record.is_required_approval = True

    def do_pass(self):
        """Override to send email notification for MO-related quality checks"""
        res = super(QualityCheck, self).do_pass()
        if self.production_id:
            self._send_quality_check_notification('pass')
        return res

    def do_fail(self):
        """Override to send email notification for MO-related quality checks"""
        res = super(QualityCheck, self).do_fail()
        if self.production_id:
            self._send_quality_check_notification('fail')
        return res

    def _send_quality_check_notification(self, result):
        """Send email notification to quality team members"""
        self.ensure_one()

        # Skip if no recipients configured
        if not self.team_id.notification_user_ids:
            return

        # Get valid email addresses
        recipient_emails = ','.join(
            self.team_id.notification_user_ids.filtered(lambda u: u.email).mapped('email')
        )

        if not recipient_emails:
            return

        # Get manufacturing order details
        mo = self.production_id
        job_costing_ref = mo.job_costing_number or 'N/A'

        # Build context for email template
        context = {
            'subject': f"Quality Check {result.upper()}: {self.name} - {mo.name}",
            'heading': f"Quality Check {result.upper()} Notification",
            'email_from': self.env.user.email or self.env.company.email,
            'email_to': recipient_emails,
            'result': result.upper(),

            # Quality Check Information
            'check_name': self.name or 'N/A',
            'check_title': self.title or 'N/A',
            'test_type': self.test_type_id.name or 'N/A',
            'performed_by': self.user_id.name if self.user_id else 'N/A',
            'control_date': self.control_date.strftime('%Y-%m-%d %H:%M:%S') if self.control_date else 'N/A',
            'quality_team': self.team_id.name or 'N/A',

            # Manufacturing Order Information
            'mo_number': mo.name,
            'mo_product': mo.product_id.name,
            'mo_quantity': mo.product_qty,
            'mo_uom': mo.product_uom_id.name,
            'job_costing': job_costing_ref,
            'project': mo.project_id.name if mo.project_id else 'N/A',
            'analytic_account': mo.job_cost_id.analytic_id.name if mo.job_cost_id and mo.job_cost_id.analytic_id else 'N/A',
            'bom': mo.bom_id.display_name if mo.bom_id else 'N/A',

            # Operation Information
            'operation_name': self.workorder_id.name if self.workorder_id else 'N/A',
            'work_center': self.workorder_id.workcenter_id.name if self.workorder_id else 'N/A',

            # Product and Lot Information
            'product_name': self.product_id.name if self.product_id else 'N/A',
            'lot_number': self.lot_id.name if self.lot_id else 'N/A',
            'finished_lot': mo.lot_producing_id.name if mo.lot_producing_id else 'N/A',
        }

        # Select template based on result
        template_ref = f'baff_manufacturing_modifications.quality_check_{result}_email_notification'
        template_id = self.env.ref(template_ref)

        # Send email
        self.env['mail.template'].browse(template_id.id).with_context(context).send_mail(
            self.id,
            force_send=True
        )

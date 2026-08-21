# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MaterialPurchaseRequisitionLine(models.Model):
    _name = 'material.purchase.requisition.line'
    _inherit = [
        'analytic.mixin',
        'material.purchase.requisition.line'
    ]

    def send_to_pr(self):
        """
        @override - add analytic distribution details to the procurement line
        OPTIMIZED: Batch fetch procurement plans instead of N+1 search per record
        """
        purchase_records = self.filtered(lambda r: r.requisition_type == 'purchase')
        if not purchase_records:
            return

        # Collect lookup keys for batch query
        product_ids = set()
        sources = set()
        for record in purchase_records:
            if record.product_id:
                product_ids.add(record.product_id.id)
            if record.requisition_id and record.requisition_id.job_costing_id:
                sources.add(record.requisition_id.job_costing_id.display_name)

        # BATCH QUERY: Fetch all potentially matching procurement plans
        domain = [('product_id', 'in', list(product_ids))]
        if sources:
            domain.append(('source', 'in', list(sources)))
        all_procurement_plans = self.env['procurement.plan'].search(domain)

        # Group by (scheduled_date, source, product_id) for O(1) lookup
        plans_by_key = {}
        for plan in all_procurement_plans:
            key = (plan.scheduled_date, plan.source, plan.product_id.id)
            if key not in plans_by_key:
                plans_by_key[key] = plan

        procurement_obj = self.env['procurement.plan']
        for record in purchase_records:
            scheduled_date = record.scheduled_date.date() if hasattr(record.scheduled_date, 'date') else record.scheduled_date
            source = record.requisition_id.job_costing_id.display_name if record.requisition_id and record.requisition_id.job_costing_id else False
            key = (scheduled_date, source, record.product_id.id)

            procurement_line = plans_by_key.get(key)
            if procurement_line:
                procurement_line.update({
                    'requisition_id': record.requisition_id.id,
                    'analytic_distribution': record.analytic_distribution
                })
                if procurement_line.actual_to_order_qty < record.qty:
                    procurement_line.required_qty = record.qty
                    procurement_line.to_order_qty += record.extra_qty
                record.send_to_procurement_email()
                record.update({
                    'sent_procurement': True
                })
            else:
                source_name = record.requisition_id.name
                vals = {
                    'product_id': record.product_id.id,
                    'product_tml_id': record.product_id.product_tmpl_id.id if record.product_id.product_tmpl_id else False,
                    'mrp_id': False,
                    'source': source_name,
                    'product_uom': record.uom.id,
                    'required_qty': (record.qty + record.extra_qty),
                    'component_id': False,
                    'scheduled_date': record.scheduled_date,
                    'company_id': record.requisition_id.company_id.id,
                    'partner_ids': record.partner_id.ids,
                    'partner_id': record.product_id.seller_ids[0].partner_id.id if record.product_id.seller_ids else False,
                    'requisition_id': record.requisition_id.id,
                    'analytic_distribution': record.analytic_distribution
                }
                procurement_line = procurement_obj.create(vals)
                if procurement_line:
                    record.send_to_procurement_email()
                    record.update({
                        'sent_procurement': True
                    })

    def send_to_pr_and_notify_once(self):
        """
        @override - add analytic distribution details to the procurement line and avoids sending duplicate emails for each line.
        OPTIMIZED: Batch fetch procurement plans instead of N+1 search per record
        """
        purchase_records = self.filtered(lambda r: r.requisition_type == 'purchase')
        if not purchase_records:
            return

        # Collect lookup keys for batch query
        product_ids = set()
        sources = set()
        for record in purchase_records:
            if record.product_id:
                product_ids.add(record.product_id.id)
            if record.requisition_id and record.requisition_id.job_costing_id:
                sources.add(record.requisition_id.job_costing_id.display_name)

        # BATCH QUERY: Fetch all potentially matching procurement plans
        domain = [('product_id', 'in', list(product_ids))]
        if sources:
            domain.append(('source', 'in', list(sources)))
        all_procurement_plans = self.env['procurement.plan'].search(domain)

        # Group by (scheduled_date, source, product_id) for O(1) lookup
        plans_by_key = {}
        for plan in all_procurement_plans:
            key = (plan.scheduled_date, plan.source, plan.product_id.id)
            if key not in plans_by_key:
                plans_by_key[key] = plan

        procurement_obj = self.env['procurement.plan']
        for record in purchase_records:
            scheduled_date = record.scheduled_date.date() if hasattr(record.scheduled_date, 'date') else record.scheduled_date
            source = record.requisition_id.job_costing_id.display_name if record.requisition_id and record.requisition_id.job_costing_id else False
            key = (scheduled_date, source, record.product_id.id)

            procurement_line = plans_by_key.get(key)
            if procurement_line:
                procurement_line.update({
                    'requisition_id': record.requisition_id.id,
                    'analytic_distribution': record.analytic_distribution
                })
                if procurement_line.actual_to_order_qty < record.qty:
                    procurement_line.required_qty = record.qty
                    procurement_line.to_order_qty += record.extra_qty
                record.send_to_procurement_email()
                record.update({
                    'sent_procurement': True
                })
            else:
                source_name = record.requisition_id.name
                vals = {
                    'product_id': record.product_id.id,
                    'product_tml_id': record.product_id.product_tmpl_id.id if record.product_id.product_tmpl_id else False,
                    'mrp_id': False,
                    'source': source_name,
                    'product_uom': record.uom.id,
                    'required_qty': (record.qty + record.extra_qty),
                    'component_id': False,
                    'scheduled_date': record.scheduled_date,
                    'company_id': record.requisition_id.company_id.id,
                    'partner_ids': record.partner_id.ids,
                    'partner_id': record.product_id.seller_ids[0].partner_id.id if record.product_id.seller_ids else False,
                    'requisition_id': record.requisition_id.id,
                    'analytic_distribution': record.analytic_distribution
                }
                procurement_line = procurement_obj.create(vals)
                if procurement_line:
                    record.update({
                        'sent_procurement': True
                    })
        if not self.requisition_id.is_email_sent_once:
            self.send_to_procurement_email()

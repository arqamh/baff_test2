# -*- coding: utf-8 -*-
{
    'name': 'GRN Approval Workflow',
    'version': '16.0.1.0.0',
    'license': 'LGPL-3',
    'summary': 'Approval workflow for Goods Receipt Notes (Incoming Transfers) '
               'with configurable approvers and email notifications.',
    'description': """
GRN Approval Workflow
=====================
Adds a Submit / Approve / Reject approval flow to incoming stock transfers
(GRNs) before they can be validated and stock-updated.

Features
--------
* New statuses: Draft -> Waiting Approval -> Approved / Rejected -> Done
* Submit for Approval button
* Approve and Reject buttons restricted to configured approvers
* Mandatory rejection reason captured through a wizard
* Approval tracking: Approved/Rejected By + Date/Time + Remarks
* GRN cannot be validated unless it is in the Approved state
* Configurable approvers per workflow action (submit / approve / reject)
* Configurable email recipients per workflow action
* Configurable email templates with dynamic placeholders
* Fallback to a default approver group when no configuration is found
* Configuration restricted to admin / system configuration users
""",
    'author': 'Centrics Business Solutions PVT Ltd',
    'company': 'Centrics Business Solutions PVT Ltd',
    'website': 'http://www.centrics.cloud/',
    'category': 'Inventory/Inventory',
    'depends': ['stock', 'purchase_stock', 'mail'],
    'data': [
        'security/grn_approval_security.xml',
        'security/ir.model.access.csv',
        'data/mail_templates.xml',
        'views/grn_approval_config_views.xml',
        'wizard/grn_reject_wizard_views.xml',
        'wizard/grn_submit_wizard_views.xml',
        'views/stock_picking_views.xml',
        'views/menu_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}

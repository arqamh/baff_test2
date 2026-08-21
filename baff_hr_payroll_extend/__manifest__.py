# -*- coding: utf-8 -*-
{
    'name': 'Ocean Voyager Payroll Extensions',
    'version': '18.0.1.0.9',
    'summary': 'Client-specific compact salary rules & structure (Ocean Voyager).',
    'description': 'Adds the "Ocean Voyager Salary Structure" and salary rules including OT (hours & amounts), allowances, deductions, EPF (8%/3%/12%), PAYE hook, and Net salary. Includes simple OT rate fields on contracts.',
    'category': 'Human Resources/Payroll',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'http://www.centrics.cloud/',
    'depends': ['hr', 'hr_contract', 'hr_payroll', 'baff_hr_extend', 'baff_hr_overtime_extend', 'centrics_hr_allowance_deduction', 'centrics_hr_loan_management', 'centrics_hr_payroll', 'centrics_hr_payroll_no_default_rules', 'material_purchase_requisitions'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payslip_input_types.xml',
        'data/hr_salary_structure_data.xml',
        "reports/baff_payslip_report.xml",
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_salary_sheet_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}

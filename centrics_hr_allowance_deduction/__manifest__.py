{
    'name': 'Employee Fixed Allowwances And Deductions',
    'version': '16.0.1.0.0',
    'sequence': 2,
    'category': 'Human Resources/Payroll',
    'license': 'OPL-1',
    'author': "Centrics Business Solutions (Pvt) Ltd",
    'website': 'https://www.centrics.lk',
    'summary': 'Manage Employee Fixed Deductions and Fixed Allowances',
    'description': """
    1. Allow the user to enable and disable Fixed Allowances and Fixed Deductions
    2. Allow the user to add Fixed Allowance and Fixed Deduction Types
    3. Allow the user to add Fixed Allowance and Fixed Deduction Amounts
    4. Configure the Fixed Allowances and Fixed Deductions in the Employee Contracts
    5. Capture these Fixed Allowances and Fixed Deductions in the Employee Pay Slip
    
    """,
    'depends': [
        'base',
        'hr',
        'centrics_hr',
        'hr_payroll'
    ],
    'data': [
        'security/centrics_hr_allowance_deduction_groups.xml',
        'security/ir.model.access.csv',
        'views/hr_payslip_input_type_views.xml',
        'views/fixed_allowance_deduction_views.xml',
        'views/hr_contract_views.xml',
        'views/fixed_allowance_deduction_template_views.xml',
        'data/hr_employee_allowance_deduction_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

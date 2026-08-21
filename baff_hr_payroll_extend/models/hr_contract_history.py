from odoo import api, fields, models, tools, _


class HrContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # Reference contract is the one with the latest start_date.
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (
            WITH contract_information AS (
                SELECT DISTINCT employee_id,
                                company_id,
                                FIRST_VALUE(id) OVER w_partition AS id,
                                MAX(CASE
                                    WHEN state='open' THEN 1
                                    WHEN state='draft' AND kanban_state='done' THEN 1
                                    ELSE 0 END) OVER w_partition AS is_under_contract
                FROM   hr_contract AS contract
                WHERE  contract.active = true
                WINDOW w_partition AS (
                    PARTITION BY contract.employee_id, contract.company_id
                    ORDER BY
                        CASE
                            WHEN contract.state = 'open' THEN 0
                            WHEN contract.state = 'draft' THEN 1
                            WHEN contract.state = 'close' THEN 2
                            WHEN contract.state = 'cancel' THEN 3
                            ELSE 4 END,
                        contract.date_start DESC
                    RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                )
            )
            SELECT DISTINCT employee.id AS id,
                            employee.id AS employee_id,
                            employee.active AS active_employee,
                            contract.id AS contract_id,
                            contract_information.is_under_contract::bool AS is_under_contract,
                            employee.first_contract_date AS date_hired,
                            %s
            FROM       hr_contract AS contract
            INNER JOIN contract_information ON contract.id = contract_information.id
            RIGHT JOIN hr_employee AS employee
                ON  contract_information.employee_id = employee.id
                AND contract.company_id = employee.company_id
            WHERE   employee.employee_type IN ('employee', 
            'student', 
            'trainee',
            'contractor',
            'staff',
            'shop_floor')
        )""" % (self._table, self._get_fields()))
from odoo import models, _
from odoo.exceptions import UserError


class JobCosting(models.Model):
    _inherit = 'job.costing'

    def action_add_lines(self):
        """ Replace the invoiceable lines this sheet created on its quotation with one line per
        Materials row ticked 'Is Included In Report' (normally the child BOMs), plus one line per
        main parent for the cost of its rows that are not ticked, priced as:

            A = Material cost of the row (leaf materials of its subtree)
            B = Labour cost of the row (labour lines of its subtree)
            C = Overhead tab total / total A of all invoiced rows x A
            D = A + B + C
            E = D x Gross Profit % Markup
            F = (D + E) / (100 - Sale Commission %) x Sale Commission %
            G = D + E + F, converted with the Currency Rate when the customer currency differs

        The vendor method is not called: it billed bare cost, skipped labour and markup and
        wiped every invoiceable line of the quotation.
        """
        for job_costing in self:
            job_costing._update_invoiceable_lines()

    def _get_invoiceable_components(self):
        """ Rows that can become invoiceable lines, in sheet order: the ticked rows, plus every
        main parent row, which takes the cost of its rows that are not ticked """
        self.ensure_one()
        components = self.job_cost_line_ids.filtered(
            lambda line: line.is_include_report or line.material_type == 'parent')
        if not components:
            raise UserError(_("Job Costing Sheet %s has no Materials line to invoice.") % self.display_name)
        return components.sorted(lambda line: (line.material_index or '', line.sequence, line.id))

    def _get_component_owner(self, line, index, header_components, check_index=True):
        """ Deepest header row (parent / BOM) whose subtree contains the line. The index tells apart
        rows with the same path; when rows were renumbered and no index matches, the path decides. """
        owner = self.env['job.cost.line']
        for component in header_components:
            if not component.component:
                continue
            if line.component != component.component \
                    and not line.component.startswith('%s/' % component.component):
                continue
            if check_index and index and component.material_index \
                    and not index.startswith(component.material_index):
                continue
            if not owner or (len(component.component), len(component.material_index or '')) > \
                    (len(owner.component), len(owner.material_index or '')):
                owner = component
        return owner

    def _compute_invoiceable_costs(self, components):
        """ Material (A) and Labour (B) cost of each row, in sheet currency. A cost line goes to the
        deepest row above it, so the cost of rows that are not ticked stays on their main parent. """
        self.ensure_one()
        costs = {component.id: {'material': 0.0, 'labour': 0.0} for component in components}
        header_components = components.filtered(lambda line: line.material_type in ('parent', 'bom'))
        for component in components - header_components:
            costs[component.id]['material'] = component.total_cost

        # Same leaf rows as the sheet's Material total
        leaf_materials = self.job_cost_line_ids.filtered(
            lambda line: line.material_type == 'component' and line.component) - components
        for line in leaf_materials:
            owner = self._get_component_owner(line, line.material_index, header_components) \
                or self._get_component_owner(line, line.material_index, header_components, check_index=False)
            if owner:
                costs[owner.id]['material'] += line.total_cost
        for line in self.job_labour_line_ids.filtered('component'):
            owner = self._get_component_owner(line, line.labour_index, header_components) \
                or self._get_component_owner(line, line.labour_index, header_components, check_index=False)
            if owner:
                costs[owner.id]['labour'] += line.total_cost
        return costs

    def _to_customer_currency(self, amount):
        self.ensure_one()
        if not self.customer_currency_id or self.currency_id == self.customer_currency_id:
            return amount
        if self.currency_rate <= 0:
            raise UserError(_("Set the Currency Rate of Job Costing Sheet %s to convert its prices to %s.")
                            % (self.display_name, self.customer_currency_id.name))
        return amount / self.currency_rate

    def _prepare_invoiceable_line_values(self):
        """ One line value dict per invoiced row, amounts in customer currency """
        self.ensure_one()
        commission_percentage = self.profit_margin_percentage
        if commission_percentage >= 100:
            raise UserError(_("The Sale Commission, After Sales Service and Design Royalties of Job Costing "
                              "Sheet %s must be below 100%%.") % self.display_name)
        components = self._get_invoiceable_components()
        costs = self._compute_invoiceable_costs(components)
        # A parent that is not ticked is only invoiced when it has cost left
        components = components.filtered(
            lambda line: line.is_include_report or costs[line.id]['material'] or costs[line.id]['labour'])
        if not components:
            raise UserError(_("Job Costing Sheet %s has no cost to invoice.") % self.display_name)
        total_material = sum(costs[component.id]['material'] for component in components)
        if self.overhead_total and not total_material:
            raise UserError(_("The Overhead of Job Costing Sheet %s cannot be allocated: the invoiced lines "
                              "have no Material cost.") % self.display_name)

        customer_currency = self.customer_currency_id or self.currency_id
        amounts = []
        for component in components:
            material = costs[component.id]['material']
            labour = costs[component.id]['labour']
            overhead = self.overhead_total * material / total_material if total_material else 0.0
            total_cost = material + labour + overhead
            profit = total_cost * self.gross_profit_markup / 100
            commission = (total_cost + profit) * commission_percentage / (100 - commission_percentage)
            amounts.append(self._to_customer_currency(total_cost + profit + commission))

        # Round each line and let the last one absorb the rounding difference
        rounded_amounts = [customer_currency.round(amount) for amount in amounts]
        rounded_amounts[-1] = customer_currency.round(sum(amounts) - sum(rounded_amounts[:-1]))

        values = []
        for sequence, (component, amount) in enumerate(zip(components, rounded_amounts), start=1):
            quantity = component.product_qty or 1.0
            values.append({
                'sequence': sequence,
                'product_id': component.product_id.id,
                'product_uom_qty': quantity,
                'product_uom': component.uom_id.id,
                'price_unit': amount / quantity,
                'name': component.component if component.material_type in ('parent', 'bom') and component.component
                else component.product_id.display_name,
                'category': 'product',
                'job_costing_id': self.id,
                'so_order_id': self.quotation_id.sale_id.id,
            })
        return values

    def _get_replaced_invoiceable_lines(self):
        """ Lines this sheet created before, plus untagged lines left by the old button """
        self.ensure_one()
        cost_lines = self.job_cost_line_ids | self.job_overhead_line_ids
        legacy_names = set(cost_lines.filtered('component').mapped('component')) \
            | set(cost_lines.product_id.mapped('name')) | set(cost_lines.product_id.mapped('display_name'))
        return self.quotation_id.invoiceable_line.filtered(
            lambda line: line.job_costing_id == self
            or (not line.job_costing_id and not line.category and not line.display_type
                and line.product_id in cost_lines.product_id and line.name in legacy_names))

    def _update_invoiceable_lines(self):
        self.ensure_one()
        if not self.quotation_id:
            raise UserError(_("Link a Quotation to Job Costing Sheet %s before adding invoiceable lines.")
                            % self.display_name)
        values = self._prepare_invoiceable_line_values()
        commands = [(2, line.id) for line in self._get_replaced_invoiceable_lines()]
        commands += [(0, 0, vals) for vals in values]
        self.quotation_id.write({'invoiceable_line': commands})

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round

# Sheet states between the Sales Order creation and the production approval (done)
INVOICEABLE_LINE_STATES = ('ready_for_production', 'waiting_production_approval')


class JobCosting(models.Model):
    _inherit = 'job.costing'

    can_add_invoiceable_lines = fields.Boolean(compute='_compute_can_add_invoiceable_lines')

    @api.depends('state', 'quotation_id.sale_id')
    def _compute_can_add_invoiceable_lines(self):
        """ Invoiceable lines can be added once the Sales Order is created, until the sheet is done """
        for job_costing in self:
            job_costing.can_add_invoiceable_lines = bool(
                job_costing.quotation_id.sale_id and job_costing.state in INVOICEABLE_LINE_STATES)

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
            job_costing._check_can_add_invoiceable_lines()
            job_costing._update_invoiceable_lines()

    def update_sales_price(self):
        """ The approval keeps updating the Sales Order line prices, but its invoiceable lines (one per
        finished good plus Labor and Overhead lines, which counted Labor and Overhead twice) are
        replaced with the same lines as the 'Add Invoiceable Lines' button """
        result = super().update_sales_price()
        for job_costing in self.filtered('quotation_id'):
            job_costing._update_invoiceable_lines()
        return result

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

    def _get_invoiceable_line_name(self, component):
        """ Component path for a parent / BOM row, Raw Material name otherwise """
        if component.material_type in ('parent', 'bom') and component.component:
            return component.component
        return component.product_id.display_name or ''

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
        # A row without description (no Raw Material, no Component) is skipped when it has no cost
        unnamed = components.filtered(lambda line: not self._get_invoiceable_line_name(line))
        unnamed_with_cost = unnamed.filtered(lambda line: costs[line.id]['material'] or costs[line.id]['labour'])
        if unnamed_with_cost:
            raise UserError(_("Set a Raw Material on line(s) %s of Job Costing Sheet %s, or untick "
                              "'Is Included In Report'.")
                            % (', '.join(unnamed_with_cost.mapped(lambda line: line.material_index or str(line.id))),
                               self.display_name))
        components -= unnamed
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

        # Bring the lines to the Sales Order total, so the quotation approval check
        # (Total Quotation Amount = Total Amount) passes: cost the rows do not reach is spread
        # over the lines and the rounding difference goes to a line of quantity 1 (else the last)
        target_total = self._get_invoiceable_target_total()
        if target_total is None:
            target_total = customer_currency.round(sum(amounts))
        factor = target_total / sum(amounts) if sum(amounts) else 1.0
        price_digits = self.env['decimal.precision'].precision_get('Product Price')
        quantities = [component.product_qty or 1.0 for component in components]
        price_units = [float_round(amount * factor / quantity, precision_digits=price_digits)
                       for amount, quantity in zip(amounts, quantities)]
        subtotals = [customer_currency.round(quantity * price_unit)
                     for quantity, price_unit in zip(quantities, price_units)]
        residue = customer_currency.round(target_total - sum(subtotals))
        if residue:
            absorber = next((index for index in reversed(range(len(quantities))) if quantities[index] == 1.0),
                            len(quantities) - 1)
            price_units[absorber] = float_round((subtotals[absorber] + residue) / quantities[absorber],
                                                precision_digits=price_digits)

        values = []
        for sequence, (component, quantity, price_unit) in enumerate(zip(components, quantities, price_units),
                                                                     start=1):
            values.append({
                'sequence': sequence,
                'product_id': component.product_id.id,
                'product_uom_qty': quantity,
                'product_uom': component.uom_id.id,
                'price_unit': price_unit,
                'name': self._get_invoiceable_line_name(component),
                'category': 'product',
                'job_costing_id': self.id,
                'so_order_id': self.quotation_id.sale_id.id,
            })
        return values

    def _get_invoiceable_target_total(self):
        """ Sales Order total the approval (update_sales_price) gives the finished goods: Total Price
        split by quantity, unit price rounded like the order line. None without finished goods. """
        self.ensure_one()
        finished_goods = self.finished_good_ids.filtered(lambda finished_good: finished_good.product_id)
        if not finished_goods:
            return None
        customer_currency = self.customer_currency_id or self.currency_id
        price_digits = self.env['decimal.precision'].precision_get('Product Price')
        total_qty = sum(finished_goods.mapped('product_qty')) or 1.0
        total_price = self._to_customer_currency(self.jobcost_total)
        target_total = 0.0
        for finished_good in finished_goods.filtered('product_qty'):
            share = total_price * finished_good.product_qty / total_qty
            unit_price = float_round(share / finished_good.product_qty, precision_digits=price_digits)
            target_total += customer_currency.round(finished_good.product_qty * unit_price)
        return customer_currency.round(target_total)

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

    def _check_can_add_invoiceable_lines(self):
        """ The button works once the Sales Order is created, until the sheet is done """
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("Job Costing Sheet %s is Done: its invoiceable lines can no longer be changed.")
                            % self.display_name)
        if not self.quotation_id.sale_id:
            raise UserError(_("Create the Sales Order of Job Costing Sheet %s before adding invoiceable lines.")
                            % self.display_name)
        if not self.can_add_invoiceable_lines:
            state = dict(self._fields['state']._description_selection(self.env)).get(self.state)
            raise UserError(_("Invoiceable lines of Job Costing Sheet %s cannot be added in state %s.")
                            % (self.display_name, state))

    def _update_invoiceable_lines(self):
        self.ensure_one()
        if not self.quotation_id:
            raise UserError(_("Link a Quotation to Job Costing Sheet %s before adding invoiceable lines.")
                            % self.display_name)
        values = self._prepare_invoiceable_line_values()
        commands = [(2, line.id) for line in self._get_replaced_invoiceable_lines()]
        commands += [(0, 0, vals) for vals in values]
        self.quotation_id.write({'invoiceable_line': commands})

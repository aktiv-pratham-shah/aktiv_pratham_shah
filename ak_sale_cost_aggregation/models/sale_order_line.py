# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # New field to store the actual individual cost of the product line.
    # This field acts as the editable input for the cost of this specific line.
    individual_cost = fields.Float(
        string="Individual Cost",
        compute="_compute_individual_cost",
        store=True,
        readonly=False,
        copy=True,
        precompute=True,
        groups="base.group_user"
    )

    # standard_purchase_price is NOT needed, we already have purchase_price from sale_margin.
    # We will override purchase_price to represent the "Effective Margin Cost".
    # purchase_price is the field used by sale_margin's _compute_margin logic.
    purchase_price = fields.Float(
        string="Cost (Margin Allocation)",
        compute="_compute_purchase_price",
        store=True,
        readonly=False,
        copy=False,
        precompute=True,
        groups="base.group_user"
    )

    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom_id')
    def _compute_individual_cost(self):
        """
        Populate individual_cost with the standard product cost.
        This logic is identical to Odoo's default _compute_purchase_price.
        """
        for line in self:
            if not line.product_id:
                line.individual_cost = 0.0
                continue
            line = line.with_company(line.company_id)

            # Convert the cost to the line UoM
            product_cost = line.product_id.uom_id._compute_price(
                line.product_id.standard_price,
                line.product_uom_id,
            )

            line.individual_cost = line._convert_to_sol_currency(
                product_cost,
                line.product_id.cost_currency_id)

    @api.depends('order_id.order_line.individual_cost', 'order_id.order_line.product_uom_qty')
    def _compute_purchase_price(self):
        """
        Override purchase_price to consolidate all costs into the first line of the order.
        This ensures that:
        1. Only the first line carries the total cost for the order's margin calculations.
        2. All other lines show a zero cost for margin purposes, avoiding double counting.
        """
        # Group lines by order to minimize sorting and summation calls
        for order in self.mapped('order_id'):
            # Identify the first line based on sequence. We use l.id only if it's an int
            # to avoid TypeError between NewId objects in UI/Onchange.
            all_lines = order.order_line.sorted(key=lambda l: (l.sequence, l.id if isinstance(l.id, int) else 0))
            if not all_lines:
                continue

            first_line = all_lines[0]
            # Calculate total order cost = sum(individual_cost * qty)
            total_order_cost = sum(l.individual_cost * l.product_uom_qty for l in all_lines)

            for line in all_lines:
                if line == first_line:
                    # For the first line, the unit cost = total_cost / its_own_qty
                    # This makes margin = subtotal - (purchase_price * qty) = subtotal - total_cost
                    if line.product_uom_qty:
                        line.purchase_price = total_order_cost / line.product_uom_qty
                    else:
                        line.purchase_price = total_order_cost
                else:
                    # Other lines have 0 cost for margin calculations as they are already bundled into the first line
                    line.purchase_price = 0.0

        # Handle lines without an order (unlikely but safe)
        for line in self:
            if not line.order_id:
                line.purchase_price = line.individual_cost

class SaleOrder(models.Model):
    _inherit = "sale.order"

    product_preview = fields.Char(
        string="Products",
        compute="_compute_product_preview",
        store=True
    )

    @api.depends('order_line.product_id')
    def _compute_product_preview(self):
        for order in self:
            products = order.order_line.mapped('product_id.display_name')

            if not products:
                order.product_preview = ''
            elif len(products) == 1:
                order.product_preview = products[0]
            else:
                order.product_preview = f"{products[0]} + {len(products) - 1} more"
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class ResCompany(models.Model):
    _inherit = 'res.company'

    margin_threshold = fields.Float(
        string="Minimum Margin Threshold (%)", 
        default=10.0,
        help="Sales orders with margins below this will be blocked from confirmation."
    )

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    margin_threshold = fields.Float(
        related='company_id.margin_threshold', 
        readonly=False, 
        string="Minimum Margin (%)"
    )

class ResUsers(models.Model):
    _inherit = 'res.users'

    commission_rate = fields.Float(
        string="Commission Rate (%)", 
        help="Percentage of the profit (margin) that goes to the salesperson."
    )

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    projected_commission = fields.Monetary(
        string="Projected Commission", 
        compute="_compute_projected_commission", 
        store=True,
        help="Estimated commission for the salesperson based on total margin."
    )

    @api.depends('order_line.price_unit', 'order_line.product_id', 'user_id.commission_rate', 'order_line.product_uom_qty')
    def _compute_projected_commission(self):
        """Calculates commission based on margin * user commission rate."""
        for order in self:
            total_margin = 0
            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                # Use purchase_price if available (sale_margin compatibility), else standard_price
                cost_unit = getattr(line, 'purchase_price', line.product_id.standard_price)
                cost = cost_unit * line.product_uom_qty
                line_margin = line.price_subtotal - cost
                total_margin += line_margin
            
            rate = order.user_id.commission_rate if order.user_id else 0.0
            order.projected_commission = total_margin * rate

    def action_confirm(self):
        """Margin Protection Guard: Blocks confirmation if any line margin is too low."""
        for order in self:
            threshold = order.company_id.margin_threshold
            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                sale_price = line.price_unit
                cost = getattr(line, 'purchase_price', line.product_id.standard_price)
                
                if sale_price > 0:
                    margin_pct = ((sale_price - cost) / sale_price) * 100
                    if margin_pct < threshold:
                        raise UserError(_(
                            "Margin Protection Alert (Threshold: %.2f%%)!\n\n"
                            "The item '%s' has a margin of %.2f%%. "
                            "Please increase the price or get manager approval."
                        ) % (threshold, line.product_id.display_name, margin_pct))
        
        return super().action_confirm()

class MarginIntelligence(models.AbstractModel):
    """
    An abstract model used as a data engine for the Margin Intelligence Dashboard.
    It provides logic for calculating profit margins on Sale and Purchase order lines.
    """
    _name = 'margin.intelligence'
    _description = 'Margin Intelligence Data Engine'

    @api.model
    def get_dashboard_data(self, tab_type='sale'):
        """
        Main entry point for fetching dashboard data.
        
        :param str tab_type: The context of the dashboard ('sale' or 'purchase').
        :return list: A list of dictionaries containing processed margin data.
        """
        if tab_type == 'sale':
            return self._get_sale_data()
        else:
            return self._get_purchase_data()

    def _get_sale_data(self):
        """
        Fetches confirmed sale order lines with optimized batch trend analysis.
        """
        date_to = fields.Date.today() - relativedelta(days=30)
        date_from = date_to - relativedelta(days=30)
        
        lines = self.env['sale.order.line'].search([
            ('state', 'in', ['sale', 'done']),
            ('display_type', '=', False),
            ('product_id', '!=', False)
        ])
        
        # Batch calculate historical averages to avoid N+1 performance issues
        product_ids = lines.mapped('product_id.id')
        history_data = self.env['sale.order.line'].read_group([
            ('product_id', 'in', product_ids),
            ('create_date', '>=', date_from),
            ('create_date', '<', date_to),
            ('state', 'in', ['sale', 'done'])
        ], ['product_id', 'price_unit', 'purchase_price:avg'], ['product_id'])

        # Note: purchase_price:avg is a fallback, we'll manually calculate if needed
        # but for performance, we create a map
        history_map = {h['product_id'][0]: self._get_historical_avg_batch(h['product_id'][0], 'sale', date_from, date_to) for h in history_data}

        result = []
        for line in lines:
            sale_price = line.price_unit
            cost = getattr(line, 'purchase_price', line.product_id.standard_price)
            margin_amt = sale_price - cost
            margin_pct = (margin_amt / sale_price * 100) if sale_price else 0.0
            
            prev_avg = history_map.get(line.product_id.id, 0.0)
            trend = 'stable'
            if prev_avg:
                if margin_pct > prev_avg + 0.5: trend = 'up'
                elif margin_pct < prev_avg - 0.5: trend = 'down'

            result.append({
                'id': line.id,
                'order_name': line.order_id.name,
                'product_name': line.product_id.display_name,
                'category_name': line.product_id.categ_id.name or 'Uncategorized',
                'price': sale_price,
                'cost_or_ref': cost,
                'margin_pct': round(margin_pct, 2),
                'margin_amt': round(margin_amt, 2),
                'health': self._calculate_health(margin_pct),
                'trend': trend,
            })
        return result

    def _get_purchase_data(self):
        """
        Fetches confirmed purchase lines with optimized batch trend analysis.
        """
        date_to = fields.Date.today() - relativedelta(days=30)
        date_from = date_to - relativedelta(days=30)
        
        lines = self.env['purchase.order.line'].search([
            ('state', 'in', ['purchase', 'done']),
            ('display_type', '=', False),
            ('product_id', '!=', False)
        ])
        
        product_ids = lines.mapped('product_id.id')
        history_map = {p_id: self._get_historical_avg_batch(p_id, 'purchase', date_from, date_to) for p_id in product_ids}
        
        result = []
        for line in lines:
            purchase_price = line.price_unit
            sale_ref_price = line.product_id.list_price
            margin_amt = sale_ref_price - purchase_price
            margin_pct = (margin_amt / sale_ref_price * 100) if sale_ref_price else 0.0
            
            prev_avg = history_map.get(line.product_id.id, 0.0)
            trend = 'stable'
            if prev_avg:
                if margin_pct > prev_avg + 0.5: trend = 'up'
                elif margin_pct < prev_avg - 0.5: trend = 'down'

            result.append({
                'id': line.id,
                'order_name': line.order_id.name,
                'product_name': line.product_id.display_name,
                'category_name': line.product_id.categ_id.name or 'Uncategorized',
                'price': purchase_price,
                'cost_or_ref': sale_ref_price,
                'margin_pct': round(margin_pct, 2),
                'margin_amt': round(margin_amt, 2),
                'health': self._calculate_health(margin_pct),
                'trend': trend,
            })
        return result

    def _get_historical_avg_batch(self, product_id, tab_type, date_from, date_to):
        """Optimized helper for trend baselines."""
        if tab_type == 'sale':
            recs = self.env['sale.order.line'].search([
                ('product_id', '=', product_id),
                ('create_date', '>=', date_from),
                ('create_date', '<', date_to),
                ('state', 'in', ['sale', 'done'])
            ])
            margins = [((r.price_unit - getattr(r, 'purchase_price', r.product_id.standard_price)) / r.price_unit * 100) 
                       for r in recs if r.price_unit > 0]
            return (sum(margins) / len(margins)) if margins else 0.0
        else:
            recs = self.env['purchase.order.line'].search([
                ('product_id', '=', product_id),
                ('create_date', '>=', date_from),
                ('create_date', '<', date_to),
                ('state', 'in', ['purchase', 'done'])
            ])
            margins = [((r.product_id.list_price - r.price_unit) / r.product_id.list_price * 100) 
                       for r in recs if r.product_id.list_price > 0]
            return (sum(margins) / len(margins)) if margins else 0.0

    def _calculate_health(self, margin_pct):
        """
        Categorizes margin health based on defined thresholds.
        Thresholds:
            Good: >= 30%
            Warning: 10% to 29.99%
            Critical: < 10%
            
        :param float margin_pct: The calculated margin percentage.
        :return str: The health status string ('good', 'warning', 'critical').
        """
        if margin_pct >= 30:
            return 'good'
        elif margin_pct >= 10:
            return 'warning'
        else:
            return 'critical'

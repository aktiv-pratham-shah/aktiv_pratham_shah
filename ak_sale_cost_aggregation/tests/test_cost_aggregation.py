# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestCostAggregation(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestCostAggregation, cls).setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer'})
        cls.product_a = cls.env['product.product'].create({
            'name': 'Service A',
            'standard_price': 50.0,
            'list_price': 1000.0,
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'Component B',
            'standard_price': 200.0,
            'list_price': 0.0,
        })
        cls.product_c = cls.env['product.product'].create({
            'name': 'Component C',
            'standard_price': 300.0,
            'list_price': 0.0,
        })

    def test_01_cost_consolidation(self):
        """Test that costs are consolidated into the first line."""
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        
        # Add Product A (Line 1)
        line_a = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_a.id,
            'product_uom_qty': 1,
            'individual_cost': 50.0,
            'sequence': 10,
        })
        # Add Product B (Line 2)
        line_b = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_b.id,
            'product_uom_qty': 1,
            'individual_cost': 200.0,
            'sequence': 20,
        })

        # Line 1 should have consolidated cost: 50 + 200 = 250
        self.assertEqual(line_a.purchase_price, 250.0, "Line 1 should contain total cost")
        self.assertEqual(line_b.purchase_price, 0.0, "Line 2 should have zero cost for margin")
        self.assertEqual(order.margin, 750.0, "Total margin should be 1000 - 250 = 750")

    def test_02_reorder_recomputation(self):
        """Test that reordering lines shifts the cost anchor."""
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line_a = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_a.id,
            'individual_cost': 100.0,
            'sequence': 10,
        })
        line_b = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product_b.id,
            'individual_cost': 200.0,
            'sequence': 20,
        })

        # Move Line B to top
        line_b.write({'sequence': 5})
        
        # Now Line B should be the "First Line"
        self.assertEqual(line_b.purchase_price, 300.0, "New top line should have total cost")
        self.assertEqual(line_a.purchase_price, 0.0, "Previous top line should now be zero")

# models/sale_order_line.py
from odoo import fields, models, api

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    belement_image = fields.Binary(
        string="Image",
        attachment=True,
        help="Image specific to Belement company",
    )

    belement_description = fields.Text(
        string="Belement Description",
        help="Custom description for Belement reports"
    )

    # Ticket : HT01791
    report_row_number = fields.Integer(
        string="Report Row #",
        compute="_compute_report_row_number",
        store=False,
        compute_sudo=True,
        help="1-based row number for PDF/print reports."
    )

    # Ticket : HT01791
    @api.depends('order_id', 'order_id.order_line', 'order_id.order_line.sequence')
    def _compute_report_row_number(self):
        """
        Assign 1..N per order using the recordset's natural order (sequence fallback).
        Works even when lines are unsaved (NewId objects).
        """
        for order in self.mapped('order_id'):
            # Ensure a predictable order: sort by sequence only
            ordered_lines = order.order_line.sorted(lambda l: l.sequence or 0)
            for idx, line in enumerate(ordered_lines, start=1):
                line.report_row_number = idx

    @api.depends('order_id', 'order_id.order_line', 'order_id.order_line.sequence', 'order_id.order_line.display_type')
    def _compute_report_row_number(self):
        """
        Assign row numbers only to product lines.
        Notes and sections are ignored and do not affect numbering.
        """
        for order in self.mapped('order_id'):
            # Sort all lines by sequence
            ordered_lines = order.order_line.sorted(lambda l: l.sequence or 0)

            row_number = 0
            for line in ordered_lines:
                # Reset number for non-product lines
                if line.display_type:
                    line.report_row_number = False
                    continue

                # Count only product lines
                row_number += 1
                line.report_row_number = row_number

    @api.model_create_multi
    def create(self, vals):
        """Ensure belement_image is populated when product is selected from Catalog for company 1."""
        lines = super().create(vals)
        for line in lines:
            if (
                    line.order_id.company_id.id == 1
                    and not line.belement_image
                    and line.product_id
                    and line.product_id.image_1920
            ):
                line.belement_image = line.product_id.image_1920
        return lines


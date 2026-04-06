# -*- coding: utf-8 -*-

import logging
from odoo import models, api, fields
from markupsafe import Markup

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    """
    Extends the standard User system in Odoo to add a background automated job (cron job).
    This job automatically gathers all unpaid invoices for each salesperson's customers
    and emails them a clean summary table every Monday.
    """
    _inherit = 'res.users'

    @api.model
    def _cron_send_weekly_due_invoices(self):
        """
        Automated Job: 
        1. Finds all validated invoices that are not fully paid.
        2. Groups these invoices by the respective Salesperson.
        3. Generates a readable email containing a list of these invoices.
        4. Sends the email specifically to each Salesperson.
        """
        # Find all relevant invoices
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('company_id', 'in', self.env.companies.ids)
        ])
        
        inr_currency = self.env.ref('base.INR', raise_if_not_found=False)

        # Build Director's Master Table structure
        director_table_html = """
        <table style="width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px;">
            <thead style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6; color: #495057;">
                <tr>
                    <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Salesperson</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Customer</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Company</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Reference</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Due Days</th>
                    <th style="padding: 10px; text-align: right; border: 1px solid #dee2e6; white-space: nowrap;">Amount Due</th>
                    <th style="padding: 10px; text-align: right; border: 1px solid #dee2e6; white-space: nowrap;">Amount (INR)</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # Sort invoices for Directors globally. Filter only those that have ANY salesperson.
        invoices_with_salesperson = invoices.filtered(lambda i: i.partner_id.user_id or i.invoice_user_id)
        global_invoices = invoices_with_salesperson.sorted(key=lambda i: (
            (i.partner_id.user_id.name or i.invoice_user_id.name or ''), 
            i.company_id.name or '', 
            i.partner_id.name or '', 
            i.invoice_date_due or ''
        ))
        
        total_amount_inr_director = 0.0
        for inv in global_invoices:
            salesperson_name = inv.partner_id.user_id.name or inv.invoice_user_id.name or 'No Salesperson'
            # Calculate INR Amount
            amount_inr = 0.0
            if inr_currency and inv.currency_id != inr_currency:
                date = inv.invoice_date or fields.Date.today()
                amount_inr = inv.currency_id._convert(
                    inv.amount_residual, inr_currency, inv.company_id, date
                )
            else:
                amount_inr = inv.amount_residual

            amount_formatted = f"""{inv.currency_id.symbol or ''} {inv.amount_residual:,.2f}""".strip() if inv.currency_id else f"""{inv.amount_residual:,.2f}"""
            amount_inr_formatted = f"₹ {amount_inr:,.2f}" if inr_currency else ""
            
            director_table_html += f"""
            <tr style="border-bottom: 1px solid #dee2e6;">
                <td style="padding: 8px 10px; border: 1px solid #dee2e6;">{salesperson_name}</td>
                <td style="padding: 8px 10px; border: 1px solid #dee2e6;">{inv.partner_id.name or ''}</td>
                <td style="padding: 8px 10px; border: 1px solid #dee2e6;">{inv.company_id.name or ''}</td>
                <td style="padding: 8px 10px; border: 1px solid #dee2e6;">{inv.name or ''}</td>
                <td style="padding: 8px 10px; border: 1px solid #dee2e6; white-space: nowrap;">{(fields.Date.today() - inv.create_date.date()).days}</td>
                <td style="padding: 8px 10px; border: 1px solid #dee2e6; text-align: right; font-weight: bold; white-space: nowrap;">{amount_formatted}</td>
                <td style="padding: 8px 10px; border: 1px solid #dee2e6; text-align: right; font-weight: bold; white-space: nowrap;">{amount_inr_formatted}</td>
            </tr>
            """
            total_amount_inr_director += amount_inr
        director_table_html += f"""
            </tbody>
            <tfoot>
                <tr style="background-color: #f8f9fa; border-top: 2px solid #dee2e6; font-weight: bold;">
                    <td colspan="6" style="padding: 10px; text-align: right; border: 1px solid #dee2e6;">Grand Total</td>
                    <td style="padding: 10px; text-align: right; border: 1px solid #dee2e6; white-space: nowrap;">₹ {total_amount_inr_director:,.2f}</td>
                </tr>
            </tfoot>
        </table>"""

        # Send to Directors
        director_template = self.env.ref('account_extended.email_template_directors_weekly_due_invoices', raise_if_not_found=False)
        if director_template and global_invoices:
            ctx = {
                'invoices_table': Markup(director_table_html),
                'invoice_count': len(global_invoices),
            }
            # Sending to a central directors email address
            director_template.with_context(ctx).send_mail(
                self.env.user.id,
                force_send=True,
                email_values={'email_to': 'directors@aktivsoftware.com'}
            )

        # Group by salesperson ID for individual emails
        grouped_invoices = {}
        for inv in invoices:
            # Use dedicated customer salesperson, fallback to invoice salesperson
            salesperson = inv.partner_id.user_id or inv.invoice_user_id
            if not salesperson:
                continue
                
            salesperson_id = salesperson.id
            if salesperson_id not in grouped_invoices:
                grouped_invoices[salesperson_id] = self.env['account.move']
            grouped_invoices[salesperson_id] += inv

        template = self.env.ref('account_extended.email_template_salesperson_weekly_due_invoices', raise_if_not_found=False)
        if not template:
            return

        for salesperson_id, invs in grouped_invoices.items():
            salesperson = self.env['res.users'].browse(salesperson_id)
            email_to = salesperson.email or salesperson.partner_id.email
            if not email_to:
                continue

            # Generate HTML Table for individual salesperson
            table_html = """
            <table style="width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px;">
                <thead style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6; color: #495057;">
                    <tr>
                        <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Customer</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Company</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Invoice Date</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Due Days</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Reference</th>
                        <th style="padding: 10px; text-align: right; border: 1px solid #dee2e6; white-space: nowrap;">Amount Due</th>
                        <th style="padding: 10px; text-align: right; border: 1px solid #dee2e6; white-space: nowrap;">Amount (INR)</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            total_amount_inr_salesperson = 0.0
            # Sort invoices by company, then customer name, then due date
            sorted_invs = invs.sorted(key=lambda i: (i.company_id.name or '', i.partner_id.name or '', i.invoice_date_due or ''))
            
            for inv in sorted_invs:
                amount_inr = 0.0
                if inr_currency and inv.currency_id != inr_currency:
                    date = inv.invoice_date or fields.Date.today()
                    amount_inr = inv.currency_id._convert(
                        inv.amount_residual, inr_currency, inv.company_id, date
                    )
                else:
                    amount_inr = inv.amount_residual
                    
                amount_formatted = f"""{inv.currency_id.symbol or ''} {inv.amount_residual:,.2f}""".strip() if inv.currency_id else f"""{inv.amount_residual:,.2f}"""
                amount_inr_formatted = f"₹ {amount_inr:,.2f}" if inr_currency else ""
                
                table_html += f"""
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6;">{inv.partner_id.name or ''}</td>
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6;">{inv.company_id.name or ''}</td>
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6; white-space: nowrap;">{inv.invoice_date.strftime('%m/%d/%Y') if inv.invoice_date else ''}</td>
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6; white-space: nowrap;">{(fields.Date.today() - inv.create_date.date()).days}</td>
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6;">{inv.name or ''}</td>
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6; text-align: right; font-weight: bold; white-space: nowrap;">{amount_formatted}</td>
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6; text-align: right; font-weight: bold; white-space: nowrap;">{amount_inr_formatted}</td>
                </tr>
                """
                total_amount_inr_salesperson += amount_inr
            
            table_html += f"""
                </tbody>
                <tfoot>
                    <tr style="background-color: #f8f9fa; border-top: 2px solid #dee2e6; font-weight: bold;">
                        <td colspan="6" style="padding: 10px; text-align: right; border: 1px solid #dee2e6;">Grand Total</td>
                        <td style="padding: 10px; text-align: right; border: 1px solid #dee2e6; white-space: nowrap;">₹ {total_amount_inr_salesperson:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
            """

            # Prepare dynamic context for the template
            ctx = {
                'salesperson_name': salesperson.name,
                'invoices_table': Markup(table_html),
                'invoice_count': len(sorted_invs),
            }
            
            # Send the email using the template
            template.with_context(ctx).send_mail(
                salesperson.id, 
                force_send=True,
                email_values={
                    'email_to': False,
                    'recipient_ids': [(4, salesperson.partner_id.id)]
                }
            )

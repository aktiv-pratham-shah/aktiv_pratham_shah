# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo import models, _
from markupsafe import Markup
import re


class AccountFollowupReport(models.AbstractModel):
    """
    Customizes the visual design of the Follow-up Report that is sent to customers.
    It dynamically inserts a summary table of all unpaid invoices directly into the 
    email body and PDF, ensuring the table automatically adjusts its width and 
    presents a clearly formatted Grand Total with the correct currency symbol.
    """
    _inherit = 'account.followup.report'

    def _get_main_body(self, options):
        """ 
        Automatically injects our custom Unpaid Invoices table into the main message 
        body of the follow-up email before it goes out to the customer.
        """
        body = super()._get_main_body(options)

        if not body:
            return body

        # Prevent duplicate tables
        if 'id="followup_invoices_table"' in str(body):
            return body

        # Generate the dynamic HTML table from PDF data
        table_html = self._generate_followup_table_html(options)

        # Inject into the body dynamically and wrap in Markup
        new_body = self._inject_html_dynamically(body, table_html)
        return Markup(new_body)

    def _generate_followup_table_html(self, options):
        """ 
        Builds the visual physical HTML code for the table (columns for Date, Due Date, Reference, Amount). 
        It cleanly formats the borders, alignments, and adds up the total at the bottom.
        """
        lines = self._get_followup_report_lines(options)

        table_html = """
        <div id="followup_invoices_table" style="margin: 20px 0; display: block; width: 100%; max-width: 100%; border: 1px solid #dee2e6; border-radius: 4px; overflow: hidden;">
            <table style="width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px;">
                <thead style="background-color: #f8f9fa; border-bottom: 2px solid #dee2e6; color: #495057;">
                    <tr>
                        <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Date</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Due Date</th>
                        <th style="padding: 10px; text-align: left; border: 1px solid #dee2e6; white-space: nowrap;">Reference</th>
                        <th style="padding: 10px; text-align: right; border: 1px solid #dee2e6; white-space: nowrap;">Amount</th>
                    </tr>
                </thead>
                <tbody>
        """
        total_amount = 0.0
        total_formatted = ''
        for line in lines:
            # Skip summary/total lines
            if line.get('class') == 'total' or not line.get('columns'):
                continue

            cols = line.get('columns', [])
            if len(cols) < 5:
                continue

            # KEY FIX: Skip grouping lines (like "Overdue" or "Due") which have empty names in the first column
            if not cols[0].get('name'):
                continue

            # Accumulate raw amount for total
            amount_col = cols[4]
            raw_val = amount_col.get('no_format', None)
            amount_name = amount_col.get('name', '') or ''
            if not raw_val:
                # Parse numeric value from formatted string like "$ 700.00" or "1,200.00 USD"
                numeric_str = re.sub(r'[^\d.\-]', '', amount_name.replace(',', ''))
                try:
                    raw_val = float(numeric_str) if numeric_str else 0.0
                except ValueError:
                    raw_val = 0.0
            total_amount += raw_val
            total_formatted = amount_name  # keep last for currency symbol detection

            # Use the data mapping consistent with the PDF
            # col[0]: Date, col[1]: Due Date, col[4]: Amount
            table_html += f"""
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6; white-space: nowrap;">{cols[0].get('name', '')}</td>
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6; white-space: nowrap;">{cols[1].get('name', '')}</td>
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6; white-space: nowrap;">{line.get('name', '')}</td>
                    <td style="padding: 8px 10px; border: 1px solid #dee2e6; text-align: right; font-weight: bold; white-space: nowrap;">{amount_col.get('name', '')}</td>
                </tr>
            """

        # Extract currency symbol/code from the last formatted amount for the total display
        # total_formatted is like "1,200.00 USD" or "$ 1,200.00" or "1,200.00 €"
        currency_suffix = ''
        currency_prefix = ''
        if total_formatted:
            # Try to detect trailing currency code or symbol (e.g., " USD" or " €" or "€")
            suffix_match = re.search(r'([^\d.,\-]+)$', total_formatted.strip())
            # Match prefix currency symbol or code (e.g., "$ " or "€ ")
            prefix_match = re.match(r'^([^\d.,\-]+)', total_formatted.strip())

            if suffix_match:
                currency_suffix = '&nbsp;' + suffix_match.group(1).strip()
            if prefix_match:
                currency_prefix = prefix_match.group(1).strip() + '&nbsp;'

        total_display = f'{currency_prefix}{total_amount:,.2f}{currency_suffix}'.strip()

        table_html += f"""
                </tbody>
                <tfoot>
                    <tr style="background-color: #e9ecef; border-top: 2px solid #868e96;">
                        <td colspan="3" style="padding: 10px; border: 1px solid #dee2e6; font-weight: 700; font-size: 14px; text-align: right; color: #212529;">Grand Total</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6; text-align: right; font-weight: 700; font-size: 14px; color: #212529; white-space: nowrap;">{total_display}</td>
                    </tr>
                </tfoot>
            </table></div>"""
        return table_html

    def _inject_html_dynamically(self, body, html_to_inject):
        """ 
        Smartly finds the best place in the email text (usually right before "Best Regards" or the signature) 
        and securely inserts our custom table there.
        """
        body_str = str(body)

        closing_markers = [
            r'<p[^>]*>\s*If you have already (processed|made) the payment',
            r'<p[^>]*>\s*If the payment has already been made',
            r'<p[^>]*>\s*Best [Rr]egards,?',
            r'<p[^>]*>\s*Sincerely,?',
            r'<p[^>]*>\s*Kind [Rr]egards,?',
            r'<p[^>]*>\s*Yours [Ff]aithfully,?',
            r'<p[^>]*>\s*Best regards,?',
            r'--<br/>',
        ]

        for marker in closing_markers:
            match = re.search(marker, body_str, re.IGNORECASE)
            if match:
                start_pos = match.start()
                return body_str[:start_pos] + html_to_inject + body_str[start_pos:]

        if body_str.strip().lower().endswith('</div>'):
            return body_str.strip()[:-6] + html_to_inject + '</div>'

        return body_str + html_to_inject

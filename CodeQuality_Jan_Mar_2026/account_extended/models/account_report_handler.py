# -*- coding: utf-8 -*-

from odoo import models, _


class AccountFollowupReportHandler(models.AbstractModel):
    """
    Modifies how Odoo internally calculates and formats the accounting follow-up report lines.
    Specifically, it ensures that even if a customer's invoice uses the company's default currency, 
    the currency symbol (like € or $) is still explicitly printed next to the amount 
    so it's clearly visible on the final follow-up document.
    """
    _inherit = 'account.followup.report.handler'

    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group,
                                   level_shift=0):
        """
        Internal calculation step: Forces Odoo to attach the currency symbol to each individual invoice line 
        when generating the follow-up report instead of leaving it blank.
        """
        # Call the parent method to get the base report line
        res = super()._get_report_line_move_line(options, aml_query_result, partner_line_id, init_bal_by_col_group,
                                                 level_shift=level_shift)

        report = self.env['account.report'].browse(options['report_id'])

        # We need to iterate over the columns to find 'amount_currency'
        # and ensure its name is not empty if it matches the company currency.
        for column, line_col in zip(options['columns'], res['columns']):
            if column.get('expression_label') == 'amount_currency':
                # Original logic in account_partner_ledger.py sets line_col['name'] to '' 
                # if the currency matches the company currency.
                if not line_col.get('name'):
                    col_value = aml_query_result['amount_currency']
                    currency = self.env['res.currency'].browse(aml_query_result['currency_id'])

                    # Re-build the column dictionary with the actual value and currency
                    # This ensures the amount is formatted with the currency symbol.
                    new_col = report._build_column_dict(col_value, column, options=options, currency=currency)
                    line_col.update(new_col)

        return res

    def _get_report_line_total(self, options, totals_by_column_group):
        """
        Internal calculation step: Calculates the total amount due for a customer and 
        forces Odoo to display the correct currency symbol next to the final total.
        """
        # Call the parent method to get the base total line
        res = super()._get_report_line_total(options, totals_by_column_group)
        report = self.env['account.report'].browse(options['report_id'])

        # Check if we have only one partner selected (typical for follow-up)
        if options.get('partner_ids') and len(options['partner_ids']) == 1:
            partner = self.env['res.partner'].browse(options['partner_ids'][0])
            
            # Sum unreconciled amounts in currency
            # We filter by company and unreconciled status to match report logic
            amls = partner.unreconciled_aml_ids.filtered(
                lambda l: l.company_id == self.env.company and not l.currency_id.is_zero(l.amount_residual_currency)
            )
            
            if amls:
                # Group by currency to see if we have a consistent one
                currencies = amls.mapped('currency_id')
                total_currency = sum(amls.mapped('amount_residual_currency'))
                
                # Find the 'amount_currency' column to update
                for i, column in enumerate(options['columns']):
                    if column.get('expression_label') == 'amount_currency':
                        # Use the first currency found for formatting (or company if mixed/none)
                        currency = currencies[0] if len(currencies) == 1 else self.env.company.currency_id
                        res['columns'][i] = report._build_column_dict(total_currency, column, options=options, currency=currency)

        return res

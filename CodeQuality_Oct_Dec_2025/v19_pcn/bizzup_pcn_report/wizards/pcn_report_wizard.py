# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app
import base64
import logging
from datetime import datetime, timedelta
from venv import logger

from lxml import etree
from odoo import models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PCNReportWizard(models.TransientModel):
    _name = "pcn.report.wizard"
    _description = "PCN Report"

    def _get_last_date_of_previous_month(self):
        # Get the current date
        today = datetime.today()

        # TODO: previous month range as default
        # Calculate the first day of the current month
        first_day_of_current_month = datetime(today.year, today.month, 1)
        # Subtract one day to get the last day of the previous month
        last_day_of_previous_month = first_day_of_current_month - timedelta(
            days=1)

        return last_day_of_previous_month.date()

    start_date = fields.Date("Start Date",
                             default=datetime.now().date().replace(month=1,
                                                                   day=1))
    end_date = fields.Date("End Date",
                           default=lambda self: self._get_last_date_of_previous_month())
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    state = fields.Selection(
        [('choose', 'choose'), ('get', 'get')], default='choose')
    pcn_filename = fields.Char()
    pcn_data = fields.Binary(
        'PCN Report', readonly=True, attachment=False)

    is_pcn_test_report = fields.Boolean('PCN Test Report')
    run_date = fields.Char(
        string="Run Date",
        default=lambda self: fields.Date.context_today(self).strftime('%-d %B %Y')  # e.g., "2 July 2025"
    )

    def count_length(self, records, length):
        """Find and passed length of each record."""
        records = str(records)
        if len(records) < length:
            value = records.rjust(length, "0")
        elif len(records) > length:
            value = records[:length]
        else:
            value = records

        assert len(value) == length
        return value

    def right_count_length(self, records, length):
        records = str(records)
        if len(records) < length:
            value = records.ljust(length, "0")
        elif len(records) > length:
            value = records[:length]
        else:
            value = records
        return value

    def _get_tax_amount(self, entry):
        """Returns the total tax amount of the entry"""
        tax_tags = self.env['account.account.tag'].search([
            ("name", "in", ["+VAT Sales", "-VAT Sales"])
        ])

        vat_lines = entry.line_ids.filtered(
            lambda line: any(
                tag.id in tax_tags.ids for tag in line.tax_tag_ids)
        )

        credit_sum = sum(vat_lines.mapped("credit"))
        debit_sum = sum(vat_lines.mapped("debit"))

        return credit_sum - debit_sum

    def _get_untaxed_amount(self, entry):
        """Returns the untaxed amount of the entry"""
        base_tax_tags = self.env['account.account.tag'].search([
            ('name', 'ilike', 'VAT SALES (BASE)')
        ])

        vat_lines = entry.line_ids.filtered(
            lambda line: any(
                tag.id in base_tax_tags.ids for tag in line.tax_tag_ids)
        )

        credit_sum = sum(vat_lines.mapped("credit"))
        debit_sum = sum(vat_lines.mapped("debit"))

        return credit_sum - debit_sum

    def check_untaxed_amount(self, move):
        untax_grids = self.env['account.account.tag'].search([
            ('name', 'ilike', 'VAT SALES (BASE)')
        ]).ids

        return any(
            line.tax_tag_ids.filtered(lambda tag: tag.id in untax_grids) for
            line in move.line_ids)

    def has_taxed_invoice_lines(self, move):
        """
        Check if any invoice line in the given move has taxes applied.
        """
        return any(line.tax_ids for line in move.invoice_line_ids)

    def calculate_total_excluding_vat(self, move):
        """
        Check if the Tax Grid includes 'VAT 2/3' in journal items.
        If found, subtract the amount from the total.

        :param move: account.move record
        :return: Adjusted total amount
        """
        # total_amount = sum(move.line_ids.mapped('amount'))  # Get total from journal items
        tax_2_3_grids = self.env['account.account.tag'].search([
            ('name', 'ilike', 'VAT Inputs')
        ]).ids

        vat_lines = move.line_ids.filtered(
            lambda line: any(
                tag.id in tax_2_3_grids for tag in line.tax_tag_ids)
        )

        credit_sum = sum(vat_lines.mapped("credit"))
        debit_sum = sum(vat_lines.mapped("debit"))
        return debit_sum - credit_sum

    def _check_tax_in_debit(self, entry):
        """Check if the tax amount is in debit for the given entry."""
        tax_tags = self.env['account.account.tag'].search([("name", "in", ["+VAT Sales", "-VAT Sales"])])
        vat_lines = entry.line_ids.filtered(lambda line: any(tag.id in tax_tags.ids for tag in line.tax_tag_ids))
        credit_sum = sum(vat_lines.mapped("credit"))
        debit_sum = sum(vat_lines.mapped("debit"))
        return debit_sum > credit_sum

    def _get_header_entry(self):
        start_date = self.start_date
        end_date = self.end_date

        sales_count = 0
        sales_sum_untaxed = 0
        sales_sum_tax = 0
        sales_sum_exempt = 0
        inputs_count = 0
        other_input = 0

        if start_date > end_date:
            raise ValidationError("Please add valid dates. Start date can not be greater than end date.")

        submit_date = self.end_date.strftime("%Y%m")
        file_generation_date = datetime.today().strftime("%Y%m%d")

        header_data = {
            'entry_type': "O",
            'customer_vat_id': self.count_length(self.company_id.vat, 9),
            'submit_date': self.count_length(submit_date, 6),
            'report_type': "1",
            'file_generation_date': self.count_length(file_generation_date, 8),
            'total_untaxed_amount': "+" + self.count_length("0", 11),
            'total_tax_amount': "+" + self.count_length("0", 9),
            'taxable_different_rate_exclude_vat': "+" + self.count_length("0", 11),
            'taxable_different_rate_only_vat': "+" + self.count_length("0", 9),
            'deals_entries_count': self.count_length("0", 9),
            'exempt_sales': "+" + self.count_length("0", 11),
            'other_inputs_sales': "+" + self.count_length("0", 9),
            'equipment_inputs_sales': "+" + self.count_length("0", 9),
            'tsuma_entries_count': "+" + self.count_length("0", 9),
            'total_vat_due': "+" + self.count_length("0", 11),
        }

        records = []

        # Journal entry filters
        journal_entries = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('company_id', '=', self.env.company.id),
            ('is_pcn', '=', False),
            '|',
            ('move_type', 'in',
             ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ('is_pos_invoice', '=', True)
        ])
        # filter by dates:
        entries_in_range = journal_entries.filtered(lambda move: (
                (
                        move.move_type in ['out_invoice', 'out_refund'] and
                        move.amount_untaxed > 0 and
                        self.has_taxed_invoice_lines(move) and
                        start_date <= move.invoice_date <= end_date
                ) or
                (
                        move.move_type in ['in_invoice', 'in_refund'] and
                        move.amount_untaxed > 0 and
                        self.has_taxed_invoice_lines(move) and
                        start_date <= move.date <= end_date
                ) or
                        move.move_type in ['entry'] and
                        self.check_untaxed_amount(move) and
                        start_date <= move.date <= end_date
        ))


        # Loop through journal entries
        for entry in entries_in_range:

            # Initialize transaction data
            partner_vat = entry.partner_id.vat if entry.partner_id.vat else "0"

            amount_taxed = round(entry.amount_tax)
            amount_untaxed = round(entry.amount_untaxed)

            if entry.move_type in ('out_refund', 'in_refund'):
                invoice_sign = '-'
                amount_taxed = abs(amount_taxed) * -1  # make negative
                amount_untaxed = abs(amount_untaxed) * -1  # make negative
            else:
                invoice_sign = '+'

            if entry.move_type in ('out_invoice', 'out_refund'):
                entry_date = entry.invoice_date.strftime("%Y%m%d")
            else:
                entry_date = entry.date.strftime("%Y%m%d")

            if entry.move_type in ('entry'):
                amount_taxed = round(self._get_tax_amount(entry))
                amount_untaxed = round(self._get_untaxed_amount(entry))
                entry_date = entry.date.strftime("%Y%m%d")
            else:
                entry_date = entry.invoice_date.strftime("%Y%m%d")

            if entry.move_type in ['in_invoice','in_refund'] and entry.pcn_codes == 'T':
                taxed_amount = round(self.calculate_total_excluding_vat(
                    entry))
                if taxed_amount:
                    amount_taxed = taxed_amount
                    amount_untaxed = round(entry.amount_total - abs(amount_taxed))

            if (entry.is_pos_invoice and self._check_tax_in_debit(
                    entry)):
                invoice_sign = '-'
            pcn_codes = entry.pcn_codes

            confirmation_number = entry.rt_confirmation_number if entry.rt_confirmation_number else 0
            confirmation_number_last9 = str(confirmation_number)[-9:]
            transaction_data = {
                'transaction_entry_type': pcn_codes,
                'partner_vat': self.count_length(partner_vat, 9),
                'entry_date': self.count_length(entry_date, 8),
                'reference_group': self.count_length("0", 4),
                'reference_number': self.right_count_length(entry.id, 9),
                'amount_taxed': self.count_length(abs(amount_taxed), 9),
                'amount_untaxed': invoice_sign + self.count_length(abs(amount_untaxed), 10),
                'future_data': self.count_length(confirmation_number_last9, 9)
            }

            if entry.pcn_codes == 'C':
                # Reverse values for "M" entry
                M_entry = {
                    'transaction_entry_type': 'M',
                    'partner_vat': self.count_length(partner_vat, 9),
                    'entry_date': self.count_length(entry_date, 8),
                    'reference_group': self.count_length("0", 4),
                    'reference_number': self.right_count_length(entry.id, 9),
                    'amount_taxed': self.count_length(abs(amount_taxed), 9),
                    'amount_untaxed': invoice_sign + self.count_length(abs(amount_untaxed), 10),
                    'future_data': self.count_length(confirmation_number, 9)
                }
                records.append(M_entry)

                sales_count += 1

                # If tax is exempt
                if amount_taxed == 0 and (tax.tax_ids.amount == 0 for tax in
                                          entry.invoice_line_ids):
                    sales_sum_exempt += amount_untaxed

                else:
                    # Managed Amount Tax
                    sales_sum_tax += amount_taxed

                    # Managed Amount Untaxed
                    sales_sum_untaxed += amount_untaxed

            records.append(transaction_data)

            # Update header data based on transaction entry type
            if pcn_codes in ['S', 'L', 'M', 'Y', 'I']:
                sales_count += 1

                # If tax is exempt
                if amount_taxed == 0 and (tax.tax_ids.amount == 0 for tax in
                                          entry.invoice_line_ids):
                    sales_sum_exempt += amount_untaxed

                else:
                    # Managed Amount Tax
                    sales_sum_tax += amount_taxed

                    # Managed Amount Untaxed
                    sales_sum_untaxed += amount_untaxed


            elif pcn_codes in ['T', 'C', 'K', 'R', 'P', 'H']:
                inputs_count += 1

                # current default
                other_input += amount_taxed

            else:
                logger.warning(f"PCN code is not supported: '{pcn_codes}' ID: {entry.id}")

        # --------------------------- Header assignment ------------------------

        header_data['tsuma_entries_count'] = self.count_length(inputs_count, 9)
        header_data['deals_entries_count'] = self.count_length(sales_count, 9)

        if sales_sum_tax < 0:
            header_data['total_tax_amount'] = '-' + self.count_length(
                abs(sales_sum_tax), 9)
        else:
            header_data['total_tax_amount'] = '+' + self.count_length(
                sales_sum_tax, 9)

        if sales_sum_untaxed < 0:
            header_data['total_untaxed_amount'] = '-' + self.count_length(
                abs(sales_sum_untaxed), 11)
        else:
            header_data['total_untaxed_amount'] = '+' + self.count_length(
                sales_sum_untaxed, 11)

        if sales_sum_exempt < 0:
            header_data['exempt_sales'] = '-' + self.count_length(abs(sales_sum_exempt), 11)
        else:
            header_data['exempt_sales'] = '+' + self.count_length(sales_sum_exempt, 11)

        if other_input < 0:
            header_data['other_inputs_sales'] = '-' + self.count_length(abs(other_input), 9)
        else:
            header_data['other_inputs_sales'] = '+' + self.count_length(other_input, 9)

        # Calculate Total VAT Due
        total_vat_due = round(int(header_data['total_tax_amount']) - int(header_data['other_inputs_sales']) -
                              int(header_data['equipment_inputs_sales']))
        if total_vat_due < 0:
            header_data['total_vat_due'] = "-" + self.count_length(abs(total_vat_due), 11)
        else:
            header_data['total_vat_due'] = "+" + self.count_length(abs(total_vat_due), 11)

        records.insert(0, header_data)
        # update pcn run date to today date
        if self.run_date:
            entries_in_range.run_date = self.run_date

        if not self.is_pcn_test_report:
            entries_in_range.is_pcn = True

        return records

    def _closing_entris(self):
        docs = []
        closing_entry = {
            'closing_entry_type': "X",
            'closing_company_vat_id': self.count_length(self.company_id.vat, 9)
        }
        docs.append(closing_entry)
        return docs

    def generate(self):
        content = etree.fromstring(
            self.env['ir.ui.view']._render_template(
                'bizzup_pcn_report.pcn_dat_file',
                {"docs_list": self._get_header_entry(), "closing_entry": self._closing_entris()})).text.replace("\n",
                                                                                                                "").replace(
            "            ", "").replace("\n                ", "\n").replace("!@#*^$!@#*^$!@#*^$", "\n").replace(
            "!@#*^$!@#*^$", "\n").replace("!@#*^$", "\n").strip().encode("iso8859_8")

        vals = {
            'state': 'get',
            'pcn_data': base64.encodebytes(content),
            'pcn_filename': "PCN874.TXT",
        }
        if not self.is_pcn_test_report:
            self.env['pcn.attachment'].create(
                {
                    'pcn_file': base64.encodebytes(content),
                    'printing_date': fields.Datetime.now(),
                    'printed_by': self.env.user.id, 'pcn_filename': "PCN874.TXT",
                 })
        self.write(vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pcn.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

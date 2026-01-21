# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import _, fields, models,api
import base64
import json
# import pandas as pd
# import openpyxl
# from openpyxl import Workbook
# from openpyxl.styles import Alignment, PatternFill, Color, Font
from lxml import etree
from odoo.exceptions import ValidationError

CATEGORY_SELECTION = [
    ('א', '&'),
    ('ב', 'A'),
    ('ג', 'B'),
    ('ד', 'C'),
    ('ה', 'D'),
    ('ו', 'E'),
    ('ז', 'F'),
    ('ח', 'G'),
    ('ט', 'H'),
    ('י', 'I'),
    ('ך', 'J'),
    ('כ', 'K'),
    ('ל', 'L'),
    ('ם', 'M'),
    ('מ', 'N'),
    ('ן', 'O'),
    ('נ', 'P'),
    ('ס', 'Q'),
    ('ע', 'R'),
    ('ף', 'S'),
    ('פ', 'T'),
    ('ץ', 'U'),
    ('צ', 'V'),
    ('ק', 'W'),
    ('ר', 'X'),
    ('ש', 'Y'),
    ('ת', 'Z'),
]

class CertificationReportText(models.AbstractModel):
    _name = 'report.vander_bill_ascii_report.vendorbill_text_report_text1'
    _description = "Colombian Certification Report"

    def _get_report_values(self, docids, data=None):
        docs = []
        partner_doc = {}

        return {
            'docs': docs,
            'a': data['a'],
        }

class VenderBillASCIIReportHistory(models.Model):
    _name = "vendor.bill.history"

    report_data = fields.Binary('Report Data')





class VenderBillASCIIReportWizard(models.TransientModel):
    _name = "vender.bill.ascii.reort.wizard"
    _description = "Vender Bill ASCII Report Wizard"
    _rec_name = 'report_type'


    report_type=fields.Selection([('vendor','Vendor'),('salary','Salary')],default='vendor')

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    payment_date = fields.Date(string="Payment Date")
    first_line = fields.Char("First")

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company
    )
    masav_no_id = fields.Many2one(
        "masav.no",
        string="Masav No",
        domain="[('company_id', '=', company_id)]",
        required=True
    )
    vendor_ids = fields.Many2many(
        'res.partner',
        string="Vendors",
        domain="[('id', 'in', filtered_vendor_ids)]"
    )
    filtered_vendor_ids = fields.Many2many(
        'res.partner',
        compute='_compute_filtered_vendors',
        store=False
    )

    @api.onchange('start_date', 'end_date')
    def _onchange_dates_clear_vendors(self):
        """
              Clear selected vendors when either the start or end date changes.

              This ensures that outdated or invalid vendor selections are removed
              whenever the date range is modified.
         """
        for rec in self:
            rec.vendor_ids = [(5, 0, 0)]

    @api.depends('start_date', 'end_date')
    def _compute_filtered_vendors(self):
        """
               Compute and assign the list of vendors based on payment records within the selected date range.

               If the report type is 'vendor' and both start_date and end_date are set,
               this method searches for outbound supplier payments within the date range
               and assigns the corresponding partner (vendor) IDs to `filtered_vendor_ids`.

               If the conditions are not met, the list is cleared.
         """
        for rec in self:
            if rec.report_type == 'vendor' and rec.start_date and rec.end_date:
                payments = self.env['account.payment'].search([
                    ('date', '>=', rec.start_date),
                    ('date', '<=', rec.end_date),
                    ('partner_type', '=', 'supplier'),
                    ('payment_type', '=', 'outbound'),
                    ('company_id', '=', self.env.company.id),
                    ('currency_id', '=', rec.env.company.currency_id.id),
                    ('partner_id', '!=', False),
                    ('is_printed', '!=', True),
                    ('receipt_id', '=', False),
                ])
                rec.filtered_vendor_ids = payments.mapped('partner_id').ids
            else:
                rec.filtered_vendor_ids = []

    def print_text_report_from_button(
            self
            ):
        import re

        domain = [
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('payment_type', '=', 'outbound'),  # Vendor payments only
            ('company_id', '=', self.env.company.id),
            ('currency_id', '=', self.env.company.currency_id.id),
            ('is_printed', '!=', True),
            ('receipt_id', '=', False),
        ]
        if self.env.company.is_account_paid:
            domain += [('state', '=', 'posted')]
        if self.vendor_ids:
            domain += [('partner_id', 'in', self.vendor_ids.ids)]
        masav = self.env.company.masav if self.report_type == 'vendor' else self.env.company.Masav_salary

        company_name = self.env.company.name
        padded_company = self.pad_data(
            company_name,
            30
            )

        if not re.search(
                '[a-zA-Z0-9]',
                company_name
                ):
            reversed_company = self.pad_data(
                company_name,
                30
                )[::-1]
            padded_company = ''.join(
                next(
                    (cat[1] for cat in CATEGORY_SELECTION if cat[0] == char),
                    char
                    )
                for char in reversed_company
            ).replace(
                '&amp;',
                '&'
                )

        first_line = (
            f"K{self.pad_data(masav or '0', 8)}00"
            f"{self.payment_date.strftime('%y%m%d') if self.payment_date else '000000'}0"
            f"0010{fields.date.today().strftime('%y%m%d')}{self.pad_data(self.masav_no_id.masav_no or '', 5)}000000"
            f"{padded_company}{''.ljust(56, ' ')}KOT"
        )

        account_moves = self.env['account.payment'].search(
            domain
        )
        missing_bank_accounts = [payment.display_name for payment in account_moves if not payment.partner_id.bank_ids]
        if missing_bank_accounts:
            active_lang = self.env.context.get('lang', 'en_US')
            if active_lang == 'he_IL':
                raise ValidationError(
                    _("בבקשה עדכן את חשבונות הבנק עבור התשלומים הבאים: %s") % ", ".join(missing_bank_accounts)
                )
            else:
                raise ValidationError(
                    _("Please set the vendor bank account for the following payments: %s") % ", ".join(
                        missing_bank_accounts)
                )

        if account_moves:
            self._cr.execute(
                '''
                UPDATE account_payment 
                SET is_printed=%s
                WHERE id = ANY(%s)
                ''',
                [True, account_moves.ids]
            )

        move_data = []

        for move in account_moves:
            bank_account = move.partner_bank_id or move.partner_id.bank_ids[:1]
            bic = bank_account.bank_bic if bank_account else '0'
            if not re.search(
                    '[a-zA-Z0-9]',
                    bic
                    ):
                bic = ''.join(
                    next(
                        (cat[1] for cat in CATEGORY_SELECTION if
                         cat[0] == char),
                        char
                        )
                    for char in reversed(
                        bic
                        )
                ).replace(
                    '&amp;',
                    '&'
                    )

            acc_no = bank_account.acc_number if bank_account else '0'
            if not re.search(
                    '[a-zA-Z0-9]',
                    acc_no
                    ):
                acc_no = ''.join(
                    next(
                        (cat[1] for cat in CATEGORY_SELECTION if
                         cat[0] == char),
                        char
                        )
                    for char in reversed(
                        acc_no
                        )
                ).replace(
                    '&amp;',
                    '&'
                    )

            vat = move.partner_id.vat or '0'
            if not re.search(
                    '[a-zA-Z0-9]',
                    vat
                    ):
                vat = ''.join(
                    next(
                        (cat[1] for cat in CATEGORY_SELECTION if
                         cat[0] == char),
                        char
                        )
                    for char in vat
                ).replace(
                    '&amp;',
                    '&'
                    )

            partner_name = self.pad_data(
                move.partner_id.name,
                16
                )
            if not re.search(
                    '[a-zA-Z]',
                    move.partner_id.name
                    ):
                partner_name = ''.join(
                    next(
                        (cat[1] for cat in CATEGORY_SELECTION if
                         cat[0] == char),
                        char
                        )
                    for char in self.pad_data(
                        move.partner_id.name,
                        16
                        )[::-1]
                )

            # Ensure numeric fields are properly formatted without dots
            amount_signed = str(
                "{:.2f}".format(
                    abs(
                        move.amount_after_withholding
                    )
                )
            ).replace('.', '')  # Convert to integer and string
            vat_padded = self.pad_data(
                vat,
                20
                )

            second_line = (
                f"1{self.pad_data(masav or '0', 8)}00"
                f"000000{self.pad_data(bic, 2)}{self.pad_data(move.partner_bank_id.branch_bank or '0', 3)}0000"
                f"{self.pad_data(acc_no, 9)}0{self.pad_data(vat, 9)}{partner_name}"

                f"{self.pad_data(amount_signed, 13)}{vat_padded}"
                f"{move.date.strftime('%y%m') if move.date else ''}{move.date.strftime('%y%m') if move.date else ''}"
                f"000006000000000000000000{' '.ljust(2)}"
            )
            move_data.append(
                second_line
                )
        amount_signed_sum = str("{:.2f}".format(abs(sum(account_moves.mapped('amount_after_withholding'))))).replace('.','')
        last_line = (
            f"5{self.pad_data(masav or '0', 8)}00"
            f"{self.payment_date.strftime('%y%m%d') if self.payment_date else '000000'}0"
            f"001{self.pad_data(amount_signed_sum, 15)}"  # Convert to integer and string
            f"000000000000000{self.pad_data(str(len(account_moves)), 7)}0000000{''.ljust(63)}"
        )

        final_line = ''.ljust(
            128,
            '9'
            )

        return self.env.ref(
            'vander_bill_ascii_report.vendorbill_text_report_id'
        ).report_action(
            [],
            data={
                'a': [first_line, move_data, last_line, final_line]
            }
        )

    def pad_data(self,data, length):
        if data == False:
            data = ''
        data = str(data)
        if len(data) >= length:
            return data[:length]
        else:
            return str('0' * (length - len(data)) +data)



    def action_print_ascii_report(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Vender Bill"


        # ----------------Titile Entry------------
        row = 1
        # length 1
        ws.cell(row, 1).value = 'K'

        # length 8
        ws.cell(row, 2).value = self.pad_data(self.env.company.masav,8)
        ws.cell(row, 3).value = '000'
        ws.cell(row, 4).value = self.payment_date
        ws.cell(row, 5).value = '0'
        ws.cell(row, 6).value = '001'
        ws.cell(row, 7).value = '0'
        ws.cell(row, 8).value = fields.date.today()
        ws.cell(row, 9).value = self.pad_data(self.masav_no_id.masav_no,5)
        ws.cell(row, 10).value = '000000'
        ws.cell(row, 11).value = self.pad_data(self.env.company.name or '',30)
        ws.cell(row, 12).value = ''.ljust(56, ' ')
        ws.cell(row, 13).value = 'KOT'
        # -----------Move Entry--------------
        domain = [
            # ('date', '>=', self.start_date),
            # ('date', '<=', self.end_date),
            ('state','=','posted')]
        if self.payment_date:
            domain += [('invoice_date', '=', self.payment_date)]
        account_moves = self.env['account.move'].search(domain)
        # row += 1
        for move in account_moves:
            row += 1
            ws.cell(row, 1).value = '1'
            ws.cell(row, 2).value = self.pad_data(self.env.company.masav,8)
            ws.cell(row, 3).value = '000'
            ws.cell(row, 4).value = '000000'
            ws.cell(row, 5).value = self.pad_data(move.partner_bank_id.bank_bic or '',2)
            ws.cell(row, 6).value = self.pad_data(move.partner_bank_id.bank_name or '',3)
            ws.cell(row, 7).value = '0000'
            ws.cell(row, 8).value = self.pad_data(move.partner_bank_id.acc_number or '',9)
            ws.cell(row, 9).value = '0'
            ws.cell(row, 10).value = self.pad_data(str(move.partner_id.vat) or '',9)
            ws.cell(row, 11).value = self.pad_data(str(move.partner_id.name) or '',16)
            ws.cell(row, 12).value = self.pad_data(str(move.amount_total) or '',13).replace('.','')
            ws.cell(row, 13).value = self.pad_data(move.partner_id.vat or '',20)
            ws.cell(row, 14).value = move.date or ''
            ws.cell(row, 15).value = '000'
            ws.cell(row, 16).value = '006'
            ws.cell(row, 17).value = '000000000000000000'
            ws.cell(row, 18).value = ''.ljust(2, ' ')

        # -----------------------Sum Entry---------
        row += 1
        ws.cell(row, 1).value = '5'
        ws.cell(row, 2).value = self.pad_data(self.env.company.masav or '' ,8)
        ws.cell(row, 3).value = '00'
        ws.cell(row, 4).value = str(self.payment_date) or ''
        ws.cell(row, 5).value = '0'
        ws.cell(row, 6).value = '001'
        ws.cell(row, 7).value = sum(account_moves.mapped('amount_total_signed'))
        ws.cell(row, 8).value = '000000000000000'
        ws.cell(row, 9).value = len(account_moves)
        ws.cell(row, 10).value = '0000000'
        ws.cell(row, 11).value = ''.ljust(62, ' ')


        filename = '/tmp/vendor_bill.xlsx'
        wb.save(filename)
        file = open(filename, "rb")
        file_data = file.read()
        out = base64.encodebytes(file_data)

        export_id = self.env['print.excel.ascii.report'].sudo().create({
            'file': out,
            'file_name': filename.replace('/tmp/', '')
        })
        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'print.excel.ascii.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class PrintExcelASCIIReport(models.TransientModel):
    _name = 'print.excel.ascii.report'

    file = fields.Binary('Report')
    file_name = fields.Char('Report File Name', readonly=True)

    file1 = fields.Binary('Report')
    file_name1 = fields.Char('Report File Name', readonly=True)



    def print_text_report(self):
        # xlsx_file_path = '/tmp/vendor_bill.xlsx'  # Replace with your Excel file path
        output_text_file = '/tmp/output_report.txt'  # Replace with the desired output file path
        #
        # with open(output_text_file, 'w') as file:
        #     print ("file-------------------------------------",file)
        #     df = pd.read_excel(xlsx_file_path,na_values=None,dtype = str,keep_default_na=False,).to_string(file, index=False)
        #
        # file = open(output_text_file, "rb")
        # file_data = file.read()
        #
        # out = base64.encodebytes(file_data)
        content = etree.fromstring(
            self.env.ref('vander_bill_ascii_report.vendorbill_text_report_id')._render(
                {'a': ['first_line', 'move_data', 'last_line', 'final_line']})).text.replace(
            "\n            ", "\t").replace('!@#*^$', '\n').replace('\n',
                                                                    "").replace('$^*#@!', ' \t ').replace(
            "		", "\n").strip()
        import re
        content = re.sub(' \t ', '', content).encode('UTF-8')
        export_id = self.env['print.excel.ascii.report'].sudo().create({
            'file1': base64.encodebytes(content),
            'file_name1': output_text_file.replace('/tmp/', '')
        })

        # with open("a.txt", "r") as in_f, open("o.txt", "w") as out_f:
        #     out_f.write(' '.join(in_f.read().replace('\n', '')))

        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'print.excel.ascii.report',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

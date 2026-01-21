# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import models, fields, api


class AccountMove(models.Model):
    """Inherited AccountMove for new fields."""
    _inherit = 'account.move'

    is_pcn = fields.Boolean("Included in PCN ?", copy=False)
    pcn_codes = fields.Char("PCN Codes", compute="_compute_pcn_codes")
    is_pos_invoice = fields.Boolean("Is POS Invoice?")
    run_date = fields.Char(string="Run Date")


    @api.onchange('is_pos_invoice')
    def onchange_is_pos_invoice(self):
        """Updates transaction_type_document_out_invoice to 'L' when
         is_pos_invoice changes,if move_type is 'entry' and
         transaction_type_document_out_invoice is not already 'L'.
        """
        if self.move_type == 'entry' and self.is_pos_invoice:
            self.transaction_type_document_out_invoice = 'L'

    @api.depends("transaction_type_document_out_invoice",
                 "transaction_type_document_in_invoice")
    def _compute_pcn_codes(self):
        """Function to compute the PCN codes."""
        for rec in self:
            if (rec.move_type in ('out_invoice',
                                 'out_refund','entry') and
                    rec.transaction_type_document_out_invoice):
                rec.pcn_codes = rec.transaction_type_document_out_invoice
            elif rec.move_type in ('in_invoice',
                                   'in_refund') and rec.transaction_type_document_in_invoice:
                rec.pcn_codes = rec.transaction_type_document_in_invoice
            else:
                rec.pcn_codes = 0

    @api.onchange("transaction_type_document_out_invoice",
                 "transaction_type_document_in_invoice")
    def _onchange_document_type(self):
        """Function to assign fical position if document_type == 'C'."""
        for rec in self:
            if rec.transaction_type_document_in_invoice == 'C':
                self_invoice = self.env['account.fiscal.position'].search([
                    ('name', '=', 'Self Invoice')
                ]).id
                rec.fiscal_position_id = self_invoice


    def _pcn_assignment_cron(self):
        """Function for Scheduled Action."""
        journal_entries = self.env['account.move'].search([
            ('state', '=', 'posted')
        ])
        for rec in journal_entries:
            if rec.move_type in ('out_invoice', 'out_refund') and rec.transaction_type_document_out_invoice:
                rec.pcn_codes = rec.transaction_type_document_out_invoice
            elif rec.move_type in ('in_invoice', 'in_refund') and rec.transaction_type_document_in_invoice:
                rec.pcn_codes = rec.transaction_type_document_in_invoice


    def _update_pos_receipt(self):
        """Update the POS Entry record"""
        pos_sessions = self.env['pos.session'].search([])

        for session in pos_sessions:
            if session.move_id and session.move_id.move_type=='entry':
                session.move_id.is_pos_invoice = True
                session.move_id.transaction_type_document_out_invoice = "L"
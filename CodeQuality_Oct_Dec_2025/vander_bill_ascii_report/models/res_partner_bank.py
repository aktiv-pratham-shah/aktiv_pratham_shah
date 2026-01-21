# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    branch_bank = fields.Integer(string="Branch Name")

    @api.constrains("branch_bank")
    def _check_branch_bank(self):
        """A constraint to check the branch_bank number is valid"""
        for rec in self:
            if rec.env.company.is_validation_masav:
                branch_bank = str(rec.branch_bank)
                if branch_bank and (len(branch_bank) > 3 or not branch_bank.isdigit()):
                    active_lang = self.env.context.get('lang', 'en_US')
                    if active_lang == 'he_IL':  # Hebrew language code
                        raise UserError(_("סניף בנק חייב להיות עד 3 ספרות ולהכיל רק ספרות"))
                    else:
                        raise UserError(_('A partner "Branch Bank" must be 3 or less and contain only numbers.'))

    @api.constrains("acc_number")
    def _check_acc_number(self):
        """A constraint to check the acc_number is valid"""
        for rec in self:
            if rec.env.company.is_validation_masav:
                acc_number = str(rec.acc_number)
                if acc_number and (len(acc_number) > 9 or not acc_number.isdigit()):
                    active_lang = self.env.context.get('lang', 'en_US')
                    if active_lang == 'he_IL':
                        raise UserError(_("חשבון בנק חייב להיות עד 9 ספרות ולהכיל רק ספרות"))
                    else:
                        raise UserError(_('A partner "Account Number" must be 9 or less and contain only numbers.'))

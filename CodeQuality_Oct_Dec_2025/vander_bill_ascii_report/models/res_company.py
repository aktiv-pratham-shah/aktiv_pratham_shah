# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    masav = fields.Integer(string="MASAV Vendor")
    Masav_salary = fields.Integer(string="MASAV Salary")
    masav_no = fields.Integer(string="MASAV No")
    masav_no_ids = fields.One2many(
        'masav.no', 'company_id',
        string="Masav No",
    )
    is_validation_masav = fields.Boolean()
    is_account_paid = fields.Boolean()

    @api.constrains("masav")
    def _check_masav(self):
        """A constraint to check the masav number is unique or not"""
        for rec in self:
            if rec.masav is not None and rec.is_validation_masav:
                masav_str = str(rec.masav)
                if len(masav_str) > 8 or not masav_str.isdigit():
                    active_lang = self.env.context.get('lang', 'en_US')
                    if active_lang == 'he_IL':  # Hebrew language code
                        raise UserError(_("מספר מס\"ב חייב להיות עד 8 ספרות ולהכיל רק ספרות"))
                    else:
                        raise UserError(_('A Company "MASAV Vendor" must be 8 or less and contain only numbers'))

    @api.constrains("masav_no")
    def _check_masav_no(self):
        """A constraint to check the masav_no number is unique or not"""
        for rec in self:
            if rec.masav_no is not None and rec.is_validation_masav:
                masav_no_str = str(rec.masav_no)
                if len(masav_no_str) > 5 or not masav_no_str.isdigit():
                    active_lang = self.env.context.get('lang', 'en_US')
                    if active_lang == 'he_IL':  # Hebrew language code
                        raise UserError(_('"מוסד שולח" חייב להיות עד 5 ספרות ולהכיל רק ספרות'))
                    else:
                        raise UserError(_('A Company "MASAV No" must be 5 or less and contain only numbers.'))

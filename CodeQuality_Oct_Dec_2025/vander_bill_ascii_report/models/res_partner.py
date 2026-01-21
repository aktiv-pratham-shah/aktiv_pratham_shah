# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains("vat")
    def _check_vat(self):
        """A constraint to check the VAT number is unique or not"""
        for rec in self:
            if rec.env.company.is_validation_masav:
                if rec.vat and (len(rec.vat) > 9 or not rec.vat.isdigit()):
                    active_lang = self.env.context.get('lang', 'en_US')
                    if active_lang == 'he_IL':
                        raise UserError(_("ח.פ. חייב להיות עד 9 ספרות ולהכיל רק ספרות"))
                    else:
                        raise UserError(_('A partner "Vat" must be 9 or less and contain only numbers.'))

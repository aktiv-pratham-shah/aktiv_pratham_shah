# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import api, models, _
from odoo.exceptions import UserError


class ResBank(models.Model):
    _inherit = "res.bank"

    @api.constrains("bic")
    def _check_bic(self):
        """A constraint to check the BIC number is unique or not"""
        for rec in self:
            if rec.env.company.is_validation_masav:
                if rec.bic and (len(rec.bic) > 2 or not rec.bic.isdigit()):
                    active_lang = self.env.context.get('lang', 'en_US')
                    if active_lang == 'he_IL':  # Hebrew language code
                        raise UserError(_("קוד בנק חייב להיות עד 2 ספרות ולהכיל רק ספרות"))
                    else:
                        raise UserError(_("A partner 'Bic' must be 2 or less and contain only numbers."))

# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import _, models, fields, api
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_printed = fields.Boolean(
        string="Printed"
    )

    @api.onchange('is_printed')
    def _onchange_is_printed(self):
        """
        Prevent updating the 'is_printed' field if it was already set.

        This method is triggered when the 'is_printed' field is changed.
        If the original record (_origin) already had is_printed set to True,
        a ValidationError is raised to prevent modifications.
        """
        for rec in self:
            if rec.is_printed and not rec._origin.is_printed:
                active_lang = self.env.context.get('lang', 'en_US')
                if active_lang == 'he_IL':
                    raise UserError(
                        _("אתה לא יכול להגדיר שהתשלום הודפס כבר.")
                    )
                else:
                    raise UserError(
                        _("You cannot update this boolean.")
                    )

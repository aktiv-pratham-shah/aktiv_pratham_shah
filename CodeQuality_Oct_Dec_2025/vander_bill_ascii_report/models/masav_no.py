# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import fields, models, _, api
from odoo.exceptions import ValidationError


class MasavaNo(models.Model):
    _name = "masav.no"
    _description = "Masav No"
    _rec_name = 'masav_no'

    masav_no = fields.Integer("Masav No")
    company_id = fields.Many2one('res.company')

    @api.constrains('masav_no')
    def _check_unique_masav_no(self):
        """Check that the masav_no is unique"""
        for rec in self:
            existing = self.search([('masav_no', '=', rec.masav_no), ('id', '!=', rec.id)])
            if existing:
                active_lang = self.env.context.get('lang', 'en_US')
                if active_lang == 'he_IL':  # Hebrew language code
                    raise ValidationError(_("סוג מס\"ב לא קיים עדיין"))
                else:
                    raise ValidationError(_("Type masav no already exists!"))
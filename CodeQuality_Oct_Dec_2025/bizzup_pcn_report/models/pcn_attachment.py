# -*- coding: utf-8 -*-
# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app
from odoo import models, fields

class PcnAttachment(models.Model):
    _name = 'pcn.attachment'
    _description = 'PCN Attachment'
    _order = 'printing_date desc'

    printing_date = fields.Datetime(string='Printing Date', default=fields.Datetime.now)
    printed_by = fields.Many2one('res.users', string='Printed By', default=lambda self: self.env.user)
    pcn_file = fields.Binary(string='Generated PCN')
    pcn_filename = fields.Char(string='Filename')
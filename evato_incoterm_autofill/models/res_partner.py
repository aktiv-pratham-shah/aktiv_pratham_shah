# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    """
    Inherits res.partner to add a default incoterm_id field.

    The incoterm_id defined on a partner will be automatically propagated
    to any transactional document (sale order, purchase order, invoice,
    bank statement line) when that partner is selected.
    """
    _inherit = 'res.partner'

    incoterm_id = fields.Many2one(
        'account.incoterms',
        string='Incoterm',
        help="International Commercial Terms are a series of predefined "
             "commercial terms used in international transactions."
    )

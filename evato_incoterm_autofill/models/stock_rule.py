# -*- coding: utf-8 -*-
from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):
        """
        Extend the purchase order preparation values to automatically set
        incoterm_id from the vendor/supplier partner's default incoterm.

        This fires for ALL procurement-driven PO creation, including:
          - Standard replenishment
          - Dropship route (picking_type.code == 'dropship')

        The vendor partner is identified via values['supplier'].partner_id,
        which is the same partner that will be set as partner_id on the PO.
        """
        vals = super()._prepare_purchase_order(company_id, origins, values)

        # values is already the first element after super() consumed the list,
        # so we work from the prepared dict.  The supplier partner is available
        # in the original values list before the call, but super() already
        # consumed it.  We can read the partner from vals['partner_id'] instead.
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        if partner and partner.incoterm_id:
            vals['incoterm_id'] = partner.incoterm_id.id

        return vals

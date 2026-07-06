# -*- coding: utf-8 -*-
from odoo import models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id')
    def _onchange_partner_id_set_incoterm(self):
        """
        Onchange handler for partner_id.

        Automatically sets incoterm_id from the selected partner's
        incoterm_id. Clears the field if no partner is selected.
        """
        if self.partner_id and self.partner_id.incoterm_id:
            self.incoterm_id = self.partner_id.incoterm_id
        elif not self.partner_id:
            self.incoterm_id = False

    def copy(self, default=None):
        """
        Override copy() so that when a Sale Order is duplicated the incoterm
        is always taken from the partner's default incoterm_id, NOT carried
        over from the source order's (potentially manually-changed) value.
        """
        default = default or {}
        # Reset incoterm: pull from partner so duplication always reflects
        # the partner's configured default, ignoring any manual override.
        partner = self.partner_id
        if partner and partner.incoterm_id:
            default.setdefault('incoterm_id', partner.incoterm_id.id)
        else:
            default.setdefault('incoterm_id', False)
        return super().copy(default)

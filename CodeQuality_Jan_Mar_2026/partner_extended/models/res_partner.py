# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResPartner(models.Model):
    """
    Extends the standard Contact (Partner) system in Odoo to include 
    custom classification fields like Region, Customer Type, and Lead Source.
    It also includes an automated task (cron job) that automatically 
    changes a customer's status from 'New' to 'Existing' every April 1st.
    """
    _inherit = 'res.partner'

    x_studio_newexisting = fields.Selection([("Existing", "Existing"), ("New", "New")], string="New/Existing")
    x_studio_region = fields.Selection([("Americas", "Americas"), ("RoW", "RoW")], string="Region")
    x_studio_region_1 = fields.Selection([("Americas", "Americas"), ("RoW", "RoW")], string="Region")
    x_studio_lead_source = fields.Selection([("Inbound", "Inbound"), ("Outbound", "Outbound")], string="Lead Source")
    x_studio_customer_type = fields.Selection([("B2B", "B2B"), ("B2C", "B2C")], string="Customer Type")

    @api.model
    def _cron_update_customer_status(self):
        """
        Automated Job: Finds all contacts currently marked as 'New' 
        and automatically changes them to 'Existing'.
        This is typically scheduled to run automatically on April 1st of every year.
        """
        partners_to_update = self.search([('x_studio_newexisting', '=', 'New')])
        if partners_to_update:
            partners_to_update.write({'x_studio_newexisting': 'Existing'})

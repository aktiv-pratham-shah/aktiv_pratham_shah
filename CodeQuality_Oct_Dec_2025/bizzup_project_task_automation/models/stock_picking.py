# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    def _infer_project_from_sale_order(self):
        """
        Attempt to find and set the project_id from the related Sale Order.
        """
        for picking in self:
            if not picking.project_id and picking.sale_id and picking.sale_id.project_id:
                picking.project_id = picking.sale_id.project_id

    def write(self, vals):
        """
        Override write to trigger task date updates when Delivery Order is modified.

        Triggers update when:
        - Analytic account is set or changed
        - Scheduled date changes
        - State changes
        """
        res = super(StockPicking, self).write(vals)

        # Try to infer project if missing
        if not self.project_id:
            self._infer_project_from_sale_order()

        # Trigger update if project, scheduled date, or state changes
        if 'project_id' in vals or 'scheduled_date' in vals or 'state' in vals or self.project_id:
            self._update_related_delivery_tasks()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to trigger task date updates when Delivery Order is created.
        """
        pickings = super(StockPicking, self).create(vals_list)
        pickings._infer_project_from_sale_order()
        pickings._update_related_delivery_tasks()
        return pickings

    def _update_related_delivery_tasks(self):
        """
        Find and update all delivery tasks related to this Delivery Order's project.
        """
        for picking in self:
            # Only process outgoing deliveries linked to a project
            if picking.picking_type_code != 'outgoing' or not picking.project_id:
                continue

            # Find delivery tasks in this project
            delivery_tasks = self.env['project.task'].search([
                ('project_id', '=', picking.project_id.id),
                ('is_auto_delivery_task', '=', True)
            ])

            # Update task dates
            delivery_tasks._update_task_dates_from_orders()

    def button_validate(self):
        """
        Override button_validate to update task dates when Delivery Order is validated.
        """
        res = super(StockPicking, self).button_validate()
        self._update_related_delivery_tasks()
        return res

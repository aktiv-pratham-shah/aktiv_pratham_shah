# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _infer_project_from_sale_order(self):
        """
        Attempt to find and set the project_id from related Sale Orders (via order lines).
        """
        for order in self:
            if not order.project_id:
                # Check if any line is linked to a Sale Order Line
                for line in order.order_line:
                    if line.sale_line_id and line.sale_line_id.order_id.project_id:
                        order.project_id = line.sale_line_id.order_id.project_id
                        break

    def write(self, vals):
        """
        Override write to trigger task date updates when PO is modified.
        """
        res = super(PurchaseOrder, self).write(vals)

        # Try to infer project if missing
        if not self.project_id:
            self._infer_project_from_sale_order()

        # Trigger update if project or date changes
        if 'project_id' in vals or 'date_order' in vals or 'state' in vals or self.project_id:
            self._update_related_purchasing_tasks()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to trigger task date updates when PO is created.
        """
        orders = super(PurchaseOrder, self).create(vals_list)
        orders._infer_project_from_sale_order()
        orders._update_related_purchasing_tasks()
        return orders

    def _update_related_purchasing_tasks(self):
        """
        Find and update all purchasing tasks related to this PO's project.
        """
        for order in self:
            if not order.project_id:
                continue

            # Find purchasing tasks in this project
            purchasing_tasks = self.env['project.task'].search([
                ('project_id', '=', order.project_id.id),
                ('is_auto_purchasing_task', '=', True)
            ])

            # Update task dates
            purchasing_tasks._update_task_dates_from_orders()

    def button_confirm(self):
        """
        Override button_confirm to update task dates when PO is confirmed.
        """
        res = super(PurchaseOrder, self).button_confirm()
        self._update_related_purchasing_tasks()
        return res

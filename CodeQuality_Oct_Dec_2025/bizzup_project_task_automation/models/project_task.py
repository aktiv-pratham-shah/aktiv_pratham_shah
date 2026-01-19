# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_auto_purchasing_task = fields.Boolean(
        string="Auto-Update Purchasing Dates",
        help="If checked, this task's planned dates will automatically update based on Purchase Orders linked to the project's analytic account."
    )

    is_auto_production_task = fields.Boolean(
        string="Auto-Update Production Dates",
        help="If checked, this task's planned dates will automatically update based on Manufacturing Orders linked to the project's analytic account."
    )

    is_auto_delivery_task = fields.Boolean(
        string="Auto-Update Delivery Dates",
        help="If checked, this task's planned dates will automatically update based on Delivery Orders linked to the project's analytic account."
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to trigger date update when a task is created.
        This ensures that if orders (PO/MO/DO) already exist when the task is created,
        the dates are synced immediately.
        """
        tasks = super(ProjectTask, self).create(vals_list)
        # Trigger update for the new tasks
        tasks._update_task_dates_from_orders()
        return tasks

    def _update_task_dates_from_orders(self):
        """
        Update task planned dates based on related orders (PO/MO/DO).

        This method is called when Purchase Orders, Manufacturing Orders, or Delivery Orders
        are created or modified. It updates:
        - planned_date_begin (Start Date): Earliest date from related orders
        - date_deadline (End Date): Latest date from related orders

        The linking is done via the project_id field:
        - Orders (PO/MO/DO) are linked directly to the project
        - Tasks with automation flags enabled get their dates updated

        Date Sources:
        - Purchasing: PO date_order (Order Date)
        - Production: MO date_start (Start Date)
        - Delivery: DO scheduled_date (Scheduled Date)
        """
        for task in self:
            if not task.project_id:
                continue

            project = task.project_id
            all_dates = []
            automation_enabled = False

            # Collect dates from Purchase Orders
            if task.is_auto_purchasing_task:
                automation_enabled = True
                pos = self.env['purchase.order'].search([
                    ('project_id', '=', project.id),
                    ('date_order', '!=', False),
                    ('state', 'in', ['purchase', 'done'])  # Only confirmed POs
                ])
                if pos:
                    all_dates.extend(pos.mapped('date_order'))

            # Collect dates from Manufacturing Orders
            if task.is_auto_production_task:
                automation_enabled = True
                mos = self.env['mrp.production'].search([
                    ('project_id', '=', project.id),
                    ('date_start', '!=', False),
                ])
                if mos:
                    all_dates.extend(mos.mapped('date_start'))

            # Collect dates from Stock Pickings (Delivery Orders)
            if task.is_auto_delivery_task:
                automation_enabled = True
                pickings = self.env['stock.picking'].search([
                    ('project_id', '=', project.id),
                    ('picking_type_code', '=', 'outgoing'),  # Only delivery orders
                    ('scheduled_date', '!=', False),
                ])
                if pickings:
                    all_dates.extend(pickings.mapped('scheduled_date'))

            # Update task dates
            if all_dates:
                task.planned_date_begin = min(all_dates)
                task.date_deadline = max(all_dates)
            elif automation_enabled:
                # If automation is enabled but no orders found, clear the dates
                # This handles the case where a project is created from a template
                # and the template dates are copied over.
                task.planned_date_begin = False
                task.date_deadline = False

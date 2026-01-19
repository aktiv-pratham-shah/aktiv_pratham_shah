# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        help="Link this Manufacturing Order to a project for automatic task date updates."
    )

    def _infer_project_from_sale_order(self):
        """
        Attempt to find and set the project_id from the related Sale Order (via origin).
        """
        for production in self:
            if not production.project_id and production.origin:
                # Try to find SO by name (origin often contains SO name)
                so = self.env['sale.order'].search([('name', '=', production.origin)], limit=1)
                if so and so.project_id:
                    production.project_id = so.project_id

    def write(self, vals):
        """
        Override write to trigger task date updates when MO is modified.
        """
        res = super(MrpProduction, self).write(vals)

        # Try to infer project if missing
        if not self.project_id:
            self._infer_project_from_sale_order()

        # Trigger update if project or state changes
        if 'project_id' in vals or 'state' in vals or self.project_id:
            self._update_related_production_tasks()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to trigger task date updates when MO is created.
        """
        productions = super(MrpProduction, self).create(vals_list)
        productions._infer_project_from_sale_order()
        productions._update_related_production_tasks()
        return productions

    def _update_related_production_tasks(self):
        """
        Find and update all production tasks related to this MO's project.
        """
        for production in self:
            if not production.project_id:
                continue

            # Find production tasks in this project
            production_tasks = self.env['project.task'].search([
                ('project_id', '=', production.project_id.id),
                ('is_auto_production_task', '=', True)
            ])

            # Update task dates
            production_tasks._update_task_dates_from_orders()

    def button_plan(self):
        """
        Override button_plan to update task dates when MO is planned.
        """
        res = super(MrpProduction, self).button_plan()
        self._update_related_production_tasks()
        return res

from odoo import api, fields, models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    project_type = fields.Selection([
        ('full_project', 'Full Project (RE + NRE)'),
        ('re_only', 'RE Only')
    ], string="Project Type", help="Select the project type to apply the corresponding template.")

    @api.model_create_multi
    def create(self, vals_list):
        projects = super(ProjectProject, self).create(vals_list)
        for project in projects:
            if project.project_type:
                project._apply_project_template()
        return projects

    def write(self, vals):
        res = super(ProjectProject, self).write(vals)
        if 'project_type' in vals:
            for project in self:
                # Only apply if tasks are empty? Or always?
                # Usually applying a template is a one-time thing.
                # But if they change it, maybe they want to add the missing tasks?
                # For now, let's only do it on create or if explicitly requested.
                # But the user asked about "create new project", so create is the priority.
                # I'll leave write alone for now to avoid duplicating tasks if they toggle the field.
                pass
        return res

    def _apply_project_template(self):
        self.ensure_one()
        template_name = False
        if self.project_type == 'full_project':
            template_name = "Full Project (RE + NRE)"
        elif self.project_type == 're_only':
            template_name = "RE Only"

        if template_name:
            # Find template project
            # We assume the templates are active or inactive projects with these exact names
            template = self.search([('name', '=', template_name)], limit=1)

            if template:
                # Copy tasks from template to this project
                for task in template.task_ids:
                    task.copy({
                        'project_id': self.id,
                        'name': task.name,  # Keep original name
                        'display_project_id': self.id
                    })

# models/sale_order.py

from odoo import api, fields, models


class SaleOrder(models.Model):
    """
    Inherit the sale.order model to add custom fields for Environmental Lab Testing.
    These fields are specific to the Belement company and will be displayed in a new tab
    on the quotation form. The fields include catalog number, serial number, dimensions
    with unit of measure, weight with unit of measure, UUT quantity, UUT name, and a product picture.
    A computed field checks if the company is Belement to conditionally show the tab.
    """
    _inherit = 'sale.order'

    def _default_dimension_uom(self):
        return self.env['uom.uom'].search([
            ('name', '=', 'mm'),
            ('category_id', '=', self.env.ref('uom.uom_categ_length').id)
        ], limit=1)

    catalog_no = fields.Char(string="Catalog No.")
    serial_no = fields.Char(string="Serial No.")
    dimension_x = fields.Float(string="Depth (X)")
    dimension_y = fields.Float(string="Width (Y)")
    dimension_z = fields.Float(string="Height (Z)")
    uom_dimension = fields.Many2one(
        comodel_name='uom.uom',
        string="Dimension UoM",
        default=lambda self: self._default_dimension_uom(),
    )
    weight = fields.Float(string="Weight")
    uom_weight = fields.Many2one(
        comodel_name='uom.uom',
        string="Weight UoM",
    )
    uut_qty = fields.Char(string="UUT Qty")
    uut_name = fields.Char(string="UUT Name")
    picture = fields.Binary(string="Picture", attachment=True)

    is_belement = fields.Boolean(
        string="Is Belement Company",
        compute='_compute_is_belement'
    )

    show_lab_testing_tab = fields.Boolean(
        string="Show Environmental Lab Testing Tab",
        compute="_compute_show_lab_testing_tab",
        store=True
    )

    add_env_lab_testing = fields.Boolean(
        string="Add to Quotation",
        default=True,
        help="If enabled, Environmental Lab Testing table will be shown in the quotation PDF."
    )

    @api.depends('company_id')
    def _compute_show_lab_testing_tab(self):
        for order in self:
            order.show_lab_testing_tab = order.company_id.id == 1

    @api.depends('company_id')
    def _compute_is_belement(self):
        """
        Compute whether the sale order belongs to the Belement company based on the company name.
        """
        for order in self:
            order.is_belement = order.company_id.name == 'באלמנט אנליזה הנדסית בע״מ'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to inject copy logic.

        - Runs ONLY for company_id = 1
        - Copies CRM description into crm_notes field
        - Copies attachments from crm.lead → sale.order
        """
        sale_orders = super(SaleOrder, self).create(vals_list)

        for so in sale_orders:

            # ----------------------------------------------------
            # RUN CUSTOMIZATION ONLY FOR COMPANY ID = 1
            # ----------------------------------------------------
            if so.company_id.id != 1:
                continue

            lead = so.opportunity_id
            if not lead:
                continue

            # ----------------------------------------------------
            # Copy attachments from Opportunity → Quotation
            # ----------------------------------------------------
            try:
                Attachment = self.env['ir.attachment']
                attachments = Attachment.search([
                    ('res_model', '=', 'crm.lead'),
                    ('res_id', '=', lead.id),
                ])

                for at in attachments:
                    at.copy({
                        'res_model': 'sale.order',
                        'res_id': so.id,
                    })
            except Exception:
                _logger = self.env['ir.logging']
                _logger.create({
                    'name': 'sale_crm_copy_notes_attachments',
                    'type': 'server',
                    'level': 'ERROR',
                    'message': 'Failed to copy attachments from crm.lead %s to sale.order %s'
                               % (lead.id, so.id),
                    'path': 'sale_crm_copy_notes_attachments',
                })

        return sale_orders

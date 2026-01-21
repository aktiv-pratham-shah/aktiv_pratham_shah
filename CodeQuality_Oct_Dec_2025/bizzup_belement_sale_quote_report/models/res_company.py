from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    header_logo = fields.Binary(string="Header Logo Left", attachment=True)
    header_logo_2 = fields.Binary(string="Header Logo Right", attachment=True)

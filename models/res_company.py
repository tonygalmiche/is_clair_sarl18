# -*- coding: utf-8 -*-
from odoo import api, fields, models  

class res_company(models.Model):
    _inherit = "res.company"

    is_penalite_retard           = fields.Text('Pénalités de retard')
    is_indemnite_forfaitaire     = fields.Text('Indemnité forfaitaire de recouvrement')
    is_clause_de_reserve         = fields.Text('Clause de réserve de propriété')
    is_attribution_de_competence = fields.Text('Attribution de compétence territoriale')

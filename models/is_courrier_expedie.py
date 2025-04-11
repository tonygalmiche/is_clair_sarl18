# -*- coding: utf-8 -*-
from odoo import fields, models  # type: ignore


class IsCourrierExpedie(models.Model):
    _name='is.courrier.expedie'
    _description = "Courrier expédié"
    _order='date desc'
    _rec_name='date'

    date = fields.Datetime('Date', required=True, index=True, default=fields.Datetime.now)
    sens = fields.Selection([
        ('expedie', 'Expédié'),
        ('recu'   , 'Recu'),
    ], 'Sens', default='expedie', required=True)
    partner_id = fields.Many2one('res.partner' , 'Destinataire', required=True)
    affaire_id = fields.Many2one('is.affaire', 'Affaire')
    invoice_id = fields.Many2one('account.move', 'Facture')
    payment_id = fields.Many2one('account.payment', 'Paiement')
    traite_id  = fields.Many2one('is.traite', 'Traite')
    objet      = fields.Char('Objet', required=True)
    montant    = fields.Float("Montant", digits=(14,2), required=True)

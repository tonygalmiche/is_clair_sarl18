# -*- coding: utf-8 -*-
from odoo import api, fields, models  
import re


_TYPE_PAIEMENT=[
    ('traite'      , 'Traite'),
    ('virement'    , 'Virement'),
    ('cheque'      , 'Chèque'),
    ('prelevement' , 'Prélèvement automatique'),
]


class IsStatut(models.Model):
    _name='is.statut'
    _description = "Statut"
    _order='name'

    name = fields.Char('Statut', required=True, index=True)


class IsProfil(models.Model):
    _name='is.profil'
    _description = "Profil"
    _order='name'

    name = fields.Char('Profil', required=True, index=True)


class IsOrigine(models.Model):
    _name='is.origine'
    _description = "Origine DP"
    _order='name'

    name = fields.Char('Origine DP', required=True, index=True)


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_statut_id                = fields.Many2one('is.statut' , 'Statut')
    is_profil_id                = fields.Many2one('is.profil' , 'Profil')
    is_origine_id               = fields.Many2one('is.origine', 'Origine DP')
    is_condition_tarifaire      = fields.Text('Conditions tarifaire', help="Informations sur les conditions tarifaires affichées sur la commande")
    is_banque_id                = fields.Many2one('account.journal', 'Banque par défaut', domain=[('type','=','bank')])
    is_compte_auxiliaire        = fields.Char('Compte auxiliaire fournisseur', help="Code du fournisseur pour l'export en compta")
    is_compte_auxiliaire_client = fields.Char('Compte auxiliaire client'     , help="Code du client pour l'export en compta")
    is_modele_commande_id       = fields.Many2one('is.modele.commande' , 'Modèle de commande')
    is_adresse                  = fields.Text("Adresse complète", store=True, readonly=True, compute='_compute_is_adresse')
    is_affaire_ids              = fields.One2many('is.affaire', 'client_id', 'Affaires')
    is_sale_order_ids           = fields.One2many('sale.order', 'partner_id', 'Commandes client')
    is_type_paiement            = fields.Selection(_TYPE_PAIEMENT, 'Type de paiement')
    is_contact_relance_facture_id = fields.Many2one('res.partner', 'Contact facture')
    is_contact_demande_prix_id  = fields.Many2one('res.partner', 'Contact demande de prix', help="Contact utilisé pour l'envoi des demandes de prix simplifiées")
    is_article_demande_prix_ids = fields.Many2many('product.product', 'res_partner_product_demande_prix_rel', 'partner_id', 'product_id', string="Articles demande de prix", help="Liste des articles disponibles pour les demandes de prix simplifiées")
    

    @api.depends('name', 'street','street2','city','zip')
    def _compute_is_adresse(self):
        for obj in self:
            adresse = '%s\n%s\n%s'%((obj.name or ''), (obj.street or ''), (obj.street2 or ''))
            if obj.zip or obj.city:
                adresse += '\n%s - %s'%((obj.zip or ''), (obj.city or ''))
            adresse = re.sub('\\n+','\n',adresse) # Supprimer les \n en double
            obj.is_adresse = adresse


    def creer_modele_commande(self):
        for obj in self:
            vals={
                'name'  : obj.name,
            }
            modele=self.env['is.modele.commande'].create(vals)
            obj.is_modele_commande_id = modele.id
            modele.initialiser_action()


# -*- coding: utf-8 -*-
from odoo import api, fields, models  # type: ignore
from random import randint
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class IsSuiviTresorerie(models.Model):
    _name='is.suivi.tresorerie'
    _description = "Suivi trésorerie"
    _rec_name = 'mois'
    _order='mois desc'

    mois          = fields.Char('Mois', required=True, index=True)
    montant_achat = fields.Float('Montant achats dus')
    montant_vente = fields.Float('Montant factures client en attente')
    solde         = fields.Float('Solde')
    active        = fields.Boolean('Actif', default=True)
    commentaire   = fields.Text('Commentaire')
    

    def actualiser_suivi_tresorerie_action(self):

        #** Factures de ventes ************************************************
        domain=[
            ('move_type'    ,'in' , ['out_invoice','out_refund']),
            ('state'        ,'=' , 'posted'),
            ('payment_state','!=', 'paid'),
        ]
        invoices = self.env['account.move'].search(domain)
        res={}
        for invoice in invoices:
            mois = str(invoice.invoice_date_due or '')[0:7]
            if mois not in res:
                res[mois]={'montant_achat':0, 'montant_vente':0}
            res[mois]['montant_vente']+=invoice.amount_residual_signed

        #** Factures d'achats *************************************************
        domain=[
            ('move_type'    ,'in' , ['in_invoice','in_refund']),
            ('state'        ,'=' , 'posted'),
            ('payment_state','!=', 'paid'),
        ]
        invoices = self.env['account.move'].search(domain)
        for invoice in invoices:
            mois = str(invoice.invoice_date_due or '')[0:7]
            if mois not in res:
                res[mois]={'montant_achat':0, 'montant_vente':0}
            res[mois]['montant_achat']+=invoice.amount_residual_signed

        #** Mise à jour des données *******************************************
        for mois in res:
            montant_achat = -res[mois]['montant_achat']
            montant_vente = res[mois]['montant_vente']
            solde = montant_achat-montant_vente
            vals={
                'mois'         : mois,
                'montant_achat': montant_achat,
                'montant_vente': montant_vente,
                'solde'        : solde,
            }
            domain=[
                ('mois'  ,'=' , mois),
                ('active','in', [True,False])
            ]
            suivis = self.env['is.suivi.tresorerie'].search(domain)
            if len(suivis)>0:
                for suivi in suivis:
                    suivi.write(vals)
            else:
                self.env['is.suivi.tresorerie'].create(vals)


    

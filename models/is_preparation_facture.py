# -*- coding: utf-8 -*-
from odoo import models,fields,api  
from datetime import date


class IsPreparationFacture(models.Model):
    _name='is.preparation.facture'
    _description = "Préparation Facture"
    _order='id desc'
    _rec_name='partner_id'

    partner_id     = fields.Many2one('res.partner' , 'Fournisseur', required=True)
    montant        = fields.Float("Montant", digits=(14,2), store=True, readonly=True, compute='_compute_montant')
    invoice_id     = fields.Many2one('account.move' , 'Facture créée', readonly=True, copy=False)
    ligne_ids      = fields.One2many('purchase.order.line', 'is_preparation_id', 'Lignes', copy=True)


    @api.depends('ligne_ids')
    def _compute_montant(self):
        for obj in self:
            montant=0
            sequence = 10
            for line in obj.ligne_ids:
                if line.is_sequence_facturation>=sequence:
                    sequence = line.is_sequence_facturation+10

            for line in obj.ligne_ids:
                qt = line.product_qty - line.qty_invoiced 
                if line.is_qt_a_facturer<=0:
                    line.is_qt_a_facturer = qt
                    line.is_sequence_facturation = sequence
                    sequence+=10
                line.is_montant_a_facturer = line.is_qt_a_facturer * line.price_unit
                montant+=line.is_montant_a_facturer
            obj.montant = montant


    def creer_facture_action(self):
        for obj in self:
            #** Création des lignes *******************************************
            invoice_line_ids=[]
            for line in obj.ligne_ids:
                taxes = line.product_id.supplier_taxes_id
                taxes = obj.partner_id.property_account_position_id.map_tax(taxes)
                tax_ids=[]
                for tax in taxes:
                   tax_ids.append(tax.id)
                vals={
                    'sequence'  : line.is_sequence_facturation,
                    'product_id': line.product_id.id,
                    'name'      : line.name,
                    'quantity'  : line.is_qt_a_facturer,
                    'purchase_line_id': line.id,
                    'price_unit'      : line.price_unit,
                    'tax_ids'         : [(6, 0, tax_ids)],
                    'is_affaire_id'   : line.order_id.is_affaire_id.id,
                }
                invoice_line_ids.append((0, 0, vals))


            #** Création entête facture ***************************************
            vals={
                'invoice_date'      : date.today(),
                'partner_id'        : obj.partner_id.id,
                'fiscal_position_id': obj.partner_id.property_account_position_id.id,
                'move_type'         : 'in_invoice',
                'invoice_line_ids'  : invoice_line_ids,
            }

            print(vals)


            move=self.env['account.move'].create(vals)
            move.action_post()
            obj.invoice_id=move.id

            res= {
                'name': obj.partner_id,
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': move.id,
                'type': 'ir.actions.act_window',
                'domain': [('type','=','in_invoice')],
            }
            return res

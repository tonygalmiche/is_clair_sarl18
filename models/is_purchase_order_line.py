# -*- coding: utf-8 -*-
from odoo import api, fields, models             
from odoo.tools.sql import drop_view_if_exists   


class is_purchase_order_line(models.Model):
    _name='is.purchase.order.line'
    _description='is.purchase.order.line'
    _order='id desc'
    _auto = False


    order_id               = fields.Many2one('purchase.order', 'Commande')
    partner_id             = fields.Many2one('res.partner', 'Client')
    is_affaire_id          = fields.Many2one('is.affaire', 'Affaire')
    is_date                = fields.Date('Date Cde')
    is_date_livraison      = fields.Date('Date de livraison')
    product_id             = fields.Many2one('product.product', 'Variante')
    product_tmpl_id        = fields.Many2one('product.template', 'Article')
    description  = fields.Text('Description')

    product_qty         = fields.Float('Quantité')
    product_uom             = fields.Many2one('uom.uom', 'Unité')
    price_unit         = fields.Float('Prix unitaire')
    price_subtotal         = fields.Float('Montant')

    is_famille_id      = fields.Many2one('is.famille', 'Famille')
    is_sous_famille_id = fields.Many2one('is.sous.famille', 'Sous-famille')
    is_finition_id     = fields.Many2one('is.finition'  , 'Finition')
    is_traitement_id   = fields.Many2one('is.traitement', 'Traitement')


    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE view is_purchase_order_line AS (
                select  
                    pol.id,
                    pol.order_id,
                    COALESCE(po.is_date,po.create_date)::DATE is_date,
                    po.partner_id,
                    po.is_affaire_id,
                    po.is_date_livraison,
                    pol.product_id,
                    pol.name description,
                    pol.product_qty,
                    pol.product_uom,
                    pol.price_unit,
                    pol.price_subtotal,
                    pt.is_famille_id,
                    pt.is_sous_famille_id,
                    pol.is_finition_id,
                    pol.is_traitement_id,
                    pp.product_tmpl_id
                from purchase_order po inner join purchase_order_line pol on po.id=pol.order_id
                                       inner join product_product      pp on pol.product_id=pp.id
                                       inner join product_template     pt on pp.product_tmpl_id=pt.id
                                       inner join res_partner          rp on po.partner_id=rp.id
                where po.state!='cancel'
            )
        """)

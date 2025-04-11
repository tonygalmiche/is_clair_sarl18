# -*- coding: utf-8 -*-
from odoo import api, fields, models  # type: ignore


class IsModeleCommandeLigne(models.Model):
    _name = 'is.modele.commande.ligne'
    _description = "Lignes des modèles de commandes"
    _order='modele_id,sequence'

    modele_id   = fields.Many2one('is.modele.commande', 'Modèle de commandes', required=True, ondelete='cascade')
    sequence    = fields.Integer('Séquence')
    product_id  = fields.Many2one('product.product', 'Article', required=True)
    description = fields.Text('Description')
    qt_cde      = fields.Float(string='Qt commandée', help="quantité commandée au moment de l'initialisation", readonly=True)


class IsModeleCommande(models.Model):
    _name        = 'is.modele.commande'
    _description = "Modèle de commandes"
    _order       ='name'

    name       = fields.Char('Nom du modèle', required=True)
    ligne_ids  = fields.One2many('is.modele.commande.ligne', 'modele_id', 'Lignes')


    def initialiser_action(self):
        cr = self._cr
        for obj in self:
            filtre=[
                ('is_modele_commande_id','=',obj.id),
            ]
            partners = self.env['res.partner'].search(filtre)
            if len(partners)>0:
                obj.ligne_ids.unlink()
                ids=[]
                for partner in partners:
                    ids.append("'%s'"%(partner.id))
                ids=','.join(ids)
                sql="""
                    SELECT  
                        pol.product_id,
                        sum(pol.product_qty) qt_cde
                    FROM purchase_order po join purchase_order_line pol on po.id=pol.order_id
                                           join product_product pp on pol.product_id=pp.id
                    WHERE 
                        po.state='purchase' and po.partner_id in ("""+ids+""") and pol.product_qty>0
                    GROUP BY pol.product_id 
                """
                cr.execute(sql)
                for row in cr.dictfetchall():
                    vals={
                        'modele_id' : obj.id,
                        'product_id': row["product_id"],
                        'qt_cde'    : row["qt_cde"],
                        'sequence'  : -10*row["qt_cde"],
                    }
                    self.env['is.modele.commande.ligne'].create(vals)


 
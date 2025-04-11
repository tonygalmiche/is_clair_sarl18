# -*- coding: utf-8 -*-
from odoo import fields, models, api  # type: ignore


class IsFamille(models.Model):
    _name='is.famille'
    _description = "Famille"
    _order='name'

    name = fields.Char('Famille', required=True, index=True)

    sous_famille_ids = fields.Many2many('is.sous.famille'   , 'is_famille_sous_famille_rel'   , 'famille_id', 'sous_famille_id', string="Sous-familles")

    is_longueur             = fields.Boolean("Longueur")
    is_largeur_utile        = fields.Boolean("Largeur utile (mm)")
    is_surface_panneau      = fields.Boolean("Surface Panneau")
    is_surface_palette      = fields.Boolean("Surface Palette")
    is_poids                = fields.Boolean("Poids Unité")
    is_poids_rouleau        = fields.Boolean("Poids Rouleau")
    is_ondes                = fields.Boolean("Ondes")
    is_resistance_thermique = fields.Boolean("Résistance thermique (R)")
    is_lambda               = fields.Boolean("Lambda ʎ (W/m.K)")
    is_lg_mini_forfait      = fields.Boolean("Longueur mini forfait coupe")
    is_forfait_coupe_id     = fields.Boolean("Forfait coupe")
    is_conditionnement      = fields.Boolean("Conditionnement")
    is_ordre_tri            = fields.Boolean("Ordre de tri")
    is_sous_article_ids     = fields.Boolean("Sous-articles")
    colisage                = fields.Boolean("Accès au colisage dans les commandes")
    is_eco_contribution     = fields.Boolean("Montant Eco-contribution")



class IsSousFamille(models.Model):
    _name='is.sous.famille'
    _description = "Sous-famille"
    _order='name'

    name = fields.Char('Sous-famille', required=True, index=True)

    famille_ids = fields.Many2many('is.famille', 'is_famille_sous_famille_rel', 'sous_famille_id' , 'famille_id', string="Familles")


class IsSousArticle(models.Model):
    _name='is.sous.article'
    _description = "Sous-articles"
    _order='product_tmpl_id, product_id'

    product_tmpl_id = fields.Many2one('product.template', 'Article parent', required=True, ondelete='cascade')
    product_id      = fields.Many2one('product.product' , 'Sous-Article', required=True)
    quantite        = fields.Float("Quantité", default=1)


class product_product(models.Model):
    _inherit = "product.product"

    def evolution_prix_achat_action(self):
        for obj in self:
            return obj.product_tmpl_id.evolution_prix_achat_action()


class product_template(models.Model):
    _inherit = "product.template"
    _order="name"

    is_tache                = fields.Boolean("Tache")
    is_famille_id           = fields.Many2one('is.famille', 'Famille')
    is_sous_famille_id      = fields.Many2one('is.sous.famille', 'Sous-famille')

    is_longueur             = fields.Integer("Longueur")
    is_largeur_utile        = fields.Integer("Largeur utile (mm)")
    is_surface_panneau      = fields.Float("Surface Panneau", digits=(14,2))
    is_surface_palette      = fields.Float("Surface Palette", digits=(14,2))
    is_poids                = fields.Float("Poids Unité"        , digits=(14,2))
    is_poids_rouleau        = fields.Float("Poids Rouleau", digits=(14,2))
    is_ondes                = fields.Integer("Ondes")
    is_resistance_thermique = fields.Float("Résistance thermique (R)", digits=(14,2))
    is_lambda               = fields.Float("Lambda ʎ (W/m.K)"        , digits=(14,3))
    is_lg_mini_forfait      = fields.Integer("Longueur mini forfait coupe")
    is_conditionnement      = fields.Char("Conditionnement")
    is_forfait_coupe_id     = fields.Many2one('product.product', 'Forfait coupe')
    is_ordre_tri            = fields.Integer("Ordre de tri")
    is_sous_article_ids     = fields.One2many('is.sous.article', 'product_tmpl_id', 'Sous-articles')
    is_eco_contribution     = fields.Float("Montant Eco-contribution", digits=(14,6), help='Si ce montant est renseigné, cela ajoutera automatiquement une ligne sur la commande')

    is_longueur_vsb             = fields.Boolean("Longueur vsb"                   , store=False, readonly=True, compute='_compute_vsb')
    is_largeur_utile_vsb        = fields.Boolean("Largeur utile (mm) vsb"         , store=False, readonly=True, compute='_compute_vsb')
    is_surface_panneau_vsb      = fields.Boolean("Surface Panneau vsb"            , store=False, readonly=True, compute='_compute_vsb')
    is_surface_palette_vsb      = fields.Boolean("Surface Palette vsb"            , store=False, readonly=True, compute='_compute_vsb')
    is_poids_vsb                = fields.Boolean("Poids Unité vsb"                , store=False, readonly=True, compute='_compute_vsb')
    is_poids_rouleau_vsb        = fields.Boolean("Poids Rouleau vsb"              , store=False, readonly=True, compute='_compute_vsb')
    is_ondes_vsb                = fields.Boolean("Ondes vsb"                      , store=False, readonly=True, compute='_compute_vsb')
    is_resistance_thermique_vsb = fields.Boolean("Résistance thermique (R) vsb"   , store=False, readonly=True, compute='_compute_vsb')
    is_lambda_vsb               = fields.Boolean("Lambda ʎ (W/m.K) vsb"           , store=False, readonly=True, compute='_compute_vsb')
    is_lg_mini_forfait_vsb      = fields.Boolean("Longueur mini forfait coupe vsb", store=False, readonly=True, compute='_compute_vsb')
    is_conditionnement_vsb      = fields.Boolean("Conditionnement vsb"            , store=False, readonly=True, compute='_compute_vsb')
    is_forfait_coupe_id_vsb     = fields.Boolean("Forfait coupe vsb"              , store=False, readonly=True, compute='_compute_vsb')
    is_ordre_tri_vsb            = fields.Boolean("Ordre de tri vsb"               , store=False, readonly=True, compute='_compute_vsb')
    is_sous_article_ids_vsb     = fields.Boolean("Sous-articles vsb"              , store=False, readonly=True, compute='_compute_vsb')
    is_fournisseur_id           = fields.Many2one('res.partner', 'Fournisseur par défaut', store=True, readonly=True, compute='_compute_is_fournisseur_id')
    is_eco_contribution_vsb     = fields.Boolean("Montant Eco-contribution vsb"   , store=False, readonly=True, compute='_compute_vsb')



    def evolution_prix_achat_action(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            SQL="""
                SELECT is_date, max(id)
                FROM is_purchase_order_line
                WHERE product_tmpl_id=%s and price_unit>0
                GROUP BY is_date
            """
            cr.execute(SQL,[obj.id])
            ids=[]
            for row in cr.fetchall():
                ids.append(row[1])
            graph_id = self.env.ref('is_clair_sarl18.is_purchase_order_line_price_unit_graph').id
            return {
                "name": "Achats ",
                "view_mode": "graph,tree,form,pivot",
                "res_model": "is.purchase.order.line",
                "domain": [
                    ("id","in",ids),
                ],
                "type": "ir.actions.act_window",
                "views"    : [[graph_id, "graph"], [False, "tree"], [False, "form"], [False, "pivot"]],
            }





    @api.depends('seller_ids')
    def _compute_is_fournisseur_id(self):
        for obj in self:
            is_fournisseur_id=False
            for line in obj.seller_ids:
                is_fournisseur_id = line.name.id
                break
            obj.is_fournisseur_id =is_fournisseur_id


    @api.depends('is_famille_id')
    def _compute_vsb(self):
        for obj in self:
            vsb=False
            if obj.is_famille_id.is_longueur:
                vsb=True
            obj.is_longueur_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_largeur_utile:
                vsb=True
            obj.is_largeur_utile_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_surface_panneau:
                vsb=True
            obj.is_surface_panneau_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_surface_palette:
                vsb=True
            obj.is_surface_palette_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_poids:
                vsb=True
            obj.is_poids_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_poids_rouleau:
                vsb=True
            obj.is_poids_rouleau_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_ondes:
                vsb=True
            obj.is_ondes_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_resistance_thermique:
                vsb=True
            obj.is_resistance_thermique_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_lambda:
                vsb=True
            obj.is_lambda_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_lg_mini_forfait:
                vsb=True
            obj.is_lg_mini_forfait_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_conditionnement:
                vsb=True
            obj.is_conditionnement_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_forfait_coupe_id:
                vsb=True
            obj.is_forfait_coupe_id_vsb = vsb

            vsb=False
            if obj.is_famille_id.is_ordre_tri:
                vsb=True
            obj.is_ordre_tri_vsb = vsb
            
            vsb=False
            if obj.is_famille_id.is_sous_article_ids:
                vsb=True
            obj.is_sous_article_ids_vsb = vsb
            vsb=False
            if obj.is_famille_id.is_eco_contribution:
                vsb=True
            obj.is_eco_contribution_vsb = vsb

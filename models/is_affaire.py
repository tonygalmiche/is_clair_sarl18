# -*- coding: utf-8 -*-
from odoo import api, fields, models  # type: ignore
from random import randint
from datetime import datetime, date, timedelta
import re
import logging
_logger = logging.getLogger(__name__)


class IsNatureTravaux(models.Model):
    _name='is.nature.travaux'
    _description = "Nature des travaux"
    _order='name'

    def _get_default_color(self):
        return randint(1, 11)

    name  = fields.Char('Nature des travaux', required=True, index=True)
    color = fields.Integer('Couleur', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class IsTypeTravaux(models.Model):
    _name='is.type.travaux'
    _description = "Type des travaux"
    _order='name'

    def _get_default_color(self):
        return randint(1, 11)

    name  = fields.Char('Type des travaux', required=True, index=True)
    color = fields.Integer('Couleur', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class IsSpecificite(models.Model):
    _name='is.specificite'
    _description = "Spécificité"
    _order='name'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Spécificité', required=True, index=True)
    color = fields.Integer('Couleur', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class IsAffaireAnalyse(models.Model):
    _name='is.affaire.analyse'
    _description = "Analyse de commandes par affaire"

    affaire_id       = fields.Many2one('is.affaire', 'Affaire', required=True, ondelete='cascade')
    fournisseur_id   = fields.Many2one('res.partner' , 'Fournisseur')
    famille_id       = fields.Many2one('is.famille', 'Famille')
    intitule         = fields.Char('Intitulé')
    budget           = fields.Float("Budget"          , digits=(14,2))
    montant_cde      = fields.Float("Montant Commandé", digits=(14,2))
    montant_fac      = fields.Float("Montant Facturé" , digits=(14,2))
    ecart            = fields.Float("Ecart Cde/Fac"   , digits=(14,2))
    ecart_pourcent   = fields.Float("% Ecart"         , digits=(14,2))
    ecart_budget_cde = fields.Float("Ecart Budget/Cde", digits=(14,2))
    ecart_budget_fac = fields.Float("Ecart Budget/Fac", digits=(14,2))


    def liste_achat_famille_commande_action(self):
        for obj in self:
            return {
                "name": "Lignes des commandes ",
                "view_mode": "tree,form",
                "res_model": "purchase.order.line",
                "domain": [
                    ("order_id.is_affaire_id","=",obj.affaire_id.id),
                    ("product_id.is_famille_id","=",obj.famille_id.id),
                    ("order_id.state","=","purchase"),
                ],
                "type": "ir.actions.act_window",
            }


    def liste_achat_fournisseur_commande_action(self):
        for obj in self:
            return {
                "name": "Lignes des commandes ",
                "view_mode": "tree,form",
                "res_model": "purchase.order.line",
                "domain": [
                    ("order_id.is_affaire_id","=",obj.affaire_id.id),
                    ("order_id.partner_id","=",obj.fournisseur_id.id),
                    ("order_id.state","=","purchase"),
                ],
                "type": "ir.actions.act_window",
            }


    def liste_achat_famille_facture_action(self):
        for obj in self:
            tree_id = self.env.ref('is_clair_sarl18.is_account_move_line_tree_view').id
            form_id = self.env.ref('is_clair_sarl18.is_account_move_line_form_view').id
            return {
                "name": "Lignes des factures ",
                "view_mode": "tree,form",
                "res_model": "account.move.line",
                "domain": [
                    ("is_affaire_id","=",obj.affaire_id.id),
                    ("is_famille_id","=",obj.famille_id.id),
                    ("exclude_from_invoice_tab","=",False),
                    ("journal_id","=",2),
                    ("move_id.state","=","posted"),
                ],
                "type": "ir.actions.act_window",
                "views"    : [[tree_id, "tree"],[form_id, "form"]],
            }


    def liste_achat_fournisseur_facture_action(self):
        for obj in self:
            tree_id = self.env.ref('is_clair_sarl18.is_account_move_line_tree_view').id
            form_id = self.env.ref('is_clair_sarl18.is_account_move_line_form_view').id
            return {
                "name": "Lignes des factures ",
                "view_mode": "tree,form",
                "res_model": "account.move.line",
                "domain": [
                    ("is_affaire_id","=",obj.affaire_id.id),
                    ("move_id.partner_id","=",obj.fournisseur_id.id),
                    ("exclude_from_invoice_tab","=",False),
                    ("journal_id","=",2),
                    ("move_id.state","=","posted"),
                ],
                "type": "ir.actions.act_window",
                "views"    : [[tree_id, "tree"],[form_id, "form"]],
            }


class IsAffaireBudgetFamille(models.Model):
    _name='is.affaire.budget.famille'
    _description = "Budget affaire par famille"

    affaire_id = fields.Many2one('is.affaire', 'Affaire', required=True, ondelete='cascade')
    famille_id = fields.Many2one('is.famille', 'Famille', required=False)
    budget     = fields.Float("Budget", digits=(14,2))
    facture    = fields.Float("Montant facturé", digits=(14,2), readonly=True)
    reste      = fields.Float("Reste au budget", digits=(14,2), readonly=True, store=True, compute='_compute_reste')
    solder     = fields.Boolean("Solder", default=False, help="Indiquez ce budget comme soldé, si vous pensez qu'il n'y aura plus de dépenses")
    gain       = fields.Float("Gain/Perte budget", digits=(14,2), readonly=True, store=True, compute='_compute_reste')


    @api.depends('budget','facture','solder')
    def _compute_reste(self):
        for obj in self:
            gain=0
            reste = obj.budget - obj.facture
            if reste<0:
                gain=reste
                reste=0
            else:
                if obj.solder:
                    gain = reste
            obj.reste = reste
            obj.gain = gain


class IsAffaireSalaire(models.Model):
    _name='is.affaire.salaire'
    _description = "Salaires des affaires"

    affaire_id     = fields.Many2one('is.affaire', 'Affaire', required=True, ondelete='cascade')
    importation_id = fields.Many2one('is.import.salaire', 'Importation')
    date           = fields.Date("Date", required=True)
    montant        = fields.Float("Montant", digits=(14,2))


    def view_affaire_action(self):
        for obj in self:
            return {
                "name": "Affaire %s"%(obj.importation_id.name),
                "view_mode": "form",
                "res_model": "is.affaire",
                "res_id"   : obj.affaire_id.id,
                "type": "ir.actions.act_window",
            }



class IsAffaireRemise(models.Model):
    _name='is.affaire.remise'
    _description = "IsAffaireRemise"

    affaire_id = fields.Many2one('is.affaire', 'Affaire', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Remise facturation', required=True, domain=[('is_famille_id.name','=','Facturation')])
    remise     = fields.Float("Remise (%)", digits=(14,2), required=True)
    apres_ttc  = fields.Boolean("Après TTC", default=False, help="Appliquer cette remise après le montant TTC de la facture")
    caution    = fields.Boolean("Caution", default=False)


class IsAffaire(models.Model):
    _name='is.affaire'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Affaire"
    _order='name desc'

    name                = fields.Char("N° d'Affaire", index=True, help="Sous la forme AA-XXXX")
    nom                 = fields.Char("Nom de l'affaire", tracking=True)
    date_creation       = fields.Date("Date de création", default=lambda *a: fields.Date.today(), required=True, tracking=True)
    client_id           = fields.Many2one('res.partner' , 'Client', tracking=True)
    maitre_oeuvre_id    = fields.Many2one('res.partner' , "Maitre d'œuvre", tracking=True)
    street              = fields.Char("Rue", tracking=True)
    street2             = fields.Char("Rue 2", tracking=True)
    zip                 = fields.Char("CP", tracking=True)
    city                = fields.Char("Ville", tracking=True)
    adresse_chantier    = fields.Text('Adresse du chantier', store=True, readonly=True, compute='_compute_adresse_chantier')
    nature_travaux_ids  = fields.Many2many('is.nature.travaux', 'is_affaire_nature_travaux_rel', 'affaire_id', 'nature_id'     , string="Nature des travaux", tracking=True)
    type_travaux_ids    = fields.Many2many('is.type.travaux'  , 'is_affaire_type_travaux_rel'  , 'affaire_id', 'type_id'       , string="Type des travaux", tracking=True)
    specificite_ids     = fields.Many2many('is.specificite'   , 'is_affaire_specificite_rel'   , 'affaire_id', 'specificite_id', string="Spécificités", tracking=True)
    commentaire         = fields.Text("Commentaire", tracking=True)
    contact_chantier_id = fields.Many2one('res.users' , 'Contact chantier', tracking=True)
    analyse_ids         = fields.One2many('is.affaire.analyse'       , 'affaire_id', 'Analyse de commandes')
    budget_famille_ids  = fields.One2many('is.affaire.budget.famille', 'affaire_id', 'Budget par famille')
    active              = fields.Boolean("Active", default=True, tracking=True)
    compte_prorata      = fields.Float("Compte prorata (%)", digits=(14,2), tracking=True)
    retenue_garantie    = fields.Float("Retenue de garantie (%)", digits=(14,2), tracking=True)
    salaire_ids         = fields.One2many('is.affaire.salaire', 'affaire_id', 'Salaires')
    remise_ids          = fields.One2many('is.affaire.remise', 'affaire_id', 'Remises')
    montant_salaire      = fields.Float("Montant salaire"     , digits=(14,2), store=True , readonly=True, compute='_compute_montant_salaire')
    montant_offre        = fields.Float("Montant offre"       , digits=(14,2), readonly=True, help="Total des commandes clients liées à cette affaire")
    vente_facture        = fields.Float("Ventes facturées"    , digits=(14,2), readonly=True, default=0)
    achat_facture        = fields.Float("Achats facturés"     , digits=(14,2), readonly=True, default=0)
    marge_brute          = fields.Float("Marge brute"         , digits=(14,2), readonly=True, default=0)
    montant_budget_achat = fields.Float("Montant budget achat", digits=(14,2), readonly=True, default=0)
    gain_perte_budget    = fields.Float("Gain/Perte budget"   , digits=(14,2), readonly=True, default=0)
    marge_previsionnelle = fields.Float("Marge prévisionnelle", digits=(14,2), readonly=True, default=0)
    type_affaire = fields.Selection([
        ('chantier' , 'Chantier'),
        ('entretien', 'Entretien'),
        ('sav'      , 'SAV'),
        ('interne'  , 'Interne'),
    ], 'Type affaire', index=True, default="chantier", required=True, tracking=True)
    state = fields.Selection([
        ('offre'   , 'Offre'),
        ('commande', 'Commande'),
        ('terminee', 'Terminée'),
    ], 'Etat', index=True, default="offre", required=True, tracking=True)


    def write(self, vals):
        state=self.state
        res = super(IsAffaire, self).write(vals)
        if 'state' in vals:
            if vals['state']=='commande' and state=='offre':
                self.creer_chantier_affaire_action()
        return res


    def actualiser_marge_affaire_cron(self):
        self.env['is.affaire'].search([], order="name,id").actualiser_marge()


    @api.depends('name')
    def actualiser_marge(self):
        for obj in self:
            _logger.info("actualiser_marge : %s (%s)"%(obj.name, obj.id))
            obj._update_gain_perte_budget()
            obj._update_montant_offre()
            obj._update_vente_facture()
            obj._update_achat_facture()
            obj._update_budget_famille(analyse=False)
            marge_brute = obj.vente_facture - obj.achat_facture - obj.montant_salaire
            obj.marge_brute = marge_brute
            obj.marge_previsionnelle = obj.montant_offre - obj.montant_budget_achat + obj.gain_perte_budget


    def _update_gain_perte_budget(self):
        for obj in self:
            budget = 0
            gain = 0
            for line in obj.budget_famille_ids:
                gain+=line.gain
                budget+=line.budget
            obj.montant_budget_achat = budget
            obj.gain_perte_budget = gain


    def _update_montant_offre(self):
        for obj in self:
            val = 0
            filtre=[('is_affaire_id', '=', obj.id),('state', '!=', 'cancel')]
            orders = self.env['sale.order'].search(filtre)
            for order in orders:
                val+=order.amount_untaxed
            obj.montant_offre = val


    def _update_achat_facture(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            val=0
            if isinstance(obj.id, int):
                SQL="""
                    SELECT sum(aml.price_subtotal)
                    FROM account_move_line aml join account_move am on aml.move_id=am.id
                    WHERE aml.is_affaire_id=%s and aml.exclude_from_invoice_tab='f' and aml.journal_id=2 and am.state='posted'
                """
                cr.execute(SQL,[obj.id])
                for row in cr.fetchall():
                    val = row[0]
            obj.achat_facture = val


    def _update_vente_facture(self):
        for obj in self:
            val=0
            filtre=[('state','=','posted'), ('is_affaire_id','=',obj.id),('journal_id','=', 1)]
            invoices = self.env['account.move'].search(filtre)
            for invoice in invoices:
                val+=invoice.amount_untaxed_signed
            obj.vente_facture = val


    @api.depends('street','street2','city','zip')
    def _compute_adresse_chantier(self):
        for obj in self:
            adresse = '%s\n%s'%((obj.street or ''), (obj.street2 or ''))
            if obj.zip or obj.city:
                adresse += '\n%s - %s'%((obj.zip or ''), (obj.city or ''))
            adresse = re.sub('\\n+','\n',adresse) # Supprimer les \n en double
            obj.adresse_chantier = adresse


    @api.depends('salaire_ids','salaire_ids.montant')
    def _compute_montant_salaire(self):
        for obj in self:
            montant = 0
            for line in obj.salaire_ids:
                montant+=line.montant
            obj.montant_salaire = montant


    def ajout_famille_action(self):
        for obj in self:
            familles = self.env['is.famille'].search([])
            for famille in familles:
                vals={
                    "affaire_id": obj.id,
                    "famille_id": famille.id,
                }
                res = self.env['is.affaire.budget.famille'].create(vals)


    def ajout_salaire(self):
        for obj in self:
            vals={
                "affaire_id"    : obj.id,
                "intitule"      : "0-SALAIRES",
                "montant_cde"   : obj.montant_salaire,
                "montant_fac"   : obj.montant_salaire,
                "ecart"         : 0,
                "ecart_pourcent": 0,
            }
            res = self.env['is.affaire.analyse'].sudo().create(vals)




    def analyse_par_fournisseur_action(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            obj.analyse_ids.sudo().unlink()
            SQL="""
                SELECT coalesce(rp.parent_id,po.partner_id),sum(amount_untaxed)
                FROM purchase_order po join res_partner rp on po.partner_id=rp.id
                WHERE is_affaire_id=%s and state='purchase'
                GROUP BY coalesce(rp.parent_id,po.partner_id)
            """
            cr.execute(SQL,[obj.id])
            for row in cr.fetchall():
                partner_id = row[0]
                partner = self.env['res.partner'].browse(partner_id)
                montant_cde = row[1] or 0
                SQL="""
                    SELECT sum(aml.price_subtotal)
                    FROM account_move_line aml join account_move am on aml.move_id=am.id
                                               join res_partner rp on am.partner_id=rp.id
                    WHERE 
                        aml.is_affaire_id=%s and 
                        aml.exclude_from_invoice_tab='f' and 
                        aml.journal_id=2 and 
                        (am.partner_id=%s or rp.parent_id=%s) and
                        am.state='posted'
                """
                cr.execute(SQL,[obj.id, row[0], row[0]])
                montant_fac=ecart=ecart_pourcent=0
                for row2 in cr.fetchall():
                    montant_fac = row2[0] or 0
                ecart=montant_cde-montant_fac
                if montant_fac>0:
                    ecart_pourcent = 100*ecart/montant_fac
                vals={
                    "affaire_id"    : obj.id,
                    "intitule"      : partner.name,
                    "fournisseur_id": partner_id,
                    "montant_cde"   : montant_cde,
                    "montant_fac"   : montant_fac,
                    "ecart"         : ecart,
                    "ecart_pourcent": ecart_pourcent,
                }
                res = self.env['is.affaire.analyse'].sudo().create(vals)
            obj.ajout_salaire()
            return obj.is_affaire_analyse_action("Analyse par fournisseur")


    def _update_budget_famille(self, analyse=False):
        cr,uid,context,su = self.env.args
        for obj in self:
            if analyse:
                obj.analyse_ids.sudo().unlink()
            lines = self.env['is.famille'].search([])
            familles=[]
            for line in lines:
                familles.append(line)
            familles.append(None)
            for famille in familles:
                intitule=""
                famille_id = None
                #** Budget ****************************************************
                budget_famille = False
                budget=0
                if famille:
                    famille_id = famille.id
                    intitule   = famille.name
                    filtre=[('affaire_id', '=', obj.id),('famille_id', '=', famille_id)]
                    lines = self.env['is.affaire.budget.famille'].search(filtre)
                    budget=0
                    for line in lines:
                        budget=line.budget
                        budget_famille = line
                #**************************************************************

                #** Montant Cde ***********************************************
                montant_cde=0
                SQL="""
                    SELECT pt.is_famille_id,sum(pol.price_subtotal)
                    FROM purchase_order po join purchase_order_line pol on po.id=pol.order_id
                                        join product_product pp on pol.product_id=pp.id
                                        join product_template pt on pp.product_tmpl_id=pt.id
                    WHERE po.is_affaire_id=%s and  po.state='purchase'
                """%obj.id
                if famille_id:
                    SQL+=" and pt.is_famille_id=%s "%famille_id
                else:
                    SQL+=" and pt.is_famille_id is null " 
                SQL+="GROUP BY pt.is_famille_id"
                cr.execute(SQL)
                #cr.execute(SQL,[obj.id, famille_id])
                for row in cr.fetchall():
                    montant_cde = row[1] or 0
                ecart_budget_cde = budget-montant_cde
                #**************************************************************

                #** Montant Fac ***********************************************
                SQL="""
                    SELECT sum(aml.price_subtotal)
                    FROM account_move_line aml join account_move am on aml.move_id=am.id
                                               join product_product pp on aml.product_id=pp.id
                                               join product_template pt on pp.product_tmpl_id=pt.id
                    WHERE 
                        aml.is_affaire_id=%s and 
                        aml.exclude_from_invoice_tab='f' and 
                        aml.journal_id=2 and 
                        am.state='posted'
                """%obj.id
                if famille_id:
                    SQL+=" and pt.is_famille_id=%s "%famille_id
                else:
                    SQL+=" and pt.is_famille_id is null " 
                cr.execute(SQL)
                montant_fac=ecart=ecart_pourcent=0
                for row2 in cr.fetchall():
                    montant_fac = row2[0] or 0
                ecart=montant_cde-montant_fac
                if montant_fac>0:
                    ecart_pourcent = 100*ecart/montant_fac
                ecart_budget_fac = budget-montant_fac
                #**************************************************************


                #** Ajout du budget si il n'existe pas ************************
                if not budget_famille and montant_fac>0:
                    if famille:
                        vals={
                            'affaire_id': obj.id,
                            'famille_id': famille.id,
                        }
                        budget_famille = self.env['is.affaire.budget.famille'].sudo().create(vals)
                if budget_famille:
                    budget_famille.facture = montant_fac
                #**************************************************************

                if analyse:
                    if budget!=0 or montant_cde!=0 or montant_fac!=0:
                        vals={
                            "affaire_id": obj.id,
                            "intitule": intitule,
                            "famille_id": famille_id,
                            "budget"    : budget,
                            "montant_cde"     : montant_cde,
                            "montant_fac"   : montant_fac,
                            "ecart"         : ecart,
                            "ecart_pourcent": ecart_pourcent,
                            "ecart_budget_cde": ecart_budget_cde,
                            "ecart_budget_fac": ecart_budget_fac,
                        }
                        res = self.env['is.affaire.analyse'].sudo().create(vals)
            if analyse:
                obj.ajout_salaire()


    def analyse_par_famille_action(self):
        for obj in self:
            obj._update_budget_famille(analyse=True)
            return obj.is_affaire_analyse_action("Analyse par famille")


    def import_budget_famille_action(self):
        cr,uid,context,su = self.env.args
        for obj in self:
            for line in obj.budget_famille_ids:
                SQL="""
                    SELECT sum(sol.product_uom_qty*sol.is_prix_achat)
                    FROM sale_order so join sale_order_line sol on so.id=sol.order_id
                                    join product_product pp on sol.product_id=pp.id
                                    join product_template pt on pp.product_tmpl_id=pt.id
                    WHERE 
                        so.is_affaire_id=%s and 
                        pt.is_famille_id=%s 
                """
                cr.execute(SQL,[obj.id, line.famille_id.id])
                budget=0
                for row in cr.fetchall():
                    budget = row[0] or 0
                line.budget=budget




    def is_affaire_analyse_action(self,name):
        for obj in self:
            return {
                "name": name,
                "view_mode": "tree,form,pivot,graph",
                "res_model": "is.affaire.analyse",
                "res_id"   : obj.id,
                "type": "ir.actions.act_window",
                "domain": [
                    ("affaire_id","=",obj.id),
                ],
            }


    def liste_achat_facture_action(self):
        for obj in self:
            tree_id = self.env.ref('is_clair_sarl18.is_account_move_line_tree_view').id
            form_id = self.env.ref('is_clair_sarl18.is_account_move_line_form_view').id
            return {
                "name": "Lignes de factures ",
                "view_mode": "tree,form",
                "res_model": "account.move.line",
                "domain": [
                    ("is_affaire_id","=",obj.id),
                    ("exclude_from_invoice_tab","=",False),
                    ("journal_id","=",2),
                    ("move_id.state","=","posted"),
                ],
                "type": "ir.actions.act_window",
                "views"    : [[tree_id, "tree"],[form_id, "form"]],
            }


    def liste_vente_facture_action(self):
        for obj in self:
            return {
                "name": "Factures ",
                "view_mode": "tree,form",
                "res_model": "account.move",
                "domain": [
                    ("is_affaire_id","=",obj.id),
                    ("journal_id","=",1),
                ],
                "type": "ir.actions.act_window",
            }
          

    def liste_commandes_action(self):
        for obj in self:
            return {
                "name": "Offres ",
                "view_mode": "tree,form",
                "res_model": "sale.order",
                "domain": [
                    ("is_affaire_id","=",obj.id),
                ],
                "type": "ir.actions.act_window",
            }


    def name_get(self):
        result = []
        for obj in self:

            name=""
            if obj.name and obj.nom:
                name = "[%s] %s"%(obj.name,obj.nom)
            if obj.name and not obj.nom:
                name = "%s"%(obj.name)
            if obj.nom and not obj.name:
                name = "%s"%(obj.nom)
            result.append((obj.id, name))
        return result


    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if args is None:
            args = []

        ids = []
        if len(name) >= 1:
            filtre=[
                '|','|','|','|','|',
                ('name'   , 'ilike', name),
                ('nom'    , 'ilike', name),
                ('street' , 'ilike', name),
                ('street2', 'ilike', name),
                ('zip'    , 'ilike', name),
                ('city'   , 'ilike', name),
            ]
            if name=="[":
                filtre=[('name', '!=', False)]
            if name=="#":
                filtre=[('name', '=', False)]
            ids = list(self._search(filtre + args, limit=limit))

        search_domain = [('name', operator, name)]
        if ids:
            search_domain.append(('id', 'not in', ids))
        ids += list(self._search(search_domain + args, limit=limit))
        return ids


    def creer_chantier_affaire_action(self):
        today = date.today()
        ct=1
        for obj in self:
            if obj.state=='commande' and obj.type_affaire=='chantier':
                for nature in obj.nature_travaux_ids:
                    filtre=[
                        ('affaire_id'       ,'=' , obj.id),
                        ('nature_travaux_id','=' , nature.id),
                        ('active'           ,'in', [True,False]),
                    ]
                    chantiers = self.env['is.chantier'].search(filtre)
                    if len(chantiers)==0:
                        vals={
                            "affaire_id"       : obj.id,
                            "date_debut"       : today + timedelta(days=21),
                            "date_fin"         : today + timedelta(days=24),
                            "nature_travaux_id": nature.id,
                        }
                        chantier = self.env['is.chantier'].create(vals)
                        _logger.info("creer_chantier_affaire_action : %s : %s : %s : %s"%(ct,obj.name,nature.name,chantier.name))
                        ct+=1


class IsImportSalaire(models.Model):
    _name='is.import.salaire'
    _description = "Importation des salaires dans les affaires"
    _order='name desc'

    name        = fields.Date('Date', required=True, index=True)
    importation = fields.Text('Données à importer', help="Faire un copier / coller d'Excel dans ce champ")
    total       = fields.Float('Total importé', readonly=True)
    resultat    = fields.Text('Résultat importation', readonly=True)
    salaire_ids = fields.One2many('is.affaire.salaire', 'importation_id', 'Salaires')


    def importation_salaire_action(self):
        for obj in self:
            lines = obj.importation.split('\n')
            total = 0
            resultat = []
            obj.salaire_ids.unlink()
            for line in lines:
                test=False
                t = line.split('\t')
                if len(t)==2:
                    t2 = t[0].split(' ')
                    if len(t2)>=2:
                        #name    = t[0][0:7].strip()
                        name    = t2[0]
                        montant = t[1]
                        affaires=self.env['is.affaire'].search([('name', '=',name),('name', '!=','')])
                        affaire = False
                        for a in affaires:
                            affaire = a
                            break
                        if affaire:
                            try:
                                montant=float(t[1].replace(',','.'))
                            except:
                                montant=0
                            total+=montant
                            vals={
                                'affaire_id'    : affaire.id,
                                'importation_id': obj.id,
                                'date'          : obj.name,
                                'montant'       : montant,
                            }
                            res = self.env['is.affaire.salaire'].create(vals)
                            test=True
                if test==False and line.strip()!='':
                    resultat.append("Affaire non trouvée => %s"%line)
            if len(resultat)==0:
                resultat = False
            else:
                resultat = "\n".join(resultat)
            obj.resultat = resultat
            obj.total = total



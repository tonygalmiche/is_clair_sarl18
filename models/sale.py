# -*- coding: utf-8 -*-
from odoo import models,fields,api,_                      
from odoo.http import request                           
from odoo.exceptions import UserError, ValidationError  
import datetime
from dateutil.relativedelta import relativedelta
import math
import base64
import os
import openpyxl
import logging
_logger = logging.getLogger(__name__)


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    order_id               = fields.Many2one('sale.order', string='Order Reference', required=False, ondelete='cascade', index=True, copy=False)
    is_section_id          = fields.Many2one('is.sale.order.section', 'Section', index=True, domain="[('order_id','=',order_id)]", copy=False)
    is_facturable_pourcent = fields.Float("% facturable", digits=(14,2), copy=False)
    is_facturable          = fields.Float("Facturable"  , digits=(14,2), store=True, readonly=True, compute='_compute_facturable')
    is_deja_facture        = fields.Float("Déja facturé", digits=(14,2), store=True, readonly=True, compute='_compute_facturable')
    is_a_facturer          = fields.Float("En cours facturable", digits=(14,2), store=True, readonly=True, compute='_compute_facturable')
    is_prix_achat          = fields.Float("Prix d'achat", digits=(14,4))
    is_masquer_ligne       = fields.Boolean("Masquer",default=False,help="Masquer la ligne sur le PDF de la commande")
    is_unite               = fields.Char("Unité")


    @api.depends('order_id.is_invoice_ids','order_id.is_invoice_ids.state','is_facturable_pourcent','price_unit','product_uom_qty')
    def _compute_facturable(self):
        cr = self._cr
        for obj in self:
            is_deja_facture=0
            if not isinstance(obj.id, models.NewId):
                SQL="""
                    SELECT am.move_type,sum(aml.is_a_facturer)
                    FROM account_move_line aml join account_move am on aml.move_id=am.id
                    WHERE aml.is_sale_line_id=%s and am.state!='cancel'
                    GROUP BY am.move_type
                """
                cr.execute(SQL,[obj.id])
                for row in cr.fetchall():


                    sens=1

                    #TODO : Le 14/11/2025, j'ai désactvié ces lignes à cause de l'avoir sur la commande S00642 
                    # => Mais j'ai un doute sur le fait que cela fonctionnera dans tous les cas
                    #if row[0]=='out_refund':
                    #   sens=-1

                    is_deja_facture += sens*(row[1] or 0)
            is_facturable = obj.product_uom_qty*obj.price_unit*obj.is_facturable_pourcent/100
            is_a_facturer = round(is_facturable - is_deja_facture,2)
            if obj.is_facturable_pourcent==100 and abs(is_a_facturer)<0.02:
                is_a_facturer=0
            obj.is_facturable   = is_facturable
            obj.is_deja_facture = is_deja_facture
            obj.is_a_facturer   = is_a_facturer


    def unlink(self):
        for obj in self:
            if obj.is_deja_facture>0:
                raise ValidationError("Il n'est pas possible de supprimer une ligne déjà facturée")
        super(sale_order_line, self).unlink()


class is_sale_order_section(models.Model):
    _name='is.sale.order.section'
    _description = "Sections des commandes"
    _rec_name = 'section'
    _order='sequence'

    order_id    = fields.Many2one('sale.order', 'Commande', required=True, ondelete='cascade')
    sequence    = fields.Integer("Sequence")
    section     = fields.Char("Section", required=True)
    facturable_pourcent = fields.Float("% facturable", digits=(14,2))
    facturable_pourcent_calcule = fields.Float("% facturable calculé", digits=(14,2), store=True, readonly=True, compute='_compute_facturable_pourcent_calcule')
    option      = fields.Boolean("Option", default=False)
    line_ids    = fields.One2many('sale.order.line', 'is_section_id', 'Lignes')
    all_line_ids = fields.Many2many('sale.order.line', compute='_compute_all_line_ids', string='Toutes les lignes', compute_sudo=True)
    currency_id = fields.Many2one(related='order_id.currency_id')
    montant        = fields.Monetary("Montant HT hors option", store=True, readonly=True, compute='_compute_facturable', currency_field='currency_id')
    montant_option = fields.Monetary("Montant HT des options", store=True, readonly=True, compute='_compute_facturable', currency_field='currency_id')
    facturable   = fields.Float("Facturable"         , digits=(14,2), store=True, readonly=True, compute='_compute_facturable')
    deja_facture = fields.Float("Déja facturé"       , digits=(14,2), store=True, readonly=True, compute='_compute_facturable')
    a_facturer   = fields.Float("En cours facturable", digits=(14,2), store=True, readonly=True, compute='_compute_facturable')


    def _get_all_lines(self):
        """Retourne toutes les lignes de la section, y compris celles avec order_id=False"""
        self.ensure_one()
        # Si l'enregistrement n'est pas encore sauvegardé, retourner un recordset vide
        if isinstance(self.id, models.NewId):
            return self.env['sale.order.line']
        cr = self._cr
        SQL = "SELECT id FROM sale_order_line WHERE is_section_id=%s ORDER BY sequence"
        cr.execute(SQL, [self.id])
        line_ids = [row[0] for row in cr.fetchall()]
        return self.env['sale.order.line'].sudo().browse(line_ids)


    def _compute_all_line_ids(self):
        """Compute method pour exposer _get_all_lines() via un champ"""
        for obj in self:
            obj.all_line_ids = obj._get_all_lines()


    @api.depends('line_ids.is_facturable','line_ids.is_deja_facture','line_ids.is_a_facturer','line_ids.price_subtotal')
    def _compute_facturable(self):
        for obj in self:
            facturable = deja_facture = a_facturer = montant = montant_option = 0
            for line in obj._get_all_lines():
                facturable   +=line.is_facturable
                deja_facture +=line.is_deja_facture
                a_facturer   +=line.is_a_facturer
                if obj.option:
                    montant_option+=line.price_subtotal
                else:
                    montant+=line.price_subtotal
            obj.facturable     = facturable
            obj.deja_facture   = deja_facture
            obj.a_facturer     = a_facturer
            obj.montant        = montant
            obj.montant_option = montant_option


    @api.depends('order_id.order_line.price_subtotal','order_id.order_line.is_facturable')
    def _compute_facturable_pourcent_calcule(self):
        for obj in self:
            pourcent = 0
            total = facturable = 0
            for line in obj.order_id.order_line:
                if line.is_section_id==obj:
                    total+=line.price_subtotal
                    facturable+=line.is_facturable
            if total!=0:
                pourcent = 100*facturable/total
            obj.facturable_pourcent_calcule = pourcent


    def unlink(self):
        for obj in self:
            if obj.deja_facture>0:
                raise ValidationError("Il n'est pas possible de supprimer une section contenant des lignes déjà facturées")
            obj._get_all_lines().unlink()
        super(is_sale_order_section, self).unlink()


    def write(self, vals):
        res = super(is_sale_order_section, self).write(vals)
        if "facturable_pourcent" in vals:
            for obj in self:
                for line in obj._get_all_lines():
                    if line.is_section_id==obj:
                        line.is_facturable_pourcent = vals["facturable_pourcent"]
        if "sequence" in vals:
            for obj in self:
                x=10
                for section in obj.order_id.is_section_ids:
                    for line in section._get_all_lines():
                        line.sequence = x
                        x+=10
        if 'section' in vals:
            for obj in self:
                for line in obj._get_all_lines():
                    if line.display_type=='line_section':
                        line.name = obj.section
        return res


    def option_section_action(self):
        for obj in self:
            # Récupérer toutes les lignes (y compris celles avec order_id=False)
            all_lines = obj._get_all_lines()            
            # Active/désactive l'option de la section
            obj.option = not obj.option
            for line in all_lines:
                if obj.option:
                    # En mode option: détacher la ligne de la commande
                    line.order_id = False
                else:
                    # En mode normal: rattacher la ligne à la commande
                    line.order_id = obj.order_id.id


    def lignes_section_action(self):
        for obj in self:
            tree_id = self.env.ref('is_clair_sarl18.is_view_order_line_tree').id
            return {
                "name": "Section "+str(obj.section),
                "view_mode": "list",
                "res_model": "sale.order.line",
                "domain": [
                    ("is_section_id","=",obj.id),
                    ("product_id","!=",False),
                ],
                "type": "ir.actions.act_window",
                "views"    : [[tree_id, "list"]],
            }


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.depends('is_invoice_ids','is_invoice_ids.state','amount_total','order_line','order_line.is_a_facturer','order_line.is_deja_facture','is_section_ids', 'is_section_ids.facturable_pourcent')
    def _compute_facturable(self):
        for obj in self:
            is_a_facturer=0
            is_deja_facture=0
            for line in obj.order_line:
                is_a_facturer+=line.is_a_facturer
                is_deja_facture+=line.is_deja_facture
            is_a_facturer_abs = math.ceil(abs(is_a_facturer))
            obj.is_deja_facture   = is_deja_facture
            obj.is_a_facturer     = is_a_facturer
            obj.is_a_facturer_abs = is_a_facturer_abs


    @api.depends('is_invoice_ids','is_invoice_ids.state','amount_total')
    def _compute_is_total_facture(self):
        for obj in self:
            obj.order_line._compute_facturable()
            is_total_facture = 0
            for invoice in obj.is_invoice_ids:
                if invoice.state=='posted':
                    is_total_facture+=invoice.amount_untaxed_signed
            is_reste_a_facturer = obj.amount_untaxed - is_total_facture
            obj.is_total_facture    = is_total_facture
            obj.is_reste_a_facturer = is_reste_a_facturer
            pourcent=0
            if obj.amount_untaxed!=0:
                pourcent = 100 * obj.is_reste_a_facturer / obj.amount_untaxed
            obj.is_pourcent_a_facturer = pourcent
            if obj.state=='sale':
                if abs(is_reste_a_facturer)<0.1:
                    obj.invoice_status = 'invoiced'
                else:
                    obj.invoice_status = 'to invoice'


    @api.depends('is_date_pv')
    def _compute_is_echeance_1an(self):
        for obj in self:
            echeance=False
            if obj.is_date_pv:
                echeance = obj.is_date_pv + relativedelta(years=1)
            obj.is_echeance_1an = echeance


    @api.depends('is_affaire_id','amount_untaxed')
    def _compute_is_retenue_de_garantie(self):
        for obj in self:
            retenue = taux = compte_prorata = taux_compte_prorata = 0
            for line in obj.is_affaire_id.remise_ids:
                if line.product_id.default_code=='RETENUE_GARANTIE':
                    retenue = round(obj.amount_untaxed*line.remise/100,2)
                    taux = line.remise
                if line.product_id.default_code=='COMPTE_PRORATA':
                    compte_prorata = round(obj.amount_untaxed*line.remise/100,2)
                    taux_compte_prorata = line.remise
            obj.is_retenue_de_garantie      = retenue
            obj.is_taux_retenue_de_garantie = taux
            obj.is_compte_prorata      = compte_prorata
            obj.is_taux_compte_prorata = taux_compte_prorata


    @api.depends('is_affaire_id','is_invoice_ids','is_invoice_ids.is_rg_deduite','is_invoice_ids.invoice_date')
    def _compute_is_rg_deduite(self):
        for obj in self:
            rg=0
            if obj.is_taux_retenue_de_garantie>0:
                domain=[('state','=','posted'), ('is_order_id','=',obj.id), ('move_type','=','out_invoice')]
                invoices = self.env['account.move'].search(domain,limit=1,order="invoice_date desc")
                for invoice in invoices:
                    rg=invoice.is_rg_deduite
            obj.is_rg_deduite = rg


    is_import_excel_ids     = fields.Many2many('ir.attachment' , 'sale_order_is_import_excel_ids_rel', 'order_id'     , 'attachment_id'    , 'Devis .xlsx à importer')
    is_import_alerte        = fields.Text('Alertes importation')
    is_taches_associees_ids = fields.One2many('purchase.order', 'is_sale_order_id', 'Tâches associées')
    is_affaire_id           = fields.Many2one('is.affaire', 'Affaire')
    is_contact_facture_id   = fields.Many2one('res.partner', 'Contact facture')
    is_section_ids          = fields.One2many('is.sale.order.section', 'order_id', 'Sections')
    is_invoice_ids          = fields.One2many('account.move', 'is_order_id', 'Factures', readonly=True) #, domain=[('state','=','posted')])
    is_a_facturer           = fields.Float("En cours facturable"        , digits=(14,2), store=True, readonly=True, compute='_compute_facturable')
    is_a_facturer_abs       = fields.Float("En cours facturable (>1€)"  , digits=(14,2), store=True, readonly=True, compute='_compute_facturable')
    is_deja_facture         = fields.Float("Lignes déjà facturées"      , digits=(14,2), store=True, readonly=True, compute='_compute_facturable')
    is_affichage_pdf        = fields.Selection([
        ('standard'       , 'Standard'),
        ('masquer_montant', 'Masquer le détail des montants'),
        ('total_section'  , 'Afficher uniquement le total des sections'),
    ], 'Affichage PDF', default='standard', required=True)

    is_date_facture   = fields.Date("Date de la facture à générer"  , tracking=True)
    is_numero_facture = fields.Char("Numéro de la facture à générer", tracking=True)
    is_situation      = fields.Char("Situation facture à générer"   , tracking=True)

    is_total_facture       = fields.Float("Total facturé"   , digits=(14,2), store=True, readonly=True, compute='_compute_is_total_facture')
    is_reste_a_facturer    = fields.Float("Reste à facturer", digits=(14,2), store=True, readonly=True, compute='_compute_is_total_facture')
    is_pourcent_a_facturer = fields.Float("% à facturer"    , digits=(14,2), store=True, readonly=True, compute='_compute_is_total_facture')

    is_date_pv             = fields.Date("Date PV", help="Date de réception du PV", tracking=True)
    is_pv_ids              = fields.Many2many('ir.attachment' , 'sale_order_is_pv_ids_rel', 'order_id', 'attachment_id', 'PV de réception')
    is_echeance_1an        = fields.Date("Échéance 1an"                      , store=True, readonly=True, compute='_compute_is_echeance_1an')
    is_taux_retenue_de_garantie = fields.Float("Taux RG"                     , store=True, readonly=True, compute='_compute_is_retenue_de_garantie')
    is_retenue_de_garantie      = fields.Monetary("RG"                       , store=True, readonly=True, compute='_compute_is_retenue_de_garantie', currency_field='currency_id')
    is_rg_deduite               = fields.Monetary('RG déduite'               , store=True, readonly=True, compute='_compute_is_rg_deduite')
    is_compte_prorata           = fields.Monetary("Compte prorata"           , store=True, readonly=True, compute='_compute_is_retenue_de_garantie', currency_field='currency_id')
    is_taux_compte_prorata      = fields.Float("Taux compte prorata (%)"     , store=True, readonly=True, compute='_compute_is_retenue_de_garantie')
    is_commande_soldee          = fields.Boolean("Commande soldée",default=False, tracking=True)
    is_note_facturation         = fields.Char("Note facturation", tracking=True, copy=False)


    def write(self, vals):
        res = super(sale_order, self).write(vals)
        if self.is_commande_soldee and not self.is_date_pv:
            raise ValidationError("Il est obligatoire de renseigner le champ 'Date PV' pour solder une commande")
        # Mise à jour du res_id des pièces jointes importées pour les droits d'accès
        if 'is_import_excel_ids' in vals:
            for order in self:
                for attachment in order.is_import_excel_ids:
                    if attachment.res_id != order.id or attachment.res_model != 'sale.order' or not attachment.res_field:
                        attachment.sudo().write({
                            'res_id': order.id,
                            'res_model': 'sale.order',
                            'res_field': 'is_import_excel_ids',
                        })
        return res


    @api.onchange('partner_id')
    def onchange_for_is_contact_facture_id(self):
        for obj in self:
            contact_id=False
            if obj.partner_id.is_contact_relance_facture_id:
                contact_id = obj.partner_id.is_contact_relance_facture_id.id
        obj.is_contact_facture_id = contact_id


    def voir_commande_action(self):
        for obj in self:
            return {
                "name": "Commande",
                "view_mode": "form",
                "res_model": "sale.order",
                "res_id"   : obj.id,
                "type": "ir.actions.act_window",
            }


    def import_fichier_xlsx(self):
        for obj in self:
            #** Recherche de la sequence de la dernière section ***************
            sequence_section=0
            for section in obj.is_section_ids:
                if section.sequence>sequence_section:
                    sequence_section=section.sequence
            sequence_section+=10
            #******************************************************************

            #** Recherche de la sequence de la dernière ligne *****************
            sequence=0
            for line in obj.order_line:
                if line.sequence>sequence:
                    sequence=line.sequence
            sequence+=10
            #******************************************************************

            alertes=[]
            section_id=False
            for attachment in obj.is_import_excel_ids:
                xlsxfile=base64.b64decode(attachment.datas)

                path = '/tmp/sale_order-'+str(obj.id)+'.xlsx'
                f = open(path,'wb')
                f.write(xlsxfile)
                f.close()
                #*******************************************************************

                #** Test si fichier est bien du xlsx *******************************
                try:
                    wb    = openpyxl.load_workbook(filename = path, data_only=True)
                    ws    = wb.active
                    cells = list(ws)
                except:
                    raise Warning(u"Le fichier "+attachment.name+u" n'est pas un fichier xlsx")
                #*******************************************************************

                lig=0
                option=False
                for row in ws.rows:
                    name    = cells[lig][0].value
                    ref     = cells[lig][7].value
                    is_masquer_ligne = False
                    try:
                        masquer = cells[lig][10].value # Colonne K => Mettre un x pour masquer la ligne sur le PDF
                        if masquer=="x":
                            is_masquer_ligne = True
                    except:
                        is_masquer_ligne = False
                    vals=False
                    if ref in ["SECTION", "OPTION"] and name:
                        vals={
                            "order_id"       : obj.id,
                            "sequence"       : sequence_section,
                            "section"        : name,
                        }
                        option=False
                        if ref=="OPTION":
                            vals["option"]=True
                            option=True
                        section = self.env['is.sale.order.section'].create(vals)
                        section_id=section.id
                        sequence_section+=10

                        vals={
                            "order_id"       : not option and obj.id,
                            "sequence"       : sequence,
                            "name"           : name,
                            "product_uom_qty": 0,
                            "display_type"   : "line_section",
                            "is_section_id"  : section_id,
                        }
                        filtre=[
                            ("is_sale_order_id"  ,"=", obj.id),
                            ("partner_ref"  ,"=", name),
                        ]
                    if ref=="NOTE" and name:
                        vals={
                            "order_id"       : not option and obj.id,
                            "sequence"       : sequence,
                            "name"           : name,
                            "product_uom_qty": 0,
                            "display_type"   : "line_note",
                            "is_section_id"  : section_id,
                        }
                    if name and ref and not vals:
                        filtre=[
                            ("default_code"  ,"=", ref),
                        ]
                        products = self.env['product.product'].search(filtre)
                        qty=price=discount=is_prix_achat=0
                        if not products:
                            alertes.append("Code '%s' non trouvé"%(ref))
                        else:
                            product=products[0]
                            try:
                                qty = float(cells[lig][2].value or 0)
                            except :
                                qty = 0
                            try:
                                price = float(cells[lig][4].value or 0)
                            except:
                                price = 0
                            try:
                                discount = float(cells[lig][8].value or 0)
                            except:
                                discount = 0
                            try:
                                is_prix_achat = float(cells[lig][9].value or 0)
                            except:
                                is_prix_achat = 0
                            unite=False
                            if qty:
                                unite    = cells[lig][1].value
                            vals={
                                "order_id"       : not option and obj.id,
                                "product_id"     : product.id,
                                "sequence"       : sequence,
                                "name"           : name,
                                "is_unite"       : unite,
                                "product_uom_qty": qty,
                                "price_unit"     : price,
                                "discount"       : discount,
                                "is_prix_achat"  : is_prix_achat,
                                "product_uom"    : product.uom_id.id,
                                "is_section_id"  : section_id,
                                "is_masquer_ligne": is_masquer_ligne,
                            }
                    if vals:
                        res = self.env['sale.order.line'].sudo().create(vals)
                    lig+=1
                    sequence+=1
            if alertes:
                alertes = "\n".join(alertes)
            else:
                alertes=False
            obj.is_import_alerte = alertes


    def _get_product_account_id(self, product, fiscal_position):
        accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
        return accounts['income']


    def generer_facture_action(self):
        cr = self._cr
        for obj in self:
            obj._compute_is_retenue_de_garantie()
            move_type = 'out_invoice'
            sens = 1
            if obj.is_a_facturer<0:
                move_type = 'out_refund'
                sens=-1

            #** Création des lignes *******************************************
            total_cumul_ht=0
            invoice_line_ids=[]
            remise_ids=[]
            sequence=0
            is_a_facturer = 0
            for line in obj.order_line:
                if line.display_type in ["line_section", "line_note"]:
                    vals={
                        'sequence'    : line.sequence,
                        'display_type': line.display_type ,
                        'name'        : line.name,
                    }
                else:
                    quantity=line.product_uom_qty*line.is_facturable_pourcent/100
                    account_id = self._get_product_account_id(line.product_id, obj.fiscal_position_id)
                    taxes = line.product_id.taxes_id
                    taxes = obj.fiscal_position_id.map_tax(taxes)
                    tax_ids=[]
                    for tax in taxes:
                        tax_ids.append(tax.id)
                    vals={
                        'sequence'  : line.sequence,
                        'product_id': line.product_id.id,
                        'account_id': account_id.id,
                        'name'      : line.name,
                        'quantity'  : sens*quantity,
                        'is_facturable_pourcent': sens*line.is_facturable_pourcent,
                        'price_unit'            : line.price_unit,
                        'is_sale_line_id'       : line.id,
                        'tax_ids'               : [(6, 0, tax_ids)],  # Format correct pour Many2many
                        "is_a_facturer"         : line.is_a_facturer,
                    }
                    total_cumul_ht+=sens*quantity*line.price_unit
                    is_a_facturer+=line.is_a_facturer
                invoice_line_ids.append((0, 0, vals))  # Format correct pour One2many
                sequence=line.sequence

            #** Ajout de la section pour le repport des factures **************
            sequence+=10
            vals={
                "sequence"       : sequence,
                "name"           : "AUTRE",
                "display_type"   : "line_section",
            }
            invoice_line_ids.append((0, 0, vals))  # Format correct pour One2many
            #******************************************************************

            #** Ajout des factures ********************************************
            products = self.env['product.product'].search([("default_code","=",'FACTURE')])
            if not len(products):
                raise ValidationError("Article 'FACTURE' non trouvé")
            product=products[0]
            invoices = self.env['account.move'].search([('is_order_id','=',obj.id),('state','=','posted')],order="id")
            for invoice in invoices:
                account_id = self._get_product_account_id(product, obj.fiscal_position_id)
                taxes = product.taxes_id
                taxes = obj.fiscal_position_id.map_tax(taxes)
                tax_ids=[]
                for tax in taxes:
                    tax_ids.append(tax.id)
                sequence+=10
                vals={
                    'sequence'  : sequence,
                    'product_id': product.id,
                    'account_id': account_id.id,
                    'name'      : "Situation %s (Facture %s)"%(invoice.is_situation,invoice.name),
                    'quantity'  : -1*sens,
                    'price_unit': invoice.amount_untaxed_signed,
                    'tax_ids'   : [(6, 0, tax_ids)],  # Format correct pour Many2many
                }
                invoice_line_ids.append((0, 0, vals))  # Format correct pour One2many

            #** Ajout des remises *********************************************
            for line in obj.is_affaire_id.remise_ids:
                if line.remise>0:
                    product=line.product_id
                    account_id = self._get_product_account_id(product, obj.fiscal_position_id)
                    taxes = product.taxes_id
                    taxes = obj.fiscal_position_id.map_tax(taxes)
                    tax_ids=[]
                    for tax in taxes:
                        tax_ids.append(tax.id)
                    sequence+=10
                    name="%s %s%%"%(product.name,line.remise)
                    if line.apres_ttc==False:
                        if line.caution:
                            price_unit = 0
                        else:
                            price_unit = sens*round(total_cumul_ht,2)
                        vals={
                            'sequence'  : sequence,
                            'product_id': product.id,
                            'account_id': account_id.id,
                            'name'      : name,
                            'quantity'  : -sens*line.remise/100,
                            'price_unit': price_unit,
                            'tax_ids'   : [(6, 0, tax_ids)],  # Format correct pour Many2many
                        }
                        invoice_line_ids.append((0, 0, vals))  # Format correct pour One2many
                    else:
                        vals={
                            'product_id': product.id,
                            'libelle'   : name,
                            'remise'    : line.remise,
                        }
                        remise_ids.append((0, 0, vals))  # Format correct pour One2many
            #******************************************************************

            #** Création entête facture ***************************************
            vals={
                'name'               : obj.is_numero_facture,
                'is_situation'       : obj.is_situation,
                'invoice_date'       : obj.is_date_facture or datetime.date.today(),
                'partner_id'         : obj.partner_id.id,
                'is_order_id'        : obj.id,
                'move_type'          : move_type,
                'invoice_line_ids'   : invoice_line_ids,  # Maintenant au bon format
                'is_remise_ids'      : remise_ids,        # Maintenant au bon format
            }

            move=self.env['account.move'].create(vals)
            move._onchange_partner_id()
            #move._onchange_invoice_date()
            move.action_post()

            #** Calcul des remises sur le TTC *********************************
            for line in move.is_remise_ids:
                montant = move.amount_total_signed * line.remise/100
                line.montant = montant


    def modifier_pourcentage_action(self):
        for obj in self:
            tree_id = self.env.ref('is_clair_sarl18.is_view_order_line_tree').id
            return {
                "name": obj.name,
                "view_mode": "list",
                "res_model": "sale.order.line",
                "domain": [
                    ("order_id","=",obj.id),
                ],
                "type": "ir.actions.act_window",
                "views"    : [[tree_id, "list"]],
                "limit": 1000,
            }



    def en_cours_facturable_action(self):
        for obj in self:
            tree_id = self.env.ref('is_clair_sarl18.is_view_order_line_tree').id
            return {
                "name": obj.name,
                "view_mode": "list",
                "res_model": "sale.order.line",
                "domain": [
                    ("order_id","=",obj.id),
                    ("is_a_facturer","!=",0),
                ],
                "type": "ir.actions.act_window",
                "views"    : [[tree_id, "list"]],
                "limit": 1000,
            }


    def action_cancel(self):
        """Annule la commande sans afficher le wizard et sans envoyer de mail au client"""
        # Vérification des commandes verrouillées (comme dans la méthode originale)
        if any(order.locked for order in self):
            raise UserError(_("You cannot cancel a locked order. Please unlock it first."))
        
        # Appel direct de la méthode d'annulation sans passer par le wizard
        return self._action_cancel()





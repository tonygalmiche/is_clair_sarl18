# -*- coding: utf-8 -*-
from itertools import product
from pdb import line_prefix
from odoo import models,fields,api               # type: ignore
from odoo.tools.misc import formatLang, get_lang # type: ignore
import base64
from subprocess import PIPE, Popen
import re
from thefuzz import fuzz # type: ignore
from collections import OrderedDict
import operator
from datetime import datetime

def str2float(x):
    try:
        resultat = float(x)
    except:
        return 0
    return resultat


def str2eval(x):
    try:
        resultat = str2float(eval(x))
    except:
        return 0
    return resultat


class purchase_order(models.Model):
    _inherit = "purchase.order"

    is_affaire_id          = fields.Many2one('is.affaire', 'Affaire')
    is_contact_chantier_id = fields.Many2one('res.users' , 'Contact chantier')
    is_date                = fields.Date('Date')
    is_delai_mois_id       = fields.Many2one('is.mois.trimestre', 'Délai (Mois / Trimestre)')
    is_delai_annee         = fields.Char('Délai (Année)')
    is_delai               = fields.Char("Délai prévisionnel", help="Délai prévisionnel de l'affaire")
    is_date_livraison      = fields.Date('Date de livraison')
    is_lieu_livraison      = fields.Selection([
        ('notre_adresse'      , 'A notre adresse'),
        ('chantier'           , 'Livraison sur chantier référence'),
        ('enlevement'         , 'Enlèvement'),
        ('livraison_sur_ordre', 'Livraison sur ordre'),
    ], 'Lieu de livraison')
    is_condition_tarifaire = fields.Text('Conditions tarifaire', related='partner_id.is_condition_tarifaire')
    is_repere_ids          = fields.One2many('is.purchase.order.repere', 'order_id', 'Repère de plan')
    is_mois_ids            = fields.One2many('is.purchase.order.mois'  , 'order_id', 'Mois de réalisation des tâches')
    is_sale_order_id       = fields.Many2one('sale.order', 'Commande client associée')
    is_modele_commande_id  = fields.Many2one(related='partner_id.is_modele_commande_id')

    is_import_pdf_ids      = fields.Many2many('ir.attachment' , 'purchase_order_is_import_pdf_ids_rel', 'order_id', 'attachment_id', 'PDF à importer')
    is_import_pdf_resultat = fields.Text("Résultat de l'importation", readonly=True)
    is_eco_contribution    = fields.Float("Montant Eco-contribution", digits=(14,2), store=True, readonly=False, compute='_compute_is_eco_contribution', help='Si ce montant est renseigné, cela ajoutera automatiquement une ligne sur la commande')

    is_num_facture_fournisseur  = fields.Char("N°Facture")
    is_date_facture_fournisseur = fields.Date('Date Facture')
    is_reste_a_facturer         = fields.Float("Reste à facturer", compute='_compute_is_reste_a_facturer', store=True, readonly=True)

    user_id = fields.Many2one(copy=False) # Ne pas copier le "Responsable achats" lors de la copie de la commande

    
    @api.depends('order_line.qty_invoiced','order_line.product_qty','order_line.price_unit')
    def _compute_is_reste_a_facturer(self):
        for obj in self:
            v=0
            for line in obj.order_line:
                v+=line.is_reste_a_facturer
            obj.is_reste_a_facturer = v


    @api.depends('order_line.product_id','order_line.product_qty')
    def _compute_is_eco_contribution(self):
        for obj in self:
            v=0
            for line in obj.order_line:
                v+=line.is_eco_contribution
            obj.is_eco_contribution = v


    @api.depends('order_line.invoice_lines.move_id','order_line.invoice_lines.move_id.state')
    def _compute_invoice(self):
        for order in self:
            invoices = order.mapped('order_line.invoice_lines.move_id')
            nb=0
            for invoice in invoices:
                if invoice.state!='cancel':
                    nb+=1
            order.invoice_ids = invoices
            order.invoice_count = nb


    @api.onchange('is_affaire_id')
    def onchange_is_affaire_id(self):
        for obj in self:
            if obj.is_affaire_id.contact_chantier_id:
                obj.is_contact_chantier_id = obj.is_affaire_id.contact_chantier_id.id


    def write(self, vals):
        res = super(purchase_order, self).write(vals)
        self.update_reperes()
        self.ajout_eco_contribution()
        return res


    def ajout_eco_contribution(self):
        for obj in self:
            if obj.is_eco_contribution>0:
                products = self.env['product.product'].search([('default_code','=','ECOCON')])
                for product in products:
                    sequence = 0
                    order_line=False
                    for line in obj.order_line:
                        if line.sequence>sequence:
                            sequence=line.sequence
                        if line.product_id == product:
                            order_line = line
                    sequence+=10
                    if not order_line:
                        vals={
                            'order_id': obj.id,
                            'product_id': product.id,
                            'name': product.name_get()[0][1],
                            'product_qty': 1,
                            'price_unit':obj.is_eco_contribution,
                            'sequence': sequence,
                        }
                        res=self.env['purchase.order.line'].create(vals)
                    else:
                        order_line.sequence=sequence
                        order_line.price_unit = obj.is_eco_contribution
                

    def update_reperes(self):
        cr = self._cr
        for obj in self:
            #** Ajout des lignes des reperes **********************************
            ids=[]
            for r in obj.is_repere_ids:
                ids.append(r)
            for line in obj.order_line:
                ids2=[]
                for r2 in line.is_repere_ids:
                    ids2.append(r2.repere_id)
                    r2.sequence=r2.repere_id.sequence
                for r in ids:
                    if r not in ids2:
                        vals={
                            "line_id"  : line.id,
                            "repere_id": r.id,
                            "sequence" : r.sequence,
                        }
                        res = self.env['is.purchase.order.line.repere'].create(vals)


            #** Ajout des lignes des mois *************************************
            ids=[]
            for r in obj.is_mois_ids:
                ids.append(r)
            for line in obj.order_line:
                ids2=[]
                for r2 in line.is_mois_ids:
                    ids2.append(r2.mois_id)
                for r in ids:
                    if r not in ids2:
                        vals={
                            "line_id": line.id,
                            "mois_id": r.id,
                        }
                        res = self.env['is.purchase.order.line.mois'].create(vals)


            #** Calcul des totaux des reperes *********************************
            for r in obj.is_repere_ids:
                SQL="""
                    SELECT montant
                    FROM is_purchase_order_line_repere
                    WHERE repere_id=%s
                """
                cr.execute(SQL,[r.id])
                for row in cr.fetchall():
                    r.montant = row[0]


            #** Calcul des totaux des mois ************************************
            for r in obj.is_mois_ids:
                SQL="""
                    SELECT montant
                    FROM is_purchase_order_line_mois
                    WHERE mois_id=%s
                """
                cr.execute(SQL,[r.id])
                for row in cr.fetchall():
                    r.montant = row[0]


    def importer_tache_action(self):
        cr = self._cr
        for obj in self:
            obj.order_line.unlink()
            SQL="""
                SELECT pp.id, pt.name, isf.name
                FROM product_product pp join product_template pt on pp.product_tmpl_id=pt.id
                                        join is_famille       if on pt.is_famille_id=if.id
                                        left join is_sous_famille isf on pt.is_sous_famille_id=isf.id
                WHERE if.name='Tâche' and pt.active='t'
                ORDER BY if.name,isf.name,pt.is_ordre_tri,pt.name
            """
            cr.execute(SQL)
            sequence=1
            mem=""
            for row in cr.fetchall():
                if row[2]!=mem:
                    mem=row[2]
                    vals={
                        "order_id"    : obj.id,
                        "sequence"    : sequence,
                        "name"        : mem,
                        "product_qty" : 0,
                        "display_type": "line_section",
                    }
                    res = self.env['purchase.order.line'].create(vals)
                vals={
                    "order_id"       : obj.id,
                    "product_id"     : row[0],
                    "sequence"       : sequence,
                    "name"           : row[1],
                    "product_uom_qty": 1,
                }
                res = self.env['purchase.order.line'].create(vals)
                sequence+=1


    def view_order_action(self):
        for obj in self:
            return {
                "name": "Commande %s"%(obj.name),
                "view_mode": "form",
                "res_model": "purchase.order",
                "res_id"   : obj.id,
                "type": "ir.actions.act_window",
            }


    def initialiser_depuis_modele_commande(self):
        for obj in self:
            sequence=10
            for line in obj.is_modele_commande_id.ligne_ids:
                vals={
                    'order_id'    : obj.id,
                    'sequence'    : sequence,
                    'product_id'  : line.product_id.id,
                    'name'        : line.description or line.product_id.name_get()[0][1],
                    'product_qty' : 0,
                }
                self.env['purchase.order.line'].create(vals)
                sequence+=10


    def import_pdf_action(self):
        for obj in self:
            for attachment in obj.is_import_pdf_ids:

                #** Lecture du PDF ********************************************
                pdf=base64.b64decode(attachment.datas)
                name = 'purchase_order-%s'%obj.id
                path = "/tmp/%s.pdf"%name
                f = open(path,'wb')
                f.write(pdf)
                f.close()
                cde = "cd /tmp && pdftotext -layout %s.pdf"%name
                p = Popen(cde, shell=True, stdout=PIPE, stderr=PIPE)
                stdout, stderr = p.communicate()
                path = "/tmp/%s.txt"%name
                r = open(path,'rb').read().decode('utf-8')
                lines = r.split('\n')
                order_lines=[]
                dict={}
                res=[]
                chantier_zip=False
                affaire=False
                #**************************************************************

                #** Recherche du type de PDF (LOXAM ou PUM) *******************
                def get_type_pdf(lines,txt,name_type):
                    type_pdf=False
                    for line in lines:
                        x = re.findall(txt, line) 
                        if x:
                            test = True
                            type_pdf=name_type
                            break
                    return type_pdf
                type_pdf = get_type_pdf(lines,'LOXAM','LOXAM')
                if not type_pdf:
                    type_pdf = get_type_pdf(lines,'   PUM','PUM')
                if type_pdf==False:
                    obj.is_import_pdf_resultat = "Ce PDF n'est pas de LOXAM ou de PUM => Importation impossible"
                    return
                dict["Type de PDF"] = type_pdf
                test=True
                #**************************************************************



                #** Recherche de l'adresse du chantier ************************
                dict["Chantier"] = ''
                if type_pdf=="PUM":
                    chantier=[]
                    if test:
                        lig=0
                        for line in lines:
                            x = re.findall("Réf/Cli", line) 
                            if x:
                                v = line.split(' : ')
                                if len(v)==2:
                                    dict["Chantier"] = v[1].strip()
             
                if type_pdf=='LOXAM':
                    chantier=[]
                    if test:
                        lig=0
                        for line in lines:
                            x = re.findall("Adresse de chantier", line) 
                            if x:
                                lig=1
                            if lig>1 and lig<=6:
                                v = line[0:160].strip()
                                chantier.append(v)
                            if lig>=6:
                                break
                            if lig:
                                lig+=1
                    if chantier:
                        dict["Chantier"] = ' '.join(chantier)
                    #**************************************************************

                    #** Code postal du chantier ***********************************
                    if chantier:
                        adresse = dict["Chantier"]
                        x = re.findall("[0-9]{5}", adresse)
                        if x:
                            chantier_zip = x[0]
                    #**************************************************************

                    #** N°BDC (Code Affaire) ***************************************
                    if test:
                        for line in lines:
                            x = re.findall("N°BDC", line) 
                            if x:
                                v = line.strip()[0:30].strip()
                                v = v.split(' : ')
                                if len(v)==2:
                                    bdc = v[1].strip()
                                    x = re.findall("[0-9]{2}\.[0-9]{4}", bdc)
                                    if x:
                                        bdc=x[0]

                                        affaires = self.env['is.affaire'].search([('name','=',bdc)])
                                        if affaires:
                                            affaire=affaires[0]
                                    dict["N°BDC"] = bdc
                                break
                    #**************************************************************

                #** Recherche de l'affaire ************************************
                def supprime_petit_mots(phrase,taille=4):
                    "Supprime tous les mots de phrase <= taille"
                    mots=phrase.split(' ')
                    k=0
                    for mot in mots:
                        if len(mot)<taille:
                            mots[k]=""
                        k+=1
                    phrase=' '.join(mots).strip()
                    return phrase
                if test and not affaire:
                    chantier = dict["Chantier"].upper()
                    filtre=[]
                    if chantier_zip:
                        filtre=[('zip','=',chantier_zip)]
                    #** Recherche dans l'adresse ******************************
                    affaire_dict={}
                    affaires = self.env['is.affaire'].search(filtre,order="adresse_chantier")
                    for line in affaires:
                        adresse = line.adresse_chantier.replace('\n',' ').strip().upper()
                        if adresse!='':
                            ratio = fuzz.ratio(chantier, adresse)
                            affaire_dict[ratio] = (line, line.name)
                    #** Recherche dans le nom *********************************
                    affaires = self.env['is.affaire'].search(filtre,order="nom")
                    for line in affaires:
                        if line.nom:
                            nom = line.nom.replace('\n',' ').strip().upper()
                            nom_sans_petit_mot  = supprime_petit_mots(nom)
                            chantier_sans_petit_mot = supprime_petit_mots(chantier)
                            if nom_sans_petit_mot!='' and chantier_sans_petit_mot!='':
                                ratio = fuzz.partial_ratio(chantier_sans_petit_mot, nom_sans_petit_mot)
                                affaire_dict[ratio] = (line, line.name)
                    #** Tri par ratio *****************************************
                    key_sorted = sorted(affaire_dict, reverse=True)
                    for key in key_sorted:
                        if key>50:
                            affaire = affaire_dict[key][0]
                        break
                #**************************************************************

                #** Affaire ***************************************************
                if affaire:
                    obj.is_affaire_id = affaire.id
                    dict["Affaire"] = affaire.name
                else:
                    dict["Affaire"] = "Affaire non trouvée"
                #**************************************************************

                #** Recherche Acheteur ****************************************
                if type_pdf=='LOXAM':
                    if test:
                        for line in lines:
                            x = re.findall("Acheteur", line) 
                            if x:
                                v = line.strip()[0:30].strip()
                                v = v.split(' : ')
                                if len(v)==2:
                                    dict["Acheteur"] = v[1]
                                break
                #**************************************************************

                #** N°Facture *************************************************
                def txt2date(txt,format='%d/%m/%y'):
                    txt=txt.replace(' ','')
                    try:
                        date_facture = datetime.strptime(txt, format)
                    except ValueError:
                        date_facture = False
                    return date_facture
                if test:
                    num_facture  = False
                    date_facture = False
                    if type_pdf=='LOXAM':
                        for line in lines:
                            x = re.search("Facture N° :(.*) du (.*)", line) 
                            if x:
                                v = x.groups()
                                if len(v)==2:
                                    num_facture  = v[0].strip()
                                    date_facture = txt2date(v[1])
                                    break
                    if type_pdf=='PUM':
                        for line in lines:
                            num_facture = line.strip() #Numéro de facture sur la première ligne toute seule
                            break
                        for line in lines:
                            x = re.search("F A C T U R E(.*)", line)
                            if x:
                                v = x.groups()
                                date_facture = txt2date(v[0],'%d-%m-%Y')
                                break
                    dict["N°Facture"]               = num_facture
                    dict["Date Facture"]            = date_facture 
                    obj.is_num_facture_fournisseur  = num_facture
                    obj.is_date_facture_fournisseur = date_facture
                #**************************************************************

                #** Lignes avec des Quantités ou des montants *****************
                def txt2float(txt):
                    try:
                        val=float(txt.strip().replace(',','.'))
                    except:
                        val=0
                    return val
                if type_pdf=='PUM':
                    for line in lines:
                        code_pum    = line[0:19].strip()
                        designation = line[19:85].strip()
                        reste = line[86:].strip()
                        x1 = ' '.join(reste.split()) # Supprimer les espaces en double
                        x2 = x1.split()
                        if len(x2)==5:
                            quantite = txt2float(x2[0])
                            prix_net = txt2float(x2[3])
                            montant  = txt2float(x2[4])
                            if round(quantite*prix_net,2)==round(montant,2) and montant>0:
                                description="%s (%s)"%(designation,code_pum)
                                order_lines.append([quantite, description, prix_net])
                #**************************************************************

                #** Eco-contribution ******************************************
                if type_pdf=='PUM':
                    for line in lines:
                        x = re.search("    Eco contribution :(.*)", line) 
                        if x:
                            v = x.groups()
                            if len(v)==1:
                                montant=txt2float(v[0])
                                order_lines.append([1, "Eco-contribution", montant])
                                dict["Eco contribution"] = montant
                                break
                #**************************************************************

                #** Transport *************************************************
                if type_pdf=='PUM':
                    for line in lines:
                        x = re.search("Transport : (.*)", line) 
                        if x:
                            v = x.groups()
                            if len(v)==1:
                                t = v[0].split(' ')
                                montant=txt2float(t[0])
                                order_lines.append([1, "Transport", montant])
                                dict["Transport"] = montant
                                break
                #**************************************************************

                #** Surcharge gasoil ******************************************
                if type_pdf=='PUM':
                    for line in lines:
                        x = re.search("Surcharge gasoil : (.*)", line) 
                        if x:
                            v = x.groups()
                            if len(v)==1:
                                t = v[0].split(' ')
                                montant=txt2float(t[0])
                                order_lines.append([1, "Surcharge gasoil", montant])
                                dict["Surcharge gasoil"] = montant
                                break
                #**************************************************************

                #** Lignes avec des Quantités ou des montants *****************
                if type_pdf=='LOXAM':
                    if test:
                        debut=fin=False
                        debut_libelle = fin_libelle = False
                        libelles = []
                        qte = 0
                        montant_total = 0
                        new=False
                        for line in lines:
                            if debut and not fin:
                                #** Quantité **************************************
                                qte = 0
                                libelle = False
                                montant = 0
                                tab = line.strip().split(' ')
                                if len(tab)>1:
                                    try:
                                        qte=float(tab[0].strip())
                                    except:
                                        qte=0
                                
                                #** Montant ***************************************
                                x = re.findall("[0-9]*\.[0-9]{2}$", line.strip())
                                if x:
                                    x2 = " ".join(line.split()) # Supprimer les espaces en double
                                    list = x2.split()
                                    if len(list)>1:
                                        try:
                                            montant=float(x[0].strip())
                                        except:
                                            montant=0

                                #** Libellé sans Qté et sans Montant **************
                                l = False
                                if not qte and not montant:
                                    x = " ".join(line.split()) # Supprimer les espaces en double
                                    list = x.split()
                                    l = ' '.join(list)

                                #** Libellé avec Qté et Montant *******************
                                if qte and montant:
                                    x = " ".join(line.split()) # Supprimer les espaces en double
                                    list = x.split()
                                    list.pop(0) # Supprime le premier element (la quantité)
                                    list.pop()  # Supprime le dernier element (le montant)
                                    l = ' '.join(list)

                                #** Libellé avec Qté et sans Montant **************
                                if qte and not montant:
                                    x = " ".join(line.split()) # Supprimer les espaces en double
                                    list = x.split()
                                    list.pop(0) # Supprime le premier element (la quantité)
                                    l = ' '.join(list)

                                #** Autres libellés *******************************
                                x = re.findall("Total période", line)
                                if montant and x:
                                    l=x[0].strip()
                                x = re.findall("Contribution verte", line)
                                if montant and x:
                                    l=x[0].strip()
                                    qte = qte or 1
                                x = re.findall("Forfait transport Aller", line)
                                if montant and x:
                                    l=x[0].strip()
                                    qte = qte or 1
                                x = re.findall("Forfait transport Retour", line)
                                if montant and x:
                                    l=x[0].strip()
                                    qte = qte or 1

                                #** Elimination des intitulés indésirables ********
                                indesirable=False
                                if l:
                                    l=l.strip()
                                    if l=='' or l=='Total période':
                                        indesirable=True
                                    x = re.findall("Ventes Prix Unitaire", l)
                                    if x:
                                        indesirable=True
                                    x = re.findall("Étude BVA - Viséo CI", l)
                                    if x:
                                        indesirable=True
                                if l and not indesirable:
                                    libelles.append(l.strip())

                                #** Test si nouvelle ligne ************************
                                new = False
                                if qte and montant:
                                    new=True
                                if l=="Total période":
                                    new=True
                                if new:
                                    libelle = '\n'.join(libelles)
                                    libelles=[]
                                    montant_total+=montant
                                    order_lines.append([1, libelle, montant])
                                    #order_lines.append([qte, libelle, montant])

                            x = re.findall("Qté.*Libellé.*Montant", line)
                            if x:
                                debut = True
                            x = re.findall("Total HT", line)
                            if x:
                                fin=True
                                #x = re.findall("[0-9]*\.[0-9]{2}$", line.strip())
                                x = re.findall(r"\d+\.\d{2}$", line.strip())
                                if x:
                                    try:
                                        ht=float(x[0].strip())
                                    except:
                                        ht=0
                                    dict["Total HT"] = ht
                #**************************************************************


                #** Total HT du PDF *******************************************
                ht_pdf=0
                if type_pdf=='PUM':
                    debut=False
                    for line in lines:
                        x = re.findall("TOTAL HT EUR", line) 
                        if x:
                            debut=True
                        if debut:
                            x=' '.join(line.split()) # Supprimer les espaces en trop
                            x=x.split()              # Mettre dans un talbeau les nombres séparés par un espace
                            if len(x)>4:
                                ht_pdf=txt2float(x[0])
                    dict["Total HT PDF"] = ht_pdf
                 #**************************************************************
                           
                #** Montant total *********************************************
                ht=0
                for line in order_lines:

                    
                    ht+=(line[0] * line[2])
                ht=round(ht,2)
                dict["Total HT calculé"] = ht
                #**************************************************************

                #** Résultat du traitement ************************************
                if test:
                    for key in dict:
                        x = "%s : %s"%(key.ljust(20), dict[key])
                        res.append(x)
                    obj.is_import_pdf_resultat = '\n'.join(res)
                #**************************************************************

                #** Ajout des lignes de la commande ***************************
                if test:
                    obj.order_line.unlink()
                    sequence = 0
                    for line in order_lines:
                        libelle = line[1]
                        sequence+=10
                        product = obj.get_product(libelle, type_pdf)
                        if product:
                            vals={
                                "order_id"       : obj.id,
                                "product_id"     : product.id,
                                "sequence"       : sequence,
                                "name"           : line[1],
                                "product_qty"    : line[0],
                                "price_unit"     : line[2],
                                "product_uom"    : product.uom_id.id,
                            }
                            order_line = self.env['purchase.order.line'].create(vals)
                    #**********************************************************


    def get_product(self, libelle,type_pdf=False):
        for obj in self:
            dict={
                'Gaz'	                            : 'GAZ',
                'CHARIOT TELESC'                    : 'CHARIOT',
                'PLATEFORME'                        : 'PLATEFORME',
                'NACELLE'                           : 'NACELLE',
                'BENNE DE REPRISE POUR CHARIOT'     : 'GODET',
                'Constu modulaire R/R'              : 'BUNGALOW',
                'Forfait transport'                 : 'TCHANTIER',
                'MAJORATION TRANSPORT ALLER'        : 'TCHANTIER',
                'MAJORATION TRANSPORT RETOUR'       : 'TCHANTIER',
                'MAJORATION TRANSP ALLER'           : 'TCHANTIER',
                'MAJORATION TRANSP RETOUR'          : 'TCHANTIER',
                'Kilometres supplémentaires'        : 'TCHANTIER',
                'CONTRIBUTION VERTE'                : 'ECOCON',
                'Carburant gazole non routier'      : 'GNR',
                'Prestation forfait recharge elec'  : 'RECHAELEC',
                'Garantie dommages'                 : 'ASSURANCE',
                'Remise'                            : 'REMISE',
                'CONST. MODULAIRE'                  : 'BUNGALOW',
                'WC AUTONOME'                       : 'WC',
                'Eco-contribution'                  : 'ECOCON',
                'Transport'                         : 'TCHANTIER',
                'Surcharge gasoil'                  : 'GNR',
            }
            product = False
            for key in dict:
                if re.search(key, libelle, re.IGNORECASE):
                    filtre=[
                        ("default_code"  ,"=", dict[key]),  
                    ]
                    products = self.env['product.product'].search(filtre)
                    if len(products):
                        product = products[0]
            if not product:
                if type_pdf=='PUM':
                    domain=[("default_code"  ,"=", 'PVC')]
                else:
                    domain=[("name"  ,"=", 'divers')]
                products = self.env['product.product'].search(domain)
                if len(products):
                    product = products[0]
            return product


    def _prepare_invoice(self):
        vals = super(purchase_order, self)._prepare_invoice()
        if self.is_date_facture_fournisseur:
            vals['invoice_date'] = self.is_date_facture_fournisseur
        if self.is_num_facture_fournisseur:
            vals['ref'] = self.is_num_facture_fournisseur
        return(vals)


class IsPurchaseOrderMois(models.Model):
    _name='is.purchase.order.mois'
    _description = "Mois pour le suivi des taches"
    _order='mois'
    _rec_name = 'mois'

    order_id = fields.Many2one('purchase.order', 'Commande', required=True, ondelete='cascade')
    mois     = fields.Date("Mois", required=True)
    montant  = fields.Float("Montant", digits=(14,2), readonly=True)


class IsPurchaseOrderRepere(models.Model):
    _name='is.purchase.order.repere'
    _description = "Repère de plan des commandes"
    _order='repere'
    _rec_name = 'repere'

    order_id = fields.Many2one('purchase.order', 'Commande', required=True, ondelete='cascade')
    sequence = fields.Integer("Sequence")
    repere   = fields.Char("Repère de plan", required=True)
    montant  = fields.Float("Montant", digits=(14,2), readonly=True)


class IsPurchaseOrderLineRepere(models.Model):
    _name='is.purchase.order.line.repere'
    _description = "Repère de plan des lignes de commandes"
    _order='sequence,id'
    _rec_name = 'repere_id'

    line_id   = fields.Many2one('purchase.order.line', 'Ligne de commande', required=True, ondelete='cascade')
    repere_id = fields.Many2one('is.purchase.order.repere', 'Repère de plan', required=True)
    sequence  = fields.Integer("Sequence")
    formule   = fields.Char("Formule")
    quantite  = fields.Float("Quantité", digits=(14,2), store=True, readonly=True, compute='_compute_quantite')
    montant   = fields.Float("Montant" , digits=(14,2), store=True, readonly=True, compute='_compute_quantite')

    @api.depends('formule')
    def _compute_quantite(self):
        for obj in self:
            v=str2eval(obj.formule)
            obj.quantite = v
            obj.montant  = v * obj.line_id.price_unit


class IsPurchaseOrderLineMois(models.Model):
    _name='is.purchase.order.line.mois'
    _description = "Mois des lignes de commandes"
    _order='mois_id'
    _rec_name = 'mois_id'

    line_id   = fields.Many2one('purchase.order.line', 'Ligne de commande', required=True, ondelete='cascade')
    mois_id   = fields.Many2one('is.purchase.order.mois', 'Mois', required=True)
    formule   = fields.Char("Formule")
    quantite  = fields.Float("Quantité", digits=(14,2), store=True, readonly=True, compute='_compute_quantite')
    montant   = fields.Float("Montant" , digits=(14,2), store=True, readonly=True, compute='_compute_quantite')

    @api.depends('formule')
    def _compute_quantite(self):
        for obj in self:
            v=str2eval(obj.formule)
            obj.quantite = v
            obj.montant  = v * obj.line_id.price_unit


class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"


    is_famille_id      = fields.Many2one('is.famille', 'Famille'          , related='product_id.is_famille_id')
    is_sous_famille_id = fields.Many2one('is.sous.famille', 'Sous-famille', related='product_id.is_sous_famille_id')
    is_affaire_id      = fields.Many2one(related='order_id.is_affaire_id')
    is_finition_id     = fields.Many2one('is.finition'  , 'Finition')
    is_traitement_id   = fields.Many2one('is.traitement', 'Traitement')
    is_largeur         = fields.Float('Largeur')
    is_hauteur         = fields.Float('Hauteur')
    is_colis_ids       = fields.One2many('is.purchase.order.line.colis', 'line_id', 'Colis', copy=True)
    is_nb_colis        = fields.Integer('Nb colis', store=True, readonly=True, compute='_compute_is_nb_colis')
    is_liste_colis_action_vsb = fields.Boolean("Liste colis vsb", store=False, readonly=True, compute='_compute_is_liste_colis_action_vsb')
    is_colisage               = fields.Text("Colisage", store=False, readonly=True, compute='_compute_is_colisage')
    is_repere_ids             = fields.One2many('is.purchase.order.line.repere', 'line_id', 'Repère de plan')
    is_mois_ids               = fields.One2many('is.purchase.order.line.mois'  , 'line_id', 'Mois')
    is_preparation_id         = fields.Many2one('is.preparation.facture', 'Préparation facture', help="Utilisé par IsPreparationFacture")
    is_qt_a_facturer          = fields.Float('Qt à facturer', digits='Product Unit of Measure' , help="Utilisé par IsPreparationFacture")
    is_montant_a_facturer     = fields.Float("Montant à facturer"                              , help="Utilisé par IsPreparationFacture")

    is_date_livraison = fields.Date(related='order_id.is_date_livraison')
    is_sequence_facturation = fields.Integer("Ordre") #, store=True, readonly=True, compute='_compute_is_sequence_facturation') #, default=lambda self: self._default_is_sequence_facturation())
    is_eco_contribution = fields.Float("Montant Eco-contribution", digits=(14,6), store=False, readonly=True, compute='_compute_is_eco_contribution')
    is_reste_a_facturer = fields.Float("Reste à facturer", compute='_compute_is_reste_a_facturer', store=True, readonly=True)


    @api.depends('is_colis_ids')
    def _compute_is_nb_colis(self):
        for obj in self:
            nb_colis = len(obj.is_colis_ids)
            obj.is_nb_colis = nb_colis
            obj.is_colis_ids._compute_surface()


    @api.depends('qty_invoiced','product_qty','price_unit')
    def _compute_is_reste_a_facturer(self):
        for obj in self:
            v=(obj.product_qty - obj.qty_invoiced)*obj.price_unit
            obj.is_reste_a_facturer = v


    @api.depends('product_id','product_qty')
    def _compute_is_eco_contribution(self):
        for obj in self:
            v=0
            if obj.product_id and obj.product_qty:
                v = obj.product_id.is_eco_contribution * obj.product_qty
            obj.is_eco_contribution = v


    @api.depends('is_colis_ids')
    def _compute_is_colisage(self):
        for obj in self:
            html=False
            if obj.is_colis_ids:
                html=""
                html+="<table style='width:100%' class='colisage'>"
                html+="<thead><tr><th>Colis</th><th>Nb</th><th>Long.</th><th>Note</th><th>Surface</th></tr></thead>"
                html+="<tbody>"
                for colis in obj.is_colis_ids:
                    nb=len(colis.line_ids)
                    ct=surface_total=0
                    for line in colis.line_ids:
                        surface_total+=line.surface
                        if ct==0:
                            html+="<tr><td style='white-space: normal;' rowspan='"+str(nb)+"'>"+colis.name+"</td>"
                        else:
                            html+="<tr>"
                        html+="<td style='text-align:right'>"+str(line.nb)+"</td>"
                        html+="<td style='text-align:right'>"+str(line.longueur)+"</td>"
                        html+="<td style='text-align:left'>"+(line.note or '')+"</td>"
                        html+="<td style='text-align:right'>"+str(line.surface)+"</td></tr>"
                        ct+=1
                    html+="<tr>"
                    html+="<td style='text-align:right;border-bottom: 1px solid black;' colspan='4'><b>Total:</b></td>"
                    html+="<td style='text-align:right;border-bottom: 1px solid black;'><b>%.2f</b></td>"%(surface_total)
                    html+="</tr>"
                html+="<div style='white-space: nowrap;'>                                                                </div>"
                html+="</tbody>"
                html+="</table>"
            obj.is_colisage=html


    @api.depends('product_id')
    def _compute_is_liste_colis_action_vsb(self):
        for obj in self:
            vsb=False
            if obj.product_id.is_famille_id.colisage:
                vsb=True
            obj.is_liste_colis_action_vsb=vsb



    @api.onchange('is_repere_ids')
    def onchange_repere_ids(self):
        for obj in self:
            if  obj.is_repere_ids:
                    quantite=0
                    for r in obj.is_repere_ids:
                        quantite+=r.quantite
                    obj.product_qty=quantite


    @api.onchange('product_id','is_finition_id','is_traitement_id')
    def _product_id_change(self):
        if not self.product_id:
            return
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=self.partner_id.id,
            company_id=self.company_id.id,
        )
        name = "%s %s %s"%(self.product_id.name, (self.is_finition_id.name or ''), (self.is_traitement_id.name or ''))
        self.name = name
        self._compute_tax_id()


    def liste_colis_action(self):
        for obj in self:
            ctx={
                'default_line_id': obj.id,
            }
            return {
                "name": "Colis "+obj.name,
                "view_mode": "list,form",
                "res_model": "is.purchase.order.line.colis",
                "domain": [
                    ("line_id","=",obj.id),
                ],
                "type": "ir.actions.act_window",
                "context": ctx,
            }


    def liste_lignes_colis_action(self):
        for obj in self:
            filtre=[
                ("line_id"  ,"=", obj.id),
            ]
            colis = self.env['is.purchase.order.line.colis'].search(filtre)
            ids=[]
            for c in colis:
                for line in c.line_ids:
                    ids.append(line.id)
            ctx={
                'group_by': 'colis_id',
            }
            return {
                "name": "Ligne "+str(obj.id),
                "view_mode": "kanban,list,form",
                "res_model": "is.purchase.order.line.colis.line",
                "domain": [
                    ("id","in",ids),
                ],
                "type": "ir.actions.act_window",
                "context": ctx,
            }


    def _prepare_account_move_line(self, move=False):
        res = super(purchase_order_line, self)._prepare_account_move_line(move)
        res.update({
            'is_affaire_id': self.order_id.is_affaire_id.id,
        })
        return res





class IsMoisTrimestre(models.Model):
    _name='is.mois.trimestre'
    _description = "IsMoisTrimestre"
    _order='name'

    name = fields.Char('Mois / Trimestre', required=True, index=True)


class IsFinition(models.Model):
    _name='is.finition'
    _description = "Finition"
    _order='name'

    name = fields.Char('Finition', required=True, index=True)


class IsTraitement(models.Model):
    _name='is.traitement'
    _description = "Traitement"
    _order='name'

    name = fields.Char('Traitement', required=True, index=True)


class IsPurchaseOrderLineColis(models.Model):
    _name='is.purchase.order.line.colis'
    _description = "Colis des lignes de commandes fournisseurs"
    _order='name'

    line_id          = fields.Many2one('purchase.order.line', 'Ligne de commande', required=True, ondelete='cascade')
    product_id       = fields.Many2one('product.product', 'Article', related='line_id.product_id')
    largeur_utile    = fields.Integer("Largeur utile (mm)", related='product_id.is_largeur_utile')
    poids            = fields.Float("Poids (Kg/㎡)"        , related='product_id.is_poids')
    poids_colis      = fields.Float("Poids colis", digits=(14,2), store=True, readonly=True, compute='_compute_poids_colis')
    forfait_coupe_id = fields.Many2one('product.product', 'Longueur mini forfait coupe', related='product_id.is_forfait_coupe_id')
    name             = fields.Char('Colis', required=True, index=True)
    surface          = fields.Float("Surface (㎡)", digits=(14,2), store=True, readonly=True, compute='_compute_surface')
    forfait_coupe    = fields.Integer("Forfait coupe"            , store=True, readonly=True, compute='_compute_surface')
    line_ids         = fields.One2many('is.purchase.order.line.colis.line', 'colis_id', 'Lignes', copy=True)

    @api.depends('line_ids')
    def _compute_poids_colis(self):
        for obj in self:
            poids=0
            for line in obj.line_ids:
                poids+=line.poids
            obj.poids_colis=poids


    @api.depends('line_ids','line_ids.longueur')
    def _compute_surface(self):
        for obj in self:
            surface=0
            forfait_coupe=0
            for line in obj.line_ids:
                surface+=line.surface
                forfait_coupe+=line.forfait_coupe
            obj.surface       = surface
            obj.forfait_coupe = forfait_coupe
            qty=0
            for line in obj.line_id.is_colis_ids:
                qty+=line.surface
            if qty>0:
                obj.line_id.product_qty=qty
            #** Ajout des forfait coupe ***************************************
            if obj.line_id.order_id and obj.forfait_coupe_id:
                forfait_coupe=0
                for order in obj.line_id.order_id:
                    for line in order.order_line:
                        for colis in line.is_colis_ids:
                            if obj.forfait_coupe_id==colis.forfait_coupe_id:
                                forfait_coupe+=colis.forfait_coupe 
                filtre=[
                    ("order_id"  ,"=", obj.line_id.order_id.id),
                    ("product_id","=", obj.forfait_coupe_id.id),
                ]
                lines = self.env['purchase.order.line'].search(filtre)
                vals={
                    "order_id"   : obj.line_id.order_id.id,
                    "product_id" : obj.forfait_coupe_id.id,
                    "name"       : obj.forfait_coupe_id.name,
                    "product_qty": forfait_coupe,
                    "price_unit" : obj.forfait_coupe_id.standard_price,
                    "sequence"   : 900,
                }
                filtre=[
                    ("order_id"  ,"=", obj.line_id.order_id.id),
                    ("product_id","=", obj.forfait_coupe_id.id),
                ]
                lines = self.env['purchase.order.line'].search(filtre)
                if len(lines)>0:
                    lines[0].write(vals)
                else:
                    res=self.env['purchase.order.line'].create(vals)
            #******************************************************************


class IsPurchaseOrderLineColisLine(models.Model):
    _name='is.purchase.order.line.colis.line'
    _description = "Lignes des colis des lignes de commandes fournisseurs"
    _order='colis_id,id'

    colis_id      = fields.Many2one('is.purchase.order.line.colis', 'Colis', required=True, ondelete='cascade')
    poids_colis   = fields.Float("Poids colis", related='colis_id.poids_colis')
    order_line_id = fields.Many2one('purchase.order.line', related='colis_id.line_id')
    colis_ids     = fields.Many2many('is.purchase.order.line.colis', 'is_purchase_order_line_colis_ids', 'line_id', 'colis_id', store=False, readonly=True, compute='_compute_colis_ids', string="Colis de la ligne")
    nb            = fields.Integer('Nb'      , required=True)
    longueur      = fields.Integer("Longueur", required=True)
    note          = fields.Char("Note")
    surface       = fields.Float("Surface (㎡)", digits=(14,2) , store=True, readonly=True, compute='_compute_surface_poids')
    poids         = fields.Float("Poids"       , digits=(14,2) , store=True, readonly=True, compute='_compute_surface_poids')
    forfait_coupe = fields.Integer("Forfait coupe"             , store=True, readonly=True, compute='_compute_surface_poids')


    @api.depends('nb','longueur')
    def _compute_surface_poids(self):
        for obj in self:
            surface = obj.nb*obj.longueur*obj.colis_id.largeur_utile/1000000
            obj.surface       = surface
            obj.poids         = surface*obj.colis_id.poids
            forfait_coupe = 0
            if obj.longueur<obj.colis_id.forfait_coupe_id.is_lg_mini_forfait:
                forfait_coupe = obj.nb
            obj.forfait_coupe = forfait_coupe


    @api.depends('colis_id')
    def _compute_colis_ids(self):
        for obj in self:
            filtre=[
                ("line_id"  ,"=", obj.order_line_id.id),
            ]
            colis = self.env['is.purchase.order.line.colis'].search(filtre)
            ids=[]
            for c in colis:
                ids.append(c.id)
            obj.colis_ids= [(6, 0, ids)]

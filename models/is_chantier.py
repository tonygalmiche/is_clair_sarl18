# -*- coding: utf-8 -*-
from odoo import api, fields, models  
from random import randint
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange
import base64


class IsEquipe(models.Model):
    _name='is.equipe'
    _description = "Equipe"
    _order='name'

    name       = fields.Char('Equipe', required=True, index=True)
    color      = fields.Char('Couleur')
    color_code = fields.Char('Code Couleur')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Cette équipe exite déjà !"),
    ]

    @api.onchange('color_code')
    def onchange_color_code(self):
        for obj in self:
            obj.color=obj.color_code


class IsChantier(models.Model):
    _name='is.chantier'
    _inherit = ["portal.mixin", "mail.thread", "mail.activity.mixin", "utm.mixin"]
    _description = "Chantiers"
    _order='name'

    name              = fields.Char('N°', index=True, readonly=True)
    affaire_id        = fields.Many2one('is.affaire', 'Affaire', required=False, tracking=True)
    contact_chantier_id = fields.Many2one(related='affaire_id.contact_chantier_id')
    equipe_id         = fields.Many2one('is.equipe', 'Equipe', required=False, tracking=True)
    equipe_color      = fields.Char('Couleur', help='Couleur Equipe', related="equipe_id.color")
    nature_travaux_id = fields.Many2one('is.nature.travaux', string="Nature des travaux", required=False, tracking=True)

    date_debut_souhaitee = fields.Date('Date début souhaitée', tracking=True)
    duree_souhaitee      = fields.Integer('Durée souhaitée (J)', tracking=True)

    date_debut        = fields.Date('Date début', required=True , tracking=True)
    duree             = fields.Integer('Durée (J)'              , tracking=True, compute='_compute_duree', store=True, readonly=True)
    date_fin          = fields.Date('Date fin'  , required=False, tracking=True)
    commentaire       = fields.Text('Commentaire'               , tracking=True)
    state = fields.Selection([
        ('a_planifier', 'A planifier'),
        ('en_cours'   , 'En cours'),
    ], 'Etat', index=True, default="a_planifier", required=True, tracking=True)
    alerte_ids  = fields.One2many('is.chantier.alerte', 'chantier_id', 'Alertes', tracking=True)
    alerte_html = fields.Text('Alertes ',compute='_compute_alerte_html', store=True, readonly=True, tracking=True)
    active      = fields.Boolean("Actif", default=True, copy=False)

    @api.depends('alerte_ids')
    def _compute_alerte_html(self):
        for obj in self:
            html=[]
            if obj.alerte_ids:
                for line in obj.alerte_ids:
                    html.append('%s:%s'%(line.date, line.alerte))
            obj.alerte_html='\n'.join(html)

    def recalculer_duree_action(self):
        for obj in self:
            obj._compute_duree()
 
    @api.depends('date_debut','date_fin')
    def _compute_duree(self):
        for obj in self:
            duree=0
            if obj.date_fin and obj.date_debut:
                duree = (obj.date_fin-obj.date_debut).days
                if duree<0:
                    duree=0
            obj.duree=duree

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.chantier')
        return super().create(vals_list)

    @api.model
    def move_chantier(self,chantierid=False,debut=False,decale_planning=0):
        if chantierid and debut:
            chantiers = self.env['is.chantier'].search([('id', '=',chantierid)])
            for chantier in chantiers:
                duree = chantier.duree
                now = date.today()
                jour = now.isoweekday()
                debut_planning = now - timedelta(days=(jour-1)) + timedelta(days=decale_planning)
                date_debut = debut_planning + timedelta(days=debut)
                chantier.date_debut = date_debut
                chantier.date_fin = chantier.date_debut + timedelta(days=duree)
        return 'OK'

    @api.model
    def modif_duree_chantier(self,chantierid=False,duree=False):
        if chantierid and duree:
            chantiers = self.env['is.chantier'].search([('id', '=',chantierid)])
            for chantier in chantiers:
                if chantier.date_debut:
                    chantier.date_fin = chantier.date_debut + timedelta(days=duree)
        return 'OK'

    def vers_en_encours(self):
        for obj in self:
            obj.state='en_cours'

    def vers_a_planifier(self):
        for obj in self:
            obj.state='a_planifier'

    def ajouter_alerte_action(self):
        date=self.date_debut - timedelta(days=1)
        res= {
            'name': 'Alerte',
            'view_mode': 'form',
            'res_model': 'is.chantier.alerte',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'default_chantier_id':self.id, 'default_date':date},
        }
        return res

    @api.model
    def get_chantiers(self,domain=[],decale_planning="", nb_semaines="", filtre_chantier=False, filtre_equipe=False, filtre_travaux=False, chantier_state=""):
        autorise_modif=False
        # Correction : utiliser self.env.user au lieu de self.user_has_groups
        domain=[]

        if self.env.user.has_group('is_clair_sarl18.is_responsable_planning_chantiers_group'):
            autorise_modif=True

        if nb_semaines=="":
            nb_semaines = self.env['is.mem.var'].get(self._uid, 'chantier_nb_semaine') or 16
        else:
            self.env['is.mem.var'].set(self._uid, 'chantier_nb_semaine', nb_semaines)
        if decale_planning=="":
            decale_planning = self.env['is.mem.var'].get(self._uid, 'chantier_decale_planning') or 16
        else:
            self.env['is.mem.var'].set(self._uid, 'chantier_decale_planning', decale_planning)

        if filtre_chantier==False:
            filtre_chantier = self.env['is.mem.var'].get(self._uid, 'filtre_chantier') or ""
        else:
            self.env['is.mem.var'].set(self._uid, 'filtre_chantier', filtre_chantier)
        if filtre_equipe==False:
            filtre_equipe = self.env['is.mem.var'].get(self._uid, 'filtre_equipe') or ""
        else:
            self.env['is.mem.var'].set(self._uid, 'filtre_equipe', filtre_equipe)
        if filtre_travaux==False:
            filtre_travaux = self.env['is.mem.var'].get(self._uid, 'filtre_travaux') or ""
        else:
            self.env['is.mem.var'].set(self._uid, 'filtre_travaux', filtre_travaux)

        if chantier_state=="":
            chantier_state = self.env['is.mem.var'].get(self._uid, 'chantier_state') or "Tous"
        else:
            self.env['is.mem.var'].set(self._uid, 'chantier_state', chantier_state)

        #** Liste de choix ****************************************************
        options = ["A planifier","En cours", "Tous"]
        state_options=[]
        for o in options:
            selected=False
            if o==chantier_state:
                selected=True
            state_options.append({
                "id": o,
                "name": o,
                "selected": selected,
            })
        #**********************************************************************

        #** Recherche des alertes *********************************************
        lines=self.env['is.chantier.alerte'].search([])
        alertes={}
        for line in lines:
            chantier_id = line.chantier_id.id
            date_alerte = line.date
            if chantier_id not in alertes:
                alertes[chantier_id]={}
            if date_alerte not in alertes[chantier_id]:
                alertes[chantier_id][date_alerte]=[]
            alertes[chantier_id][date_alerte].append(line)
        #**********************************************************************

        #** Recherche des jours de fermeture **********************************
        lines=self.env['is.fermeture'].search([], order='date_debut')
        fermetures=[]
        for line in lines:
            date_debut = line.date_debut
            date_fin   = line.date_fin or line.date_debut
            nb_jours = (date_fin - date_debut).days+1
            if nb_jours>0:
                for i in range(0,nb_jours):
                    if date_debut not in fermetures:
                        fermetures.append(date_debut)
                    date_debut+=timedelta(days=1)
        #**********************************************************************

        try:
            nb_semaines = int(nb_semaines)
        except:
            nb_semaines = 16
        try:
            decale_planning = int(decale_planning)
        except:
            decale_planning = 0
        if nb_semaines<4:
            nb_semaines=4
        if nb_semaines>40:
            nb_semaines=40
        nb_jours = nb_semaines*7
        now = date.today()
        jour = now.isoweekday()
        debut = now - timedelta(days=(jour-1)) + timedelta(days=decale_planning)
        debut_planning = debut
        fin_planning = debut + timedelta(days=nb_jours)

        #** Calcul du nombre de jours dans le mois pour le  colspan ***********
        mois={}
        jour = debut
        for x in range(0,nb_jours):
            if jour==debut or jour.day==1:
                nb_jours_dans_mois = monthrange(jour.year,jour.month)[1]
                if jour==debut:
                    colspan = nb_jours_dans_mois - jour.day +1
                if jour.day==1:
                    colspan = nb_jours_dans_mois
                vals={
                    "key"    : str(jour),
                    "mois"   : jour.strftime('%m/%Y'),
                    "colspan": colspan,
                }
                mois[str(jour)]=vals
            jour = jour + timedelta(days=1)
        #**********************************************************************

        #** Calcul du nombre de jours dans les semaines pour le  colspan ******
        semaines={}
        jour = debut
        for x in range(0,nb_jours):
            if jour.isoweekday()==1:
                nb_jours_dans_semaine = 7
            if jour==debut:
                nb_jours_dans_semaine = 7 - jour.isoweekday() + 1
            if jour==debut or jour.isoweekday()==1:
                colspan = nb_jours_dans_semaine
                vals={
                    "key"    : str(jour),
                    "semaine": jour.strftime('S%V'),
                    "jour"   : jour.strftime('%d'),
                    "colspan": colspan,
                }
                semaines[str(jour)]=vals
            jour = jour + timedelta(days=1)
        #**********************************************************************

        #** Ajout des filtres sur le domain ***********************************
        if filtre_chantier!='':
            domain.append(['affaire_id', 'ilike', filtre_chantier])
        if filtre_equipe!='':
            domain.append(['equipe_id', 'ilike', filtre_equipe])
        if filtre_travaux!='':
            domain.append(['nature_travaux_id', 'ilike', filtre_travaux])
        #**********************************************************************

        #** Recherche de la date de début de chaque affaire pour le tri *******
        date_debut_affaire={}
        chantiers=self.env['is.chantier'].search(domain)
        for chantier in chantiers:
            affaire_id = chantier.affaire_id.id or 0
            if affaire_id not in date_debut_affaire:
                date_debut_affaire[affaire_id]=chantier.date_debut
            if date_debut_affaire[affaire_id]>chantier.date_debut:
                date_debut_affaire[affaire_id]=chantier.date_debut
        #**********************************************************************

        #** Dictionnaire trié des chantiers par date début affaire ***********
        chantiers=self.env['is.chantier'].search(domain)
        my_dict={}
        for chantier in chantiers:
            #** Mettre à la fin les chantiers à plannifier*********************
            prefix=0
            if chantier.state=='a_planifier':
                prefix=1
            #******************************************************************
            affaire_id = chantier.affaire_id.id or 0
            date_affaire = date_debut_affaire[affaire_id]
            key = "%s-%s-%s-%s-%s"%(prefix,date_affaire,chantier.affaire_id.name,chantier.date_debut,chantier.name)
            my_dict[key]=chantier
        sorted_chantiers = dict(sorted(my_dict.items()))
        #**********************************************************************

        #** Contruction du dictionnaire finale des données dans le bon ordre **
        trcolor="#ffffff"
        mem_affaire=False
        res=[]
        my_dict={}
        width_jour = str(round(66/nb_jours,1))+"%"
        for k in sorted_chantiers:
            chantier = sorted_chantiers[k]
            #** Recherhce si le chantier est visible sur le planning **********
            test=False
            if chantier.date_debut>=debut_planning and chantier.date_debut<=fin_planning:
                test=True
            if chantier.date_fin>=debut_planning and chantier.date_fin<=fin_planning:
                test=True
            if chantier.date_debut<=debut_planning and chantier.date_fin>=fin_planning:
                test=True
            #******************************************************************

            #** Recherche si le chantier est dans l'état sélectionné **********
            if chantier_state=="En cours"    and chantier.state!="en_cours":
                test=False
            if chantier_state=="A planifier" and chantier.state!="a_planifier":
                test=False
            #******************************************************************

            if test:
                #** Changement de couleur à chaque affaire ********************
                if not mem_affaire:
                    mem_affaire=chantier.affaire_id
                if mem_affaire!=chantier.affaire_id:
                    mem_affaire=chantier.affaire_id
                    if trcolor=="#ffffff":
                        trcolor="#e5e7e9"
                    else:
                        trcolor="#ffffff"
                trstyle="background-color:%s"%(trcolor)
                color = chantier.equipe_id.color or 'GreenYellow'
                #**************************************************************

                decal = (chantier.date_debut - debut_planning).days
                jours={}
                duree = chantier.duree or (chantier.date_fin - chantier.date_debut).days
                if duree<1:
                    duree=1
                debut = decal+1
                fin = decal + duree 
                for i in range(0, nb_jours):
                    date_jour = debut_planning+timedelta(days=i)

                    #** Couleur de la fermeture *******************************
                    fermeture=''
                    if date_jour in fermetures:
                        fermeture='#FFE4C4'
                    #**********************************************************                    
                    
                    alerte=False
                    alerte_id=False
                    if chantier.id in alertes:
                        if date_jour in alertes[chantier.id]:
                            alerte = alertes[chantier.id][date_jour]
                    if alerte:
                        alerte_cumul=[]
                        for a in alerte:
                            alerte_cumul.append(a.alerte)
                            alerte_id = a.id
                        alerte='\n'.join(alerte_cumul)
                    border="none"
                    if i%7==0:
                        border="1px solid gray"
                    jour={
                        "key"      : i,
                        "color"    : "none",
                        "cursor"   : "default",
                        "border"   : border,
                        "date_jour": date_jour.strftime('%d/%m'),
                        "alerte"   : alerte,
                        "alerte_id": alerte_id,
                        "width"    : width_jour,
                        "fermeture": fermeture
                    }
                    if i>=decal and i<(decal+duree-1):
                        jour["color"]     = color
                        jour["cursor"]    = "move"
                        jour["border"]    = "none"
                        jour["fermeture"] = False
                    if i==(decal+duree-1):
                        jour["color"]     = color
                        jour["cursor"]    = "col-resize"
                        jour["border"]    = "none"
                        jour["fermeture"] = False
                    jours[i]=jour
                name=chantier.commentaire or chantier.name
                if chantier.affaire_id:
                    name=chantier.affaire_id.rec_name or '' #  name_get()[0][1]
                short_name = name[0:40]
                affaire_id = chantier.affaire_id.id or 0
                date_affaire = date_debut_affaire[affaire_id]
                #** Mettre à la fin les chantiers à plannifier*********************
                prefix=0
                if chantier.state=='a_planifier':
                    prefix=1
                #******************************************************************
                key = "%s-%s-%s-%s-%s"%(prefix,date_affaire,chantier.affaire_id.name,chantier.date_debut,chantier.name)
                vals={
                    "key"       : key,
                    "id"        : chantier.id,
                    "debut"     : debut,
                    "fin"       : fin,
                    "duree"     : duree,
                    "name"      : name,
                    "short_name": short_name,
                    "equipe"    : (chantier.equipe_id.name or '')[0:15],
                    "travaux"   : (chantier.nature_travaux_id.name or '')[0:15],
                    "trstyle"   : trstyle,
                    "jours"     : jours,
                }
                res.append(vals)
                my_dict[key]=vals
        sorted_dict = dict(sorted(my_dict.items()))

        return {
            "dict"           : sorted_dict,
            "mois"           : mois,
            "semaines"       : semaines,
            "nb_semaines"    : nb_semaines,
            "decale_planning": decale_planning,
            "autorise_modif" : autorise_modif,
            "state_options"  : state_options,
            "chantier_state" : chantier_state,
            "filtre_chantier": filtre_chantier,
            "filtre_equipe"  : filtre_equipe,
            "filtre_travaux" : filtre_travaux,
        }
    
    @api.model
    def get_planning_pdf(self):
        #** Recherche du premier chantier pour générer le planning PDF
        chantiers = self.env['is.chantier'].search([],limit=1)

        if len(chantiers)>0:
            chantier_id = chantiers[0].id
            report = self.env.ref('is_clair_sarl18.is_chantier_reports')
            pdf_content, _ = report._render_qweb_pdf(report, [chantier_id])
            datas = base64.b64encode(pdf_content).decode()

            # ** Recherche si une pièce jointe est déja associèe *******************
            attachment_obj = self.env['ir.attachment']
            name="planning_chantiers_%s.pdf"%self._uid
            attachments = attachment_obj.search([('name','=',name)],limit=1)
            # **********************************************************************

            # ** Creation ou modification de la pièce jointe ***********************
            vals = {
                'name':  name,
                'type':  'binary',
                'datas': datas,
            }
            if attachments:
                for attachment in attachments:
                    attachment.write(vals)
                    attachment_id=attachment.id
            else:
                attachment = attachment_obj.create(vals)
                attachment_id=attachment.id
            #***********************************************************************
            return attachment_id

    def recalage_auto_chantier_cron(self):
        today = date.today()
        filtre=[
            ('equipe_id' ,'=',False),
            ('date_debut','<',today + timedelta(days=7)),
            ('state','=','a_planifier'),
        ]
        chantiers = self.env['is.chantier'].search(filtre)
        for chantier in chantiers:
            vals={
                "date_debut": today + timedelta(days=21),
                "date_fin"  : today + timedelta(days=24),
            }
            chantier.write(vals)


class IsChantierAlerte(models.Model):
    _name='is.chantier.alerte'
    _description = "Alertes pour les chantiers"
    _order='id desc'

    chantier_id = fields.Many2one('is.chantier', 'Chantier', required=True, index=True)
    affaire_id  = fields.Many2one(related="chantier_id.affaire_id")
    alerte      = fields.Text('Alerte'                     , required=True)
    date        = fields.Date('Date alerte', default=fields.Datetime.now, index=True, help="Date à laquelle l'alerte sera positionnée sur le planning des chantiers")


class IsFermeture(models.Model):
    _name='is.fermeture'
    _description = "Fermetures de la société pour les chantiers"
    _order='date_debut desc'

    date_debut  = fields.Date('Date début fermeture', required=True)
    date_fin    = fields.Date('Date fin fermeture')
    commentaire = fields.Char('Commentaire')


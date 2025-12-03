# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from markupsafe import Markup


class IsDemandePrixSimplifiee(models.Model):
    _name = 'is.demande.prix.simplifiee'
    _description = "Demande de prix simplifiée"
    _order = 'name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("N°", readonly=True, copy=False)
    active = fields.Boolean("Actif", default=True)
    
    affaire_id = fields.Many2one(
        'is.affaire',
        'Affaire',
        domain="[('state', '=', 'commande')]",
        tracking=True,
        help="Affaire à l'état Commande"
    )
    
    type_demande = fields.Selection([
        ('demande_prix', 'Demande de prix'),
        ('commande', 'Commande fournisseur'),
    ], 'Type', default='demande_prix', required=True, tracking=True)
    
    fournisseur_ids = fields.Many2many(
        'res.partner', 
        'is_demande_prix_fournisseur_rel', 
        'demande_id', 
        'partner_id', 
        string="Fournisseurs",
        domain="[('supplier_rank', '>', 0), ('is_article_demande_prix_ids', '!=', False)]",
        required=True,
        tracking=True,
        help="Sélectionner les fournisseurs pour cette demande. Seuls les fournisseurs ayant une liste d'articles renseignée sont proposés."
    )
    
    product_ids_domain = fields.Many2many(
        'product.product',
        'is_demande_prix_product_domain_rel',
        'demande_id',
        'product_id',
        string="Articles disponibles",
        compute='_compute_product_ids_domain',
        store=False,
    )
    
    product_id = fields.Many2one(
        'product.product', 
        'Article',
        required=True,
        tracking=True,
        domain="[('id', 'in', product_ids_domain)]",
        help="Article à commander. La liste est filtrée selon les articles disponibles chez les fournisseurs sélectionnés."
    )
    
    quantite = fields.Float("Quantité à commander", default=1, required=True, tracking=True)
    
    photo = fields.Binary("Photo", attachment=True, help="Photo pour définir le besoin de la demande de prix")
    photo_filename = fields.Char("Nom du fichier photo")
    
    description = fields.Text("Description", help="Description complémentaire du besoin")
    
    purchase_order_ids = fields.One2many(
        'purchase.order', 
        'is_demande_prix_simplifiee_id', 
        string="Commandes générées",
        readonly=True
    )
    
    purchase_order_count = fields.Integer(
        "Nombre de commandes", 
        compute='_compute_purchase_order_count', 
        store=True
    )
    
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('envoye', 'Envoyé'),
    ], 'État', default='brouillon', tracking=True)

    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        for obj in self:
            obj.purchase_order_count = len(obj.purchase_order_ids)

    @api.depends('fournisseur_ids', 'fournisseur_ids.is_article_demande_prix_ids')
    def _compute_product_ids_domain(self):
        for obj in self:
            if obj.fournisseur_ids:
                obj.product_ids_domain = obj.fournisseur_ids.mapped('is_article_demande_prix_ids')
            else:
                obj.product_ids_domain = self.env['product.product']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('is.demande.prix.simplifiee') or 'Nouveau'
        return super().create(vals_list)

    @api.onchange('fournisseur_ids')
    def _onchange_fournisseur_ids(self):
        """Vide l'article si celui-ci n'est plus disponible chez les fournisseurs sélectionnés"""
        if self.fournisseur_ids:
            product_ids = self.fournisseur_ids.mapped('is_article_demande_prix_ids').ids
            if self.product_id and self.product_id.id not in product_ids:
                self.product_id = False
        else:
            self.product_id = False

    def generer_commandes_action(self):
        """Génère les commandes fournisseurs et les envoie par mail"""
        for obj in self:
            if not obj.fournisseur_ids:
                raise UserError(_("Veuillez sélectionner au moins un fournisseur."))
            if not obj.product_id:
                raise UserError(_("Veuillez sélectionner un article."))
            if obj.quantite <= 0:
                raise UserError(_("La quantité doit être supérieure à 0."))
            
            # Vérifier que tous les fournisseurs ont un contact demande de prix avec email
            fournisseurs_sans_contact = []
            fournisseurs_sans_email = []
            for fournisseur in obj.fournisseur_ids:
                if not fournisseur.is_contact_demande_prix_id:
                    fournisseurs_sans_contact.append(fournisseur.name)
                elif not fournisseur.is_contact_demande_prix_id.email:
                    fournisseurs_sans_email.append(fournisseur.name)
            
            if fournisseurs_sans_contact:
                raise UserError(
                    _("Les fournisseurs suivants n'ont pas de contact demande de prix configuré :\n- %s\n\nVeuillez configurer un contact demande de prix sur la fiche fournisseur.") 
                    % "\n- ".join(fournisseurs_sans_contact)
                )
            
            if fournisseurs_sans_email:
                raise UserError(
                    _("Les contacts demande de prix des fournisseurs suivants n'ont pas d'adresse email :\n- %s\n\nVeuillez configurer un email sur le contact demande de prix.") 
                    % "\n- ".join(fournisseurs_sans_email)
                )
            
            commandes_creees = []
            liens_commandes = []
            
            for fournisseur in obj.fournisseur_ids:
                # Créer la commande fournisseur pour chaque fournisseur sélectionné
                vals_po = {
                    'partner_id': fournisseur.id,
                    'is_demande_prix_simplifiee_id': obj.id,
                    'origin': obj.name,
                    'is_photo': obj.photo,  # Recopier la photo
                    'is_affaire_id': obj.affaire_id.id if obj.affaire_id else False,  # Recopier l'affaire
                }
                
                purchase_order = self.env['purchase.order'].create(vals_po)
                
                # Ajouter la ligne de commande
                vals_line = {
                    'order_id': purchase_order.id,
                    'product_id': obj.product_id.id,
                    'name': obj.product_id.display_name,
                    'product_qty': obj.quantite,
                    'product_uom': obj.product_id.uom_po_id.id or obj.product_id.uom_id.id,
                    'price_unit': obj.product_id.standard_price,
                    'date_planned': fields.Datetime.now(),
                }
                
                # Ajouter la description si présente
                if obj.description:
                    vals_line['name'] = f"{obj.product_id.display_name}\n{obj.description}"
                
                self.env['purchase.order.line'].create(vals_line)
                
                # Si c'est une commande, confirmer la commande
                if obj.type_demande == 'commande':
                    purchase_order.button_confirm()
                
                commandes_creees.append(purchase_order)
                
                # Créer le lien HTML vers la commande (sans base_url pour le chatter)
                lien = f'<a href="/web#id={purchase_order.id}&model=purchase.order&view_type=form">{purchase_order.name}</a>'
                liens_commandes.append(f"- {fournisseur.name}: {lien}")
                
                # Ajouter un message dans le chatter de la commande fournisseur
                lien_demande = Markup('<a href="/web#id=%s&model=is.demande.prix.simplifiee&view_type=form">%s</a>') % (obj.id, obj.name)
                purchase_order.message_post(
                    body=Markup(_("Cette commande a été créée depuis la demande de prix simplifiée %s")) % lien_demande,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )
                
                # Envoyer l'email au contact demande de prix
                contact = fournisseur.is_contact_demande_prix_id
                self._envoyer_email_commande(purchase_order, contact)
            
            if not commandes_creees:
                raise UserError(_("Aucune commande n'a pu être créée."))
            
            # Poster un message dans le chatter avec les liens vers les commandes
            type_label = "Commandes" if obj.type_demande == 'commande' else "Demandes de prix"
            message = Markup("<strong>%s générées :</strong><br/>%s") % (type_label, Markup("<br/>").join([Markup(l) for l in liens_commandes]))
            obj.message_post(
                body=message,
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
            
            obj.state = 'envoye'
            
            # Retourner l'affichage des commandes générées
            if len(commandes_creees) == 1:
                # Une seule commande : ouvrir le formulaire
                return {
                    'name': _('Commande générée'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_mode': 'form',
                    'res_id': commandes_creees[0].id,
                    'target': 'current',
                }
            else:
                # Plusieurs commandes : ouvrir la liste
                return {
                    'name': _('Commandes générées'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_mode': 'list,form',
                    'domain': [('id', 'in', [c.id for c in commandes_creees])],
                    'target': 'current',
                }

    def _envoyer_email_commande(self, purchase_order, contact):
        """Envoie un email au contact avec la commande via le chatter (comme l'envoi manuel)"""
        # Rechercher le template pour purchase.order selon le type de demande
        if self.type_demande == 'commande':
            # Pour une commande, utiliser le template de bon de commande
            template = self.env.ref('purchase.email_template_edi_purchase_done', raise_if_not_found=False)
        else:
            # Pour une demande de prix, utiliser le template de demande de prix
            template = self.env.ref('purchase.email_template_edi_purchase', raise_if_not_found=False)
        
        if not template:
            # Fallback: chercher l'autre template
            if self.type_demande == 'commande':
                template = self.env.ref('purchase.email_template_edi_purchase', raise_if_not_found=False)
            else:
                template = self.env.ref('purchase.email_template_edi_purchase_done', raise_if_not_found=False)
        
        if not template:
            # Chercher tous les templates pour purchase.order
            all_templates = self.env['mail.template'].search([('model_id.model', '=', 'purchase.order')])
            if all_templates:
                template = all_templates[0]
        
        if template and contact.email:
            try:
                # Utiliser message_post_with_source pour avoir le même comportement
                # que l'envoi manuel (message dans le chatter avec PDF et statut d'envoi)
                purchase_order.message_post_with_source(
                    template,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    email_layout_xmlid='mail.mail_notification_light',
                    partner_ids=[contact.id],
                    force_send=True,
                )
            except Exception as e:
                purchase_order.message_post(
                    body=Markup(_("Erreur lors de l'envoi de l'email à %s : %s")) % (contact.email, str(e)),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note'
                )

    def voir_commandes_action(self):
        """Ouvre la liste des commandes générées"""
        self.ensure_one()
        return {
            'name': _("Commandes générées"),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('is_demande_prix_simplifiee_id', '=', self.id)],
            'context': {'default_is_demande_prix_simplifiee_id': self.id},
        }

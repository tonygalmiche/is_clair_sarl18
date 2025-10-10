# -*- coding: utf-8 -*-
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _is_thread_message(self, msg_vals=None):
        """Surcharge pour désactiver TOUS les boutons d'accès dans TOUS les emails
        
        Cette méthode contrôle l'affichage du bouton "Voir [Document]" dans tous les emails.
        En retournant toujours False, on s'assure qu'aucun client ne peut accéder à Odoo
        via les liens dans les emails.
        """
        print(f'TEST - Désactivation lien Odoo pour modèle: {self._name}')
        return False

    def _notify_get_action_link(self, link_type, **kwargs):
        """Surcharge pour supprimer complètement la génération des liens d'accès
        
        En retournant un lien vide, on s'assure qu'aucun lien vers Odoo n'est généré
        dans les emails, quelque soit le contexte.
        """
        print(f'TEST - Suppression génération de lien pour modèle: {self._name}')
        return ""

    def _notify_get_recipients_groups_fillup(self, groups, model_description, msg_vals=None):
        """Surcharge pour forcer has_button_access à False dans tous les groupes"""
        result = super()._notify_get_recipients_groups_fillup(groups, model_description, msg_vals)
        
        print(f'TEST - Modification des groupes de destinataires pour modèle: {self._name}')
        
        # Forcer has_button_access à False pour tous les groupes
        for group_name, _group_func, group_data in result:
            group_data['has_button_access'] = False
            if 'button_access' in group_data:
                group_data['button_access']['url'] = ""
                
        return result
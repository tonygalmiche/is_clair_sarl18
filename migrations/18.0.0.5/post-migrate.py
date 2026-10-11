# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Met le pays France sur tous les partenaires qui n'ont pas de pays.

    La facturation electronique (account_invoice_en16931) refuse de valider
    une facture si le client (societe ou contact facture) n'a pas de pays.
    Constat (clair-sarl18, 2026-10-11) : 733 partenaires sans pays, dont
    259 clients factures (145 depuis 2025), tous francais. Clair SARL ne
    travaille qu'en France : France pour tous, sans condition.

    Ecriture par l'ORM (actifs et archives), sans revalider les numeros de
    TVA (no_vat_validation, prevu par base_vat) : avec le pays France,
    base_vat refusait 2 numeros a corriger a la main (ART : SIRET dans le
    champ TVA ; GCBAT : prefixe FR manquant).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    partners = env["res.partner"].with_context(active_test=False, no_vat_validation=True).search(
        [("country_id", "=", False)]
    )
    partners.write({"country_id": env.ref("base.fr").id})

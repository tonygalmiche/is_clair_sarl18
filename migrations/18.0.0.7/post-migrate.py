# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

# Taxes de vente gardees : id -> (libelle, categorie UNECE, motif d'exoneration)
TAXES_CODES = {
    1: ("V20%", "tax_categ_s", None),
    2: ("TVA à l'encaissement (vente) 10,0%", "tax_categ_s", None),
    3: ("TVA à l'encaissement (vente) 20,0%", "tax_categ_s", None),
    5: ("TVA collectée (vente) 10,0%", "tax_categ_s", None),
    6: ("TVA collectée (vente) 5,5%", "tax_categ_s", None),
    47: ("Exo TVA", "tax_categ_ae", "tax_vatex_eu_ae"),
    48: ("TVA 0% export (vente)", "tax_categ_g", "tax_vatex_eu_g"),
    49: ("TVA 0% livraisons intracommunautaires (vente)", "tax_categ_k", "tax_vatex_eu_ic"),
}

# Taxes de vente archivees : id -> libelle
TAXES_ARCHIVEES = {
    4: "TVA collectée (vente) 8,5%",
    7: "TVA réduite à l'encaissement (vente) 5.5%",
    8: "TVA collectée (vente) 2,1%",
    9: "TVA réduite à l'encaissement (vente) 2.1%",
    10: "TVA collectée (vente) 20,0% TTC",
    11: "TVA à l'encaissement (vente) 10,0% TTC",
    12: "TVA à l'encaissement (vente) 20,0% TTC",
    13: "TVA collectée (vente) 8,5% TTC",
    14: "TVA collectée (vente) 10,0% TTC",
    15: "TVA collectée (vente) 5,5% TTC",
    16: "TVA réduite à l'encaissement (vente) 5.5% TTC",
    17: "TVA collectée (vente) 2,1% TTC",
    18: "TVA réduite à l'encaissement (vente) 2.1% TTC",
}


def migrate(cr, version):
    """Codes UNECE des taxes de vente et archivage des taxes inutilisees.

    La facturation electronique (account_invoice_en16931) controle toutes
    les taxes de vente actives a la validation de chaque facture : type
    UNECE, categorie et, pour les taxes a 0 %, motif d'exoneration (VATEX).

    Gardees, avec type VAT :
    - categorie S : V20%, TVA collectee 10 % et 5,5 % (cibles des positions
      fiscales "TVA 10%" et "TVA 5.5% (Renovation energetique)"), TVA a
      l'encaissement 10 % et 20 % (factures encore reglees en 2026) ;
    - Exo TVA : autoliquidation sous-traitance BTP, categorie AE,
      VATEX-EU-AE ;
    - export (G, VATEX-EU-G) et intracommunautaire (K, VATEX-EU-IC) :
      cibles des positions fiscales "Import/Export" et "Intra-EU B2B" (une
      taxe cible archivee est supprimee des factures au lieu d'etre
      remplacee).

    Archivees : les 13 autres (8,5 %, 2,1 %, TTC, 5,5 % a l'encaissement),
    sur aucune facture depuis 2025, aucun produit ni aucune cible de position
    fiscale. L'archivage ne touche pas aux factures existantes.

    Ids et libelles identiques sur clair-sarl18 et en production le
    2026-10-11, controles avant modification. Necessite
    l10n_fr_account_invoice_en16931 (champs de account_tax_unece) : a
    installer avant cette mise a jour.
    """
    env = api.Environment(cr, SUPERUSER_ID, {"lang": "fr_FR", "active_test": False})
    Tax = env["account.tax"]
    if "unece_categ_id" not in Tax._fields:
        raise Exception(
            "is_clair_sarl18 0.7 : installer l10n_fr_account_invoice_en16931 "
            "avant de mettre a jour is_clair_sarl18"
        )
    libelles = {tax_id: name for tax_id, (name, categ, vatex) in TAXES_CODES.items()}
    libelles.update(TAXES_ARCHIVEES)
    for tax_id, name in libelles.items():
        tax = Tax.browse(tax_id).exists()
        if not tax or tax.name != name or tax.type_tax_use != "sale":
            raise Exception(
                "is_clair_sarl18 0.7 : taxe %s introuvable ou differente de %r" % (tax_id, name)
            )
    vat = env.ref("account_tax_unece.tax_type_vat")
    for tax_id, (name, categ, vatex) in TAXES_CODES.items():
        Tax.browse(tax_id).write({
            "unece_type_id": vat.id,
            "unece_categ_id": env.ref("account_tax_unece.%s" % categ).id,
            "unece_vatex_id": vatex and env.ref("account_tax_unece.%s" % vatex).id,
        })
    Tax.browse(list(TAXES_ARCHIVEES)).write({"active": False})

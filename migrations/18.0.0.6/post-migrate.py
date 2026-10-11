# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Position fiscale "Exo de TVA" : V20% remplacee par "Exo TVA" au lieu
    d'etre supprimee.

    La position "Exo de TVA" (note : "TVA auto-liquidee par l'acquereur -
    article 283-2 nonies du C.G.I.", autoliquidation de la sous-traitance
    BTP) supprimait la taxe V20% sans la remplacer : les lignes de facture
    se retrouvaient sans taxe, ce que refuse la facturation electronique
    (account_invoice_en16931 : exactement une TVA par ligne). Elle remplace
    maintenant V20% par "Exo TVA" (vente), comme la position
    "Auto-liquidation de la TVA".

    Ids verifies sur clair-sarl18 et en production le 2026-10-11 (position
    6, taxes 1 et 47), controles par leur libelle avant modification. Ne
    touche pas aux factures existantes.
    """
    env = api.Environment(cr, SUPERUSER_ID, {"lang": "fr_FR", "active_test": False})
    position = env["account.fiscal.position"].browse(6).exists()
    v20 = env["account.tax"].browse(1).exists()
    exo = env["account.tax"].browse(47).exists()
    if not (
        position and position.name == "Exo de TVA"
        and v20 and v20.name == "V20%" and v20.type_tax_use == "sale"
        and exo and exo.name == "Exo TVA" and exo.type_tax_use == "sale"
    ):
        return
    lines = position.tax_ids.filtered(lambda line: line.tax_src_id == v20 and not line.tax_dest_id)
    lines.write({"tax_dest_id": exo.id})

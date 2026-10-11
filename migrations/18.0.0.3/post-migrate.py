# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


# Lignes de la declaration de TVA (l10n_fr_account) dont l'expression
# "balance" existe en base sans xmlid, et xmlid attendu par
# l10n_fr_account/data/tax_report_data.xml pour cette expression
EXPRESSIONS = {
    "tax_report_16": "tax_report_16_formula",
    "tax_report_23": "tax_report_23_formula",
    "tax_report_TIC_total": "tax_report_TIC_total_formula",
    "tax_report_X4": "tax_report_X4_formula",
    "tax_report_Y1": "tax_report_Y1_formula",
    "tax_report_Y2": "tax_report_Y2_formula",
    "tax_report_Y3": "tax_report_Y3_formula",
    "tax_report_Z4": "tax_report_Z4_formula",
    "tax_report_32": "tax_report_32_formula",
}


def migrate(cr, version):
    """Rattache a leur xmlid standard 9 expressions de la declaration de TVA
    restees sans xmlid apres la migration de cette base vers Odoo 18.0.

    Le rapport de TVA de l10n_fr_account a ete refondu dans la branche 18.0
    sans changement de version du module (toujours 2.2), donc sans script
    de migration Odoo. Au -u, le XML veut creer l'expression
    tax_report_<...>_formula (label "balance") alors que la ligne en a deja
    une sans xmlid : contrainte account_report_expression_line_label_uniq
    (constate sur clair-sarl18 le 2026-10-11, ligne box_16).

    Une fois rattachees, ces expressions sont simplement mises a jour par le
    -u (formule standard actuelle). Aucune donnee comptable n'est modifiee.

    A lancer par un -u is_clair_sarl18 AVANT le -u base (cf. migration
    18.0.0.2).
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    imd_model = env["ir.model.data"]
    expression_model = env["account.report.expression"]

    for line_xmlid, expression_xmlid in EXPRESSIONS.items():
        if env.ref("l10n_fr_account.%s" % expression_xmlid, raise_if_not_found=False):
            continue
        line = env.ref("l10n_fr_account.%s" % line_xmlid, raise_if_not_found=False)
        if not line:
            continue
        expression = expression_model.search(
            [("report_line_id", "=", line.id), ("label", "=", "balance")], limit=1
        )
        if not expression:
            continue
        imd_model.create(
            {
                "module": "l10n_fr_account",
                "name": expression_xmlid,
                "model": "account.report.expression",
                "res_id": expression.id,
            }
        )

# -*- coding: utf-8 -*-
from lxml import etree

from odoo import api, SUPERUSER_ID
from odoo.tools import file_open


def migrate(cr, version):
    """Repare les xmlids standards laisses incoherents par la migration de
    cette base vers Odoo 18.0 (meme defaut que celui deja corrige sur
    is_opta_s18, migrations 18.0.0.2 a 18.0.0.4, et sur is_coheliance18 pour
    uom).

    Constat (base clair-sarl18, 2026-10-11) : les tables res_currency et
    uom_uom sont restees celles de l'ancienne version, alors que
    ir_model_data a ete rempli avec les listes d'Odoo 18.0 (davantage de
    lignes, inserees par ordre alphabetique, ce qui decale les ids) :
    - 51 xmlids base.<CODE> pointent vers une autre devise (ex: base.EUR vers
      "VUV", base.USD vers "EUR"), base.UYI et base.STN vers des ids
      inexistants, et CNH, ZIG, SLE n'existent pas en base. Le -u base
      echoue sur la creation de UYI (contrainte res_currency_unique_name) ;
    - res_country.currency_id a ete enregistre avec ces mauvais ids lors du
      chargement des donnees (ex: France -> VUV) ;
    - 8 xmlids uom.* d'unites imperiales pointent vers une autre unite (ex:
      uom.product_uom_mile vers "ft²") et l'unite "yd" n'existe pas.

    Seuls ir_model_data, res_country.currency_id et la creation de l'unite
    "yd" sont touches : aucune devise, unite ni donnee metier existante n'est
    modifiee (elles referencent une devise/unite par son id, jamais par
    xmlid).

    A lancer par un -u is_clair_sarl18 AVANT le -u base, qui echoue sinon
    sur les devises avant d'arriver a ce module.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    imd_model = env["ir.model.data"]
    # active_test=False : presque toutes les devises sont inactives (cf.
    # is_opta_s18, migration 18.0.0.4)
    currency_model = env["res.currency"].with_context(active_test=False)

    # --- Devises : xmlids base.<CODE> -----------------------------------
    currency_xmlids = imd_model.search(
        [("module", "=", "base"), ("model", "=", "res.currency")]
    )
    for imd in currency_xmlids:
        correct_currency = currency_model.search([("name", "=", imd.name)], limit=1)
        if not correct_currency:
            # Devise absente de la base (ajoutee a la liste standard apres
            # l'ancienne version) : le -u base la creera depuis
            # res_currency_data.xml une fois l'xmlid supprime
            imd.unlink()
        elif imd.res_id != correct_currency.id:
            imd.write({"res_id": correct_currency.id})

    # --- Pays : res_country.currency_id -----------------------------------
    # Devise de chaque pays d'apres la donnee standard Odoo
    with file_open("base/data/res_country_data.xml", "rb") as f:
        doc = etree.parse(f)
    country_currency = {}
    for record in doc.iterfind(".//record[@model='res.country']"):
        code = record.findtext("field[@name='code']")
        currency = record.find("field[@name='currency_id']")
        if code and currency is not None:
            country_currency[code.upper()] = currency.get("ref")

    country_model = env["res.country"].with_context(active_test=False)
    for code, currency_code in country_currency.items():
        country = country_model.search([("code", "=", code)], limit=1)
        correct_currency = currency_model.search([("name", "=", currency_code)], limit=1)
        if country and correct_currency and country.currency_id != correct_currency:
            country.currency_id = correct_currency.id

    # --- Unites de mesure : xmlids uom.* ------------------------------------
    # Ids verifies ligne par ligne (nom, facteur, categorie) sur clair-sarl18
    uom_remap = {
        "product_uom_mile": 19,
        "uom_square_foot": 20,
        "product_uom_floz": 21,
        "product_uom_qt": 22,
        "product_uom_gal": 23,
        "product_uom_cubic_inch": 24,
        "product_uom_cubic_foot": 25,
    }
    uom_model = env["uom.uom"].with_context(active_test=False)
    for name, res_id in uom_remap.items():
        imd = imd_model.search(
            [("module", "=", "uom"), ("model", "=", "uom.uom"), ("name", "=", name)], limit=1
        )
        if imd and imd.res_id != res_id and uom_model.browse(res_id).exists():
            imd.write({"res_id": res_id})

    # Le yard n'existe pas en base : son xmlid pointe vers une unite deja
    # reprise ci-dessus (mile) -> creation de l'unite standard
    yard_imd = imd_model.search(
        [("module", "=", "uom"), ("model", "=", "uom.uom"), ("name", "=", "product_uom_yard")], limit=1
    )
    if yard_imd and yard_imd.res_id in uom_remap.values():
        length_categ = env.ref("uom.uom_categ_length")
        yard = uom_model.create(
            {"name": "yd", "category_id": length_categ.id, "factor": 1.09361, "uom_type": "smaller"}
        )
        yard_imd.write({"res_id": yard.id})

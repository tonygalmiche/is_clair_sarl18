# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


# xmlid -> (id, modele, libelle en base) du sous-type correspondant, verifie
# ligne par ligne (modele, libelle, parent) sur clair-sarl18 le 2026-10-11.
# Les libelles "en_US" de cette base sont en francais.
SUBTYPES = {
    "sale.mt_order_sent": (7, "sale.order", "Devis envoyé"),
    "sale.mt_order_confirmed": (8, "sale.order", "Commande de vente confirmée"),
    "sale.mt_salesteam_order_sent": (9, "crm.team", "Devis envoyé"),
    "sale.mt_salesteam_order_confirmed": (10, "crm.team", "Commande de vente confirmée"),
    "sale.mt_salesteam_invoice_created": (11, "crm.team", "Facture créée"),
    "sale.mt_salesteam_invoice_confirmed": (12, "crm.team", "Facture confirmée"),
    "purchase.mt_rfq_confirmed": (13, "purchase.order", "Demande de prix confirmée"),
    "purchase.mt_rfq_approved": (14, "purchase.order", "Demande de prix approuvée"),
    "purchase.mt_rfq_done": (15, "purchase.order", "Demande de prix terminée"),
}

# xmlids sans sous-type correspondant en base : sous-type standard cree ici
# (valeurs de sale/data/mail_message_subtype_data.xml et
# purchase/data/purchase_data.xml, libelles en francais comme le reste de la
# base). Ils ne peuvent pas attendre un -u sale,purchase : utilises par
# env.ref() dans purchase_order.py (_track_subtype, tableau de bord) et dans
# le portail des devis (sale/controllers/portal.py).
# Ordre important : mt_order_viewed est le parent de mt_salesteam_order_viewed.
SUBTYPES_TO_CREATE = [
    ("sale.mt_order_viewed", {
        "name": "Devis consulté", "res_model": "sale.order",
        "internal": True, "default": True,
    }),
    ("sale.mt_salesteam_order_viewed", {
        "name": "Devis consulté", "sequence": 25, "res_model": "crm.team",
        "default": True, "parent_xmlid": "sale.mt_order_viewed", "relation_field": "team_id",
    }),
    ("purchase.mt_rfq_sent", {
        "name": "Envoyé", "res_model": "purchase.order", "default": False,
    }),
]


def migrate(cr, version):
    """Repare le mapping ir_model_data <-> mail.message.subtype de sale et
    purchase, laisse incoherent par la migration de cette base vers Odoo
    18.0 (meme defaut que pour les devises et unites, cf. migration
    18.0.0.2).

    Constat (clair-sarl18, 2026-10-11) : les xmlids sale.* et purchase.*
    des sous-types de messages pointaient vers d'autres sous-types (ex:
    sale.mt_order_sent vers "Facture creee" de l'equipe commerciale,
    purchase.mt_rfq_done vers "Devis envoye" de l'equipe commerciale). Un
    -u base cree alors des doublons (sous-types "Sales Order Confirmed" et
    "Invoice Confirmed" de crm.team, dont un portant deux xmlids).

    Corrige ir_model_data, cree les 3 sous-types standard absents de la base
    et supprime les doublons crm.team restes sans xmlid, sans message ni
    abonne : aucun message ni abonnement existant n'est modifie. Fonctionne
    avant comme apres un -u base.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    imd_model = env["ir.model.data"]
    subtype_model = env["mail.message.subtype"].with_context(lang="en_US")

    def imd_for(xmlid):
        module, name = xmlid.split(".")
        return imd_model.search(
            [("module", "=", module), ("name", "=", name), ("model", "=", "mail.message.subtype")],
            limit=1,
        )

    for xmlid, (res_id, res_model, label) in SUBTYPES.items():
        imd = imd_for(xmlid)
        subtype = subtype_model.browse(res_id).exists()
        if imd and subtype and subtype.res_model == res_model and subtype.name == label:
            if imd.res_id != res_id:
                imd.write({"res_id": res_id})

    mapped_ids = [res_id for res_id, _, _ in SUBTYPES.values()]
    # Id du sous-type correct par xmlid, lu dans ir_model_data et non par
    # env.ref() : son cache garde l'ancien res_id d'un xmlid qui vient d'etre
    # modifie dans cette meme migration
    subtype_ids = {}
    for xmlid, vals in SUBTYPES_TO_CREATE:
        imd = imd_for(xmlid)
        if imd and imd.res_id not in mapped_ids and subtype_model.browse(imd.res_id).exists():
            subtype_ids[xmlid] = imd.res_id  # deja correct
            continue
        vals = dict(vals)
        parent_xmlid = vals.pop("parent_xmlid", False)
        if parent_xmlid:
            vals["parent_id"] = subtype_ids[parent_xmlid]
        subtype = subtype_model.create(vals)
        subtype_ids[xmlid] = subtype.id
        if imd:
            imd.write({"res_id": subtype.id})
        else:
            module, name = xmlid.split(".")
            imd_model.create(
                {"module": module, "name": name, "model": "mail.message.subtype",
                 "res_id": subtype.id, "noupdate": True}
            )

    # Doublons crees par un -u base fait avant cette correction
    with_xmlid = imd_model.search([("model", "=", "mail.message.subtype")]).mapped("res_id")
    duplicates = subtype_model.search(
        [("res_model", "=", "crm.team"), ("id", "not in", with_xmlid)]
    )
    for subtype in duplicates:
        cr.execute("SELECT 1 FROM mail_message WHERE subtype_id = %s LIMIT 1", [subtype.id])
        has_message = cr.fetchone()
        cr.execute(
            "SELECT 1 FROM mail_followers_mail_message_subtype_rel WHERE mail_message_subtype_id = %s LIMIT 1",
            [subtype.id],
        )
        has_follower = cr.fetchone()
        if not has_message and not has_follower:
            subtype.unlink()

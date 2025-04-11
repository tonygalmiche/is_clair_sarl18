# -*- coding: utf-8 -*-
from odoo import api, fields, models  # type: ignore
import codecs
import unicodedata
import base64
import openpyxl


def xls2float(val):
    try:
        res = float(val or 0)
    except ValueError:
        res = 0
    return res


class IsImportClair(models.Model):
    _name = 'is.import.clair'
    _description = "Importation de fichiers Excel pour Clair SARL"


    name     = fields.Char("Description", required=True)
    file_ids = fields.Many2many('ir.attachment', 'is_import_clair_attachment_rel', 'doc_id', 'file_id', 'Fichiers')


    def importation_excel_action(self):
        for obj in self:
            for attachment in obj.file_ids:
                xlsxfile=base64.b64decode(attachment.datas)

                path = '/tmp/is_import_clair-'+str(obj.id)+'.xlsx'
                f = open(path,'wb')
                f.write(xlsxfile)
                f.close()

                #** Test si fichier est bien du xlsx **************************
                try:
                    wb    = openpyxl.load_workbook(filename = path, data_only=True)
                except:
                    raise Warning("Le fichier "+attachment.name+u" n'est pas un fichier xlsx")
                #**************************************************************


            ws = wb.active # ws = wb['base 2022']
            cells = list(ws)


            #** Création des fournisseurs *************************************
            lig=0
            fournisseurs=[]
            for row in ws.rows:
                if lig>0:
                    fournisseur = cells[lig][0].value
                    if fournisseur:
                        if fournisseur not in fournisseurs:
                            fournisseurs.append(fournisseur)
                lig+=1
            for fournisseur in fournisseurs:
                partner_id = False
                partners = self.env['res.partner'].search([("name","=",fournisseur)])
                for partner in partners:
                    partner_id = partner.id
                if partner_id==False:
                    vals={
                        "name"         : fournisseur,
                        "company_type" : "company",
                        "supplier_rank": 1,
                    }
                    partner=self.env['res.partner'].create(vals)
                    partner_id = partner.id
            #******************************************************************



            #** Création des Sous-familles ************************************
            lig=0
            sous_familles=[]
            for row in ws.rows:
                if lig>0:
                    sous_famille = cells[lig][2].value
                    if sous_famille:
                        if sous_famille not in sous_familles:
                            sous_familles.append(sous_famille)
                lig+=1
            for sous_famille in sous_familles:
                sous_famille_id = False
                lines = self.env['is.sous.famille'].search([("name","=",sous_famille)])
                for line in lines:
                    sous_famille_id = line.id
                if sous_famille_id==False:
                    vals={
                        "name": sous_famille,
                    }
                    res=self.env['is.sous.famille'].create(vals)
                    sous_famille_id = res.id
            #******************************************************************



            #** Création des familles *****************************************
            lig=0
            familles={}
            for row in ws.rows:
                if lig>0:
                    famille      = cells[lig][1].value
                    sous_famille = cells[lig][2].value

                    if famille:
                        if famille not in familles:
                            familles[famille]=[]

                    if sous_famille:
                        lines = self.env['is.sous.famille'].search([("name","=",sous_famille)])
                        for line in lines:
                            if line.id not in familles[famille]:
                                familles[famille].append(line.id)
                lig+=1
            for famille in familles:
                famille_id = False
                lines = self.env['is.famille'].search([("name","=",famille)])
                for line in lines:
                    famille_id = line.id
                if famille_id==False:
                    vals={
                        "name": famille,
                        "sous_famille_ids": [(6, 0, familles[famille])],
                        "is_longueur": True,
                        "is_largeur_utile": True,
                        "is_surface_panneau": True,
                        "is_surface_palette": True,
                        "is_poids": True,
                        "is_poids_rouleau": True,
                        "is_ondes": True,
                        "is_resistance_thermique": True,
                        "is_lambda": True,
                    }
                    famille=self.env['is.famille'].create(vals)
            #******************************************************************

            unites={
                "U" : "uom.product_uom_unit",	  # Unité
                "BD": "uom.product_uom_unit",	  # Unité
                "M²": "uom.uom_square_meter",     #	m²
                "ML": "uom.product_uom_meter",    # Longueur/distance
            }

            #** Création des articles *****************************************
            lig=0
            fournisseurs=[]
            for row in ws.rows:
                if lig>0:
                    fournisseur     = cells[lig][0].value
                    famille         = cells[lig][1].value
                    sous_famille    = cells[lig][2].value
                    code            = cells[lig][3].value
                    designation     = cells[lig][4].value
                    unite           = cells[lig][5].value
                    largeur_utile   = cells[lig][6].value
                    ondes           = cells[lig][7].value
                    poids           = cells[lig][8].value
                    r               = cells[lig][9].value
                    is_lambda       = cells[lig][10].value
                    surface_palette = cells[lig][11].value
                    surface_panneau = cells[lig][12].value
                    annotation      = cells[lig][13].value
                    prix            = cells[lig][14].value


                    if fournisseur and designation:
                        if not code:
                            code="XX-"+str(lig)
                        code=str(code).upper()

                        filtre=[("default_code","=",code)]
                        products = self.env['product.template'].search(filtre)

                        famille_id=False
                        lines = self.env['is.famille'].search([("name","=",famille)])
                        for line in lines:
                            famille_id = line.id

                        sous_famille_id=False
                        lines = self.env['is.sous.famille'].search([("name","=",sous_famille)])
                        for line in lines:
                            sous_famille_id = line.id

                        uom_id = self.env.ref("uom.product_uom_unit").id
                        if unite:
                            unite=unite.upper()
                            if unite in unites:
                                uom_id = self.env.ref(unites[unite]).id

                        vals={
                            "name"              : designation,
                            "default_code"      : code,
                            "is_famille_id"     : famille_id,
                            "is_sous_famille_id": sous_famille_id,
                            "uom_id"            : uom_id,
                            "uom_po_id"         : uom_id,
                            "is_largeur_utile"  : largeur_utile or 0,
                            "is_ondes"          : ondes or 0,
                            "is_poids"          : poids or 0,
                            "is_resistance_thermique": r or 0,
                            "is_lambda"         : is_lambda or 0,
                            "is_surface_palette": surface_palette or 0,
                            "is_surface_panneau": surface_panneau or 0,
                            "description"       : annotation,
                            "list_price"        : 0,
                        }



                        if len(products)==0:
                            product=self.env['product.template'].create(vals)
                        else:
                            product = products[0]
                            product.write(vals)

                        #** Création ligne tarif fournisseur ******************
                        partner_id=False
                        lines = self.env['res.partner'].search([("name","=",fournisseur)])
                        for line in lines:
                            partner_id = line.id
                        if partner_id:
                            vals={
                                "product_tmpl_id": product.id,
                                "name"           : partner_id,
                                "min_qty"        : 1,
                                "price"          : prix,
                            }
                            filtre=[("product_tmpl_id","=",product.id)]
                            supplierinfos = self.env['product.supplierinfo'].search(filtre)
                            if len(supplierinfos)==0:
                                supplierinfo=self.env['product.supplierinfo'].create(vals)
                            else:
                                supplierinfo = supplierinfos[0]
                                supplierinfo.write(vals)
                lig+=1



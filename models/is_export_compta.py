# -*- coding: utf-8 -*-
from odoo import api, fields, models   
import codecs
import base64


class IsExportComptaLigne(models.Model):
    _name = 'is.export.compta.ligne'
    _description = "Export Compta Lignes"
    _order='ligne,id'

    export_compta_id = fields.Many2one('is.export.compta', 'Export Compta', required=True, ondelete='cascade')
    ligne            = fields.Integer("Ligne")
    code_journal     = fields.Char("Journal")
    date             = fields.Date("Date")
    num_piece        = fields.Char("N°Pièce")
    num_facture      = fields.Char("N°Facture")
    num_compte       = fields.Char("N°Compte")
    libelle          = fields.Char("Libellé")
    debit            = fields.Float("Debit" , digits=(14,2))
    credit           = fields.Float("Credit", digits=(14,2))
    partner_id       = fields.Many2one('res.partner', 'Partenaire')
    invoice_id       = fields.Many2one('account.move', 'Facture')


class IsExportCompta(models.Model):
    _name = 'is.export.compta'
    _description = "Export Compta"
    _order = 'name desc'

    name       = fields.Char("N°Folio", readonly=True)
    journal    = fields.Selection([
        ('AC', 'Achat'),
        ('VE', 'Ventes'),
    ], 'Journal')
    date_fin   = fields.Date("Date de fin"  , required=True, default=lambda *a: fields.Date.today())
    ligne_ids  = fields.One2many('is.export.compta.ligne', 'export_compta_id', 'Lignes')
    file_ids   = fields.Many2many('ir.attachment', 'is_export_compta_attachment_rel', 'doc_id', 'file_id', u'Fichiers')
    company_id = fields.Many2one('res.company', 'Société',required=True,default=lambda self: self.env.user.company_id.id)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('is.export.compta')
        return super().create(vals_list)


    def generer_lignes_action(self):
        cr = self._cr
        for obj in self:
            invoices = self.env['account.move'].search([('is_export_compta_id','=',obj.id)])
            for invoice in invoices:
                invoice.is_export_compta_id=False
            obj.ligne_ids.unlink()
            sql="""
                SELECT  
                    aj.code code_journal,
                    am.invoice_date date,
                    am.ref num_piece,
                    am.name num_facture,
                    aa.code num_compte,
                    rp.is_compte_auxiliaire_client,
                    rp.is_compte_auxiliaire,
                    am.partner_id,
                    am.id invoice_id,
                    sum(aml.debit) debit,
                    sum(aml.credit) credit
                    FROM account_move_line aml inner join account_move am                on aml.move_id=am.id
                                           inner join account_account aa             on aml.account_id=aa.id
                                           left outer join res_partner rp            on aml.partner_id=rp.id
                                           inner join account_journal aj             on aml.journal_id=aj.id
                WHERE 
                     am.is_export_compta_id is null and
                     am.invoice_date<=%s and aj.code=%s and
                     am.state='posted'
                GROUP BY
                    aj.code,
                    am.invoice_date,
                    am.ref,
                    am.name,
                    aa.code,
                    rp.is_compte_auxiliaire_client,
                    rp.is_compte_auxiliaire,
                    am.partner_id,
                    am.id
                ORDER BY am.invoice_date, am.name
            """
            cr.execute(sql,[obj.date_fin,obj.journal])
            ct=0
            for row in cr.dictfetchall():
                partner = self.env['res.partner'].browse(row["partner_id"])
                libelle = partner.name

                invoice_id = row["invoice_id"]
                invoice = self.env['account.move'].browse(invoice_id)
                invoice.is_export_compta_id = obj.id
                num_compte = row["num_compte"]
                if num_compte[:3] in ['411']:
                    if row["is_compte_auxiliaire_client"]:
                        num_compte = row["is_compte_auxiliaire_client"]
                if num_compte[:3] in ['401']:
                    if row["is_compte_auxiliaire"]:
                        num_compte = row["is_compte_auxiliaire"]
                ct=ct+1
                num_piece   = invoice.ref
                num_facture = invoice.name
                if obj.journal=="VE":
                    num_piece = num_facture
                vals={
                    'export_compta_id': obj.id,
                    'ligne'           : ct,
                    'code_journal'    : row["code_journal"],
                    'date'            : row["date"],
                    'num_piece'       : num_piece,
                    'num_facture'     : num_facture,
                    'num_compte'      : num_compte,
                    'libelle'         : libelle,
                    'debit'           : row["debit"],
                    'credit'          : row["credit"],
                    'partner_id'      : row["partner_id"],
                    'invoice_id'      : row["invoice_id"],
                }
                self.env['is.export.compta.ligne'].create(vals)


    def generer_fichier_action(self):
        cr=self._cr
        for obj in self:
            name='export-compta.csv'
            model='is.export.compta'
            attachments = self.env['ir.attachment'].search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
            attachments.unlink()
            dest     = '/tmp/'+name
            f = codecs.open(dest,'wb',encoding='utf-8')
            f.write("code_journal;date;num_piece;num_facture;num_compte;libelle;debit;credit\r\n")
            for row in obj.ligne_ids:
                f.write(row.code_journal+';')
                f.write(row.date.strftime('%d%m%Y')+';')
                f.write((row.num_piece or '')+';')
                f.write((row.num_facture or '')+';')
                f.write(row.num_compte+';')
                f.write(row.libelle+';')
                f.write(str(row.debit).replace('.',',')+';')
                f.write(str(row.credit).replace('.',','))
                f.write('\r\n')
            f.close()
            r = open(dest,'rb').read()
            r=base64.b64encode(r)
            vals = {
                'name':        name,
                'type':        'binary',
                'res_model':   model,
                'res_id':      obj.id,
                'datas':       r,
            }
            attachment = self.env['ir.attachment'].create(vals)
            obj.file_ids=[(6,0,[attachment.id])]


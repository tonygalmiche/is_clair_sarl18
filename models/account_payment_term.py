# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import date_utils
from dateutil.relativedelta import relativedelta
import calendar


class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    delay_type = fields.Selection(selection_add=[
        ('day_after_invoice_date', 'jours après la date de facturation le'),
    ], ondelete={
        'day_after_invoice_date': 'set default'
    })

    @api.depends('delay_type')
    def _compute_display_days_next_month(self):
        """Override to show days_next_month for our custom delay type"""
        super()._compute_display_days_next_month()
        for record in self:
            if record.delay_type == 'day_after_invoice_date':
                record.display_days_next_month = True

    def _get_due_date(self, date_ref):
        """Override to add custom logic for new delay types"""
        self.ensure_one()
        due_date = fields.Date.from_string(date_ref) or fields.Date.today()
        
        if self.delay_type == 'day_after_invoice_date':
            # Ajouter nb_days à la date de facture
            intermediate_date = due_date + relativedelta(days=self.nb_days)
            
            # Utiliser days_next_month pour le jour du mois
            try:
                target_day = int(self.days_next_month or 1)
            except (ValueError, TypeError):
                target_day = 1
            
            # Si target_day = 31, aller à la fin du mois
            if target_day >= 31:
                return date_utils.end_of(intermediate_date, 'month')
            
            # Sinon, essayer d'aller au jour demandé
            if target_day <= 0:
                target_day = 1
            
            # Obtenir le dernier jour du mois de intermediate_date
            last_day_of_month = calendar.monthrange(intermediate_date.year, intermediate_date.month)[1]
            
            # Si le jour demandé dépasse le dernier jour du mois, prendre le dernier jour
            actual_day = min(target_day, last_day_of_month)
            
            return intermediate_date.replace(day=actual_day)
        else:
            return super()._get_due_date(date_ref)
from odoo import fields, models  

MY_VIEW = ("planning_chantier", "Planning chantier")


class IrUIView(models.Model):
    _inherit = "ir.ui.view"




    type = fields.Selection(selection_add=[MY_VIEW])




    def _is_qweb_based_view(self, view_type):
        return view_type == MY_VIEW[0] or super()._is_qweb_based_view(view_type)

    def _get_view_info(self):
        return {"planning_chantier": {"icon": "fa fa-tasks"}} | super()._get_view_info()









# from odoo import fields, models   

# class View(models.Model):
#     _inherit = "ir.ui.view"

#     type = fields.Selection(selection_add=[
#         ("planning_chantier", "Planning chantier"),
#     ])


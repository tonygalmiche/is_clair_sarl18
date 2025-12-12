-- Script SQL pour corriger les droits d'accès des pièces jointes is_import_excel_ids
-- Corriger toutes les pièces jointes liées à des commandes via la relation Many2many

UPDATE ir_attachment 
SET res_id = rel.order_id,
    res_field = 'is_import_excel_ids'
FROM sale_order_is_import_excel_ids_rel rel
WHERE ir_attachment.id = rel.attachment_id
  AND ir_attachment.res_model = 'sale.order'
  AND (ir_attachment.res_id = 0 OR ir_attachment.res_id != rel.order_id OR ir_attachment.res_field IS NULL);

-- Vérifier les corrections
SELECT 
    att.id as attachment_id,
    att.name,
    att.res_id,
    att.res_model,
    att.res_field,
    rel.order_id
FROM ir_attachment att
JOIN sale_order_is_import_excel_ids_rel rel ON att.id = rel.attachment_id
WHERE att.res_model = 'sale.order'
ORDER BY att.id;

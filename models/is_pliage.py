# -*- coding: utf-8 -*-
from odoo import models, fields, api
from markupsafe import Markup
import math


class IsPliage(models.Model):
    _name = 'is.pliage'
    _description = 'Pliage'
    _order = 'name'

    name = fields.Char(string='Nom du pliage', required=True)
    ligne_ids = fields.One2many('is.pliage.ligne', 'pliage_id', string='Lignes de pliage', copy=True)
    show_legend = fields.Boolean(string='Afficher la légende', default=True)
    show_lengths = fields.Boolean(string='Afficher les longueurs', default=True)
    show_angles = fields.Boolean(string='Afficher les angles', default=True)
    show_numbers = fields.Boolean(string='Afficher les numéros', default=True)
    text_size = fields.Selection([
        ('small', 'Petit'),
        ('medium', 'Moyen'),
        ('large', 'Grand'),
    ], string='Taille du texte', default='medium')
    graph_size = fields.Selection([
        ('300', '300 px'),
        ('400', '400 px'),
        ('500', '500 px'),
        ('600', '600 px'),
        ('700', '700 px'),
        ('800', '800 px'),
        ('1000', '1000 px'),
    ], string='Taille du graphique', default='700')
    position_laquage = fields.Selection([
        ('none', 'Aucune'),
        ('top_left', 'En haut à gauche'),
        ('top_right', 'En haut à droite'),
        ('bottom_left', 'En bas à gauche'),
        ('bottom_right', 'En bas à droite'),
    ], string='Position du laquage', default='none')
    svg_preview = fields.Html(string='Aperçu SVG', compute='_compute_svg_preview', sanitize=False)

    @api.depends('ligne_ids', 'ligne_ids.angle', 'ligne_ids.longueur', 'ligne_ids.sequence', 'show_legend', 'show_lengths', 'show_angles', 'show_numbers', 'text_size', 'graph_size', 'position_laquage')
    def _compute_svg_preview(self):
        for record in self:
            record.svg_preview = record._generate_svg()

    def _compute_svg_data(self):
        """Calcule les données communes pour générer le SVG"""
        lignes = self.ligne_ids.sorted('sequence')
        if not lignes:
            return None

        # Calculer les points du tracé
        points = [(0, 0)]
        current_angle = 0  # Angle en degrés (0 = vers la droite)
        angles_list = []  # Liste des angles cumulés pour chaque segment
        
        for ligne in lignes:
            current_angle += ligne.angle
            angles_list.append({'angle': ligne.angle, 'longueur': ligne.longueur, 'cumul': current_angle})
            angle_rad = math.radians(current_angle)
            last_x, last_y = points[-1]
            new_x = last_x + ligne.longueur * math.cos(angle_rad)
            new_y = last_y + ligne.longueur * math.sin(angle_rad)
            points.append((new_x, new_y))

        if len(points) < 2:
            return None

        # Calculer les bornes pour le viewBox
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        # Taille du texte selon l'option
        text_sizes = {'small': 8, 'medium': 10, 'large': 14}
        font_size = text_sizes.get(self.text_size, 10)
        angle_font_size = font_size - 1

        # Ajouter une marge plus grande pour les annotations
        margin = 40
        content_width = max_x - min_x + 2 * margin
        content_height = max_y - min_y + 2 * margin

        # Éviter une taille nulle
        if content_width < 100:
            content_width = 100
        if content_height < 100:
            content_height = 100

        # Rendre le viewBox carré (prendre la plus grande dimension)
        size = max(content_width, content_height)
        width = size
        height = size
        
        # Centrer le contenu dans le carré
        offset_x = (size - (max_x - min_x + 2 * margin)) / 2
        offset_y = (size - (max_y - min_y + 2 * margin)) / 2

        # Construire le path SVG
        path_d = f"M {points[0][0] - min_x + margin + offset_x} {points[0][1] - min_y + margin + offset_y}"
        for i in range(1, len(points)):
            path_d += f" L {points[i][0] - min_x + margin + offset_x} {points[i][1] - min_y + margin + offset_y}"

        # Créer les cercles pour les points
        circles = ""
        for i, (x, y) in enumerate(points):
            cx = x - min_x + margin + offset_x
            cy = y - min_y + margin + offset_y
            color = "#4CAF50" if i == 0 else ("#F44336" if i == len(points) - 1 else "#2196F3")
            circles += f'<circle cx="{cx}" cy="{cy}" r="4" fill="{color}"/>'

        # Créer les annotations de longueur au milieu de chaque segment
        length_annotations = ""
        if self.show_lengths:
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                # Point milieu
                mid_x = (x1 + x2) / 2 - min_x + margin + offset_x
                mid_y = (y1 + y2) / 2 - min_y + margin + offset_y
                longueur = angles_list[i]['longueur']
                
                # Décalage perpendiculaire pour ne pas superposer le texte sur la ligne
                dx = x2 - x1
                dy = y2 - y1
                length = math.sqrt(dx*dx + dy*dy)
                perp_x = 0
                perp_y = 0
                if length > 0:
                    # Calculer l'angle de la ligne par rapport à l'horizontale
                    line_angle = math.degrees(math.atan2(dy, dx))
                    
                    # Si la ligne est quasi-verticale (+/- 30° de la verticale, donc entre 60° et 120° ou -60° et -120°)
                    # On place le texte à droite de la ligne
                    is_vertical = (60 <= abs(line_angle) <= 120)
                    
                    if is_vertical:
                        # Placer le texte à droite (direction positive en X) avec un petit décalage
                        perp_x = 2
                        perp_y = 0
                    else:
                        # Vecteur perpendiculaire normalisé (décalage de 6 pixels)
                        perp_x = -dy / length * 6
                        perp_y = dx / length * 6
                    
                    mid_x += perp_x
                    mid_y += perp_y
                
                # Déterminer l'alignement du texte selon la direction perpendiculaire
                # Si le texte est à gauche de la ligne (perp_x < 0), aligner à droite (text-anchor: end)
                # Si le texte est à droite de la ligne (perp_x > 0), aligner à gauche (text-anchor: start)
                if perp_x < -0.1:
                    text_anchor = "end"
                elif perp_x > 0.1:
                    text_anchor = "start"
                else:
                    text_anchor = "middle"
                
                # Ajouter un fond gris derrière le texte
                length_annotations += f'<text x="{mid_x}" y="{mid_y}" dy="0.35em" font-family="Arial, sans-serif" font-size="{font_size}" fill="#333" text-anchor="{text_anchor}" style="paint-order: stroke fill;"><tspan style="stroke:#f5f5f5;stroke-width:4px;">{longueur}</tspan></text>'
                length_annotations += f'<text x="{mid_x}" y="{mid_y}" dy="0.35em" font-family="Arial, sans-serif" font-size="{font_size}" fill="#333" text-anchor="{text_anchor}">{longueur}</text>'

        # Créer les annotations d'angle sur chaque point de départ de segment
        angle_annotations = ""
        if self.show_angles:
            for i in range(len(points) - 1):
                angle = angles_list[i]['angle']
                
                # Ne pas afficher si l'angle est 0
                if angle != 0:
                    x, y = points[i]
                    cx = x - min_x + margin + offset_x
                    cy = y - min_y + margin + offset_y
                    
                    # Calculer la direction du segment actuel
                    x_next, y_next = points[i + 1]
                    dx_current = x_next - x
                    dy_current = y_next - y
                    
                    # Calculer la direction du segment précédent (ou direction initiale pour le premier)
                    if i == 0:
                        # Premier segment : l'angle précédent est 0° (horizontal vers la droite)
                        dx_prev = 1
                        dy_prev = 0
                    else:
                        x_prev, y_prev = points[i - 1]
                        dx_prev = x - x_prev
                        dy_prev = y - y_prev
                    
                    # Normaliser les vecteurs
                    len_prev = math.sqrt(dx_prev**2 + dy_prev**2)
                    len_current = math.sqrt(dx_current**2 + dy_current**2)
                    
                    if len_prev > 0 and len_current > 0:
                        dx_prev /= len_prev
                        dy_prev /= len_prev
                        dx_current /= len_current
                        dy_current /= len_current
                        
                        # Pour la bissectrice intérieure :
                        # - On inverse la direction du segment précédent (direction entrante)
                        # - On garde la direction du segment actuel (direction sortante)
                        # - La bissectrice est la moyenne de ces deux directions
                        bisect_x = (-dx_prev) + dx_current
                        bisect_y = (-dy_prev) + dy_current
                        bisect_len = math.sqrt(bisect_x**2 + bisect_y**2)
                        
                        if bisect_len > 0:
                            bisect_x /= bisect_len
                            bisect_y /= bisect_len
                        else:
                            # Les segments sont alignés (angle 180°), prendre la perpendiculaire
                            bisect_x = -dy_current
                            bisect_y = dx_current
                        
                        # Placer le centre du texte le long de la bissectrice
                        # Décalage suffisant pour que le texte soit bien visible à l'intérieur de l'angle
                        offset = 20
                        text_x = cx + bisect_x * offset
                        text_y = cy + bisect_y * offset
                        
                        # Dessiner la bissectrice du centre du texte vers l'angle
                        angle_annotations += f'<line x1="{text_x}" y1="{text_y}" x2="{cx}" y2="{cy}" stroke="#ff0000" stroke-width="1" stroke-dasharray="3,3"/>'
                        
                        # Ajouter un fond gris derrière le texte
                        angle_annotations += f'<text x="{text_x}" y="{text_y}" dy="0.35em" font-family="Arial, sans-serif" font-size="{angle_font_size}" font-weight="bold" fill="#333" text-anchor="middle"><tspan style="stroke:#f5f5f5;stroke-width:4px;">{angle}°</tspan></text>'
                        angle_annotations += f'<text x="{text_x}" y="{text_y}" dy="0.35em" font-family="Arial, sans-serif" font-size="{angle_font_size}" font-weight="bold" fill="#333" text-anchor="middle">{angle}°</text>'

        annotations = length_annotations + angle_annotations

        # Créer les annotations de numéros de pliage (à l'opposé de l'angle)
        number_annotations = ""
        if self.show_numbers:
            for i in range(len(points) - 1):
                x, y = points[i]
                cx = x - min_x + margin + offset_x
                cy = y - min_y + margin + offset_y
                num = i + 1  # Numéro de 1 à X
                
                # Calculer la direction du segment actuel
                x_next, y_next = points[i + 1]
                dx_current = x_next - x
                dy_current = y_next - y
                
                # Calculer la direction du segment précédent (ou direction initiale pour le premier)
                if i == 0:
                    dx_prev = 1
                    dy_prev = 0
                else:
                    x_prev, y_prev = points[i - 1]
                    dx_prev = x - x_prev
                    dy_prev = y - y_prev
                
                # Normaliser les vecteurs
                len_prev = math.sqrt(dx_prev**2 + dy_prev**2)
                len_current = math.sqrt(dx_current**2 + dy_current**2)
                
                if len_prev > 0 and len_current > 0:
                    dx_prev /= len_prev
                    dy_prev /= len_prev
                    dx_current /= len_current
                    dy_current /= len_current
                    
                    # Pour la direction opposée à la bissectrice intérieure :
                    # On inverse le calcul de la bissectrice
                    bisect_x = dx_prev + (-dx_current)
                    bisect_y = dy_prev + (-dy_current)
                    bisect_len = math.sqrt(bisect_x**2 + bisect_y**2)
                    
                    if bisect_len > 0:
                        bisect_x /= bisect_len
                        bisect_y /= bisect_len
                    else:
                        # Les segments sont alignés, prendre la perpendiculaire opposée
                        bisect_x = dy_current
                        bisect_y = -dx_current
                    
                    # Placer le numéro à l'opposé de l'angle
                    offset_num = 18
                    text_x = cx + bisect_x * offset_num
                    text_y = cy + bisect_y * offset_num
                    
                    # Taille du numéro (plus petit que les autres textes)
                    num_font_size = max(font_size - 3, 6)
                    circle_radius = num_font_size * 0.8
                    
                    # Ajouter un cercle fin autour du numéro
                    number_annotations += f'<circle cx="{text_x}" cy="{text_y}" r="{circle_radius}" fill="#f5f5f5" stroke="#555" stroke-width="0.5"/>'
                    number_annotations += f'<text x="{text_x}" y="{text_y}" dy="0.35em" font-family="Arial, sans-serif" font-size="{num_font_size}" font-weight="bold" fill="#555" text-anchor="middle">{num}</text>'

        annotations = annotations + number_annotations

        # Créer la flèche du laquage si une position est sélectionnée
        corner_arrows = ""
        if self.position_laquage and self.position_laquage != 'none':
            diagonal = math.sqrt(width**2 + height**2)
            arrow_length = diagonal / 8  # Divisé par 2 (avant c'était /4)
            center_x = width / 2
            center_y = height / 2
            
            # Sélectionner le coin selon la position choisie
            corners = {
                'top_left': (0, 0),
                'top_right': (width, 0),
                'bottom_left': (0, height),
                'bottom_right': (width, height),
            }
            
            corner_x, corner_y = corners[self.position_laquage]
            
            # Direction du coin vers le centre
            dx = center_x - corner_x
            dy = center_y - corner_y
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 0:
                dx /= dist
                dy /= dist
                # Point de fin de la flèche
                end_x = corner_x + dx * arrow_length
                end_y = corner_y + dy * arrow_length
                
                # Pointe de flèche
                arrow_size = 6
                # Vecteur perpendiculaire
                perp_x = -dy
                perp_y = dx
                # Points de la pointe de flèche
                tip1_x = end_x - dx * arrow_size + perp_x * arrow_size / 2
                tip1_y = end_y - dy * arrow_size + perp_y * arrow_size / 2
                tip2_x = end_x - dx * arrow_size - perp_x * arrow_size / 2
                tip2_y = end_y - dy * arrow_size - perp_y * arrow_size / 2
                
                corner_arrows = f'<line x1="{corner_x}" y1="{corner_y}" x2="{end_x}" y2="{end_y}" stroke="#999" stroke-width="1"/>'
                corner_arrows += f'<polygon points="{end_x},{end_y} {tip1_x},{tip1_y} {tip2_x},{tip2_y}" fill="#999"/>'

        return {
            'width': width,
            'height': height,
            'path_d': path_d,
            'circles': circles,
            'annotations': annotations,
            'corner_arrows': corner_arrows,
            'points': points,
        }

    def _get_legend_html(self):
        """Retourne le HTML de la légende"""
        if not self.show_legend:
            return ''
        arrow_legend = ''
        if self.position_laquage and self.position_laquage != 'none':
            arrow_legend = '<span style="color:#999;margin-left:10px;">➜</span> Emplacement du laquage'
        return f'''
            <div style="font-size:11px;color:#666;margin-top:8px;">
                <span style="color:#4CAF50;">●</span> Début
                <span style="color:#2196F3;margin-left:10px;">●</span> Intermédiaire
                <span style="color:#F44336;margin-left:10px;">●</span> Fin
                {arrow_legend}
            </div>
        '''



    def _generate_svg(self):
        """Génère le SVG pour l'affichage dans le formulaire"""
        data = self._compute_svg_data()
        if not data:
            return '<div style="text-align:center;color:#888;padding:20px;">Aucune ligne de pliage</div>'

        legend = self._get_legend_html()
        
        # Taille du SVG selon l'option choisie
        svg_size = int(self.graph_size or '400')
        
        svg = f'''
        <div style="text-align:center;display:inline-block;">
            <svg width="{svg_size}" height="{svg_size}" viewBox="0 0 {data['width']} {data['height']}" preserveAspectRatio="xMidYMid meet" style="background:#f5f5f5;border:1px solid #999;">
                {data['corner_arrows']}
                <path d="{data['path_d']}" stroke="#333" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                {data['circles']}
                {data['annotations']}
            </svg>
            {legend}
        </div>
        '''
        return svg

    def _generate_svg_for_report(self):
        """Génère le SVG pour le rapport PDF"""
        data = self._compute_svg_data()
        if not data:
            return Markup('<p style="text-align:center;color:#888;">Aucune ligne de pliage</p>')

        legend = self._get_legend_html()
        svg = f'''<div style="text-align:center;">
            <svg xmlns="http://www.w3.org/2000/svg" width="420" height="420" viewBox="0 0 {data['width']} {data['height']}" preserveAspectRatio="xMidYMid meet" style="border:1px solid #999;">
                {data['corner_arrows']}
                <path d="{data['path_d']}" stroke="#333" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                {data['circles']}
                {data['annotations']}
            </svg>
            {legend}
        </div>'''
        return Markup(svg)


class IsPliageLigne(models.Model):
    _name = 'is.pliage.ligne'
    _description = 'Ligne de pliage'
    _order = 'sequence, id'

    pliage_id = fields.Many2one('is.pliage', string='Pliage', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Séquence', default=10)
    numero = fields.Integer(string='N°', compute='_compute_numero', store=False)
    angle = fields.Integer(string='Angle')
    longueur = fields.Integer(string='Longueur')

    @api.depends('pliage_id.ligne_ids', 'pliage_id.ligne_ids.sequence')
    def _compute_numero(self):
        for record in self:
            if record.pliage_id:
                lignes = record.pliage_id.ligne_ids.sorted('sequence')
                for idx, ligne in enumerate(lignes, 1):
                    if ligne.id == record.id:
                        record.numero = idx
                        break
                else:
                    record.numero = 0
            else:
                record.numero = 0

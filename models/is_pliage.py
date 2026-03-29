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
    show_cut_lines = fields.Boolean(string='Couper les lignes', help='Couper les lignes disproportionnées (5 fois la longueur mini)', default=True)
    text_size = fields.Selection([
        ('auto', 'Automatique'),
        ('small', 'Petit'),
        ('medium', 'Moyen'),
        ('large', 'Grand'),
    ], string='Taille du texte', default='auto')
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

    @api.depends('ligne_ids', 'ligne_ids.angle', 'ligne_ids.longueur', 'ligne_ids.sequence', 'show_legend', 'show_lengths', 'show_angles', 'show_numbers', 'show_cut_lines', 'text_size', 'graph_size', 'position_laquage')
    def _compute_svg_preview(self):
        for record in self:
            record.svg_preview = record._generate_svg()

    @api.onchange('show_legend', 'show_lengths', 'show_angles', 'show_numbers', 'show_cut_lines', 'text_size', 'graph_size', 'position_laquage')
    def _onchange_svg_options(self):
        self.svg_preview = self._generate_svg()

    def _compute_svg_data(self):
        """Calcule les données communes pour générer le SVG"""
        lignes = self.ligne_ids.sorted('sequence')
        if not lignes:
            return None

        # Calculer les longueurs d'affichage (raccourcir si une ligne est trop longue)
        longueurs = [l.longueur for l in lignes]
        display_longueurs = list(longueurs)
        shortened_segments = set()
        if self.show_cut_lines and len(longueurs) >= 2:
            min_l = min(l for l in longueurs if l > 0)
            display_max = min_l * 5
            for idx, l in enumerate(longueurs):
                if l > display_max:
                    display_longueurs[idx] = display_max
                    shortened_segments.add(idx)

        # Calculer les points du tracé
        points = [(0, 0)]
        current_angle = 0  # Angle en degrés (0 = vers la droite)
        angles_list = []  # Liste des angles cumulés pour chaque segment
        
        for i, ligne in enumerate(lignes):
            if i == 0:
                current_angle = ligne.angle  # Premier segment : direction initiale
            else:
                current_angle += (180 - ligne.angle)  # Angle entre segments → déviation
            angles_list.append({'angle': ligne.angle, 'longueur': ligne.longueur, 'cumul': current_angle})
            angle_rad = math.radians(current_angle)
            last_x, last_y = points[-1]
            new_x = last_x + display_longueurs[i] * math.cos(angle_rad)
            new_y = last_y + display_longueurs[i] * math.sin(angle_rad)
            points.append((new_x, new_y))

        if len(points) < 2:
            return None

        # Calculer les bornes pour le viewBox
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)

        # Taille du texte selon l'option
        min_longueur = min(l.longueur for l in lignes if l.longueur > 0) if lignes else 100
        if self.text_size == 'auto':
            font_size = max(4, min(14, min_longueur * 0.12))
        else:
            text_sizes = {'small': 8, 'medium': 10, 'large': 14}
            font_size = text_sizes.get(self.text_size, 10)
        angle_font_size = font_size

        # Epaisseur de ligne proportionnelle à la plus petite longueur
        stroke_w = max(0.5, min(3, min_longueur * 0.04))

        # Marge proportionnelle pour les annotations
        extent = max(max_x - min_x, max_y - min_y, 1)
        margin = max(font_size * 3, extent * 0.08)
        content_width = max_x - min_x + 2 * margin
        content_height = max_y - min_y + 2 * margin

        # Rendre le viewBox carré
        size = max(content_width, content_height)
        if size < 50:
            size = 50
        width = size
        height = size

        # Centrer le contenu dans le carré
        offset_x = (size - (max_x - min_x + 2 * margin)) / 2
        offset_y = (size - (max_y - min_y + 2 * margin)) / 2

        # Construire le path SVG
        path_d = f"M {points[0][0] - min_x + margin + offset_x} {points[0][1] - min_y + margin + offset_y}"
        for i in range(1, len(points)):
            path_d += f" L {points[i][0] - min_x + margin + offset_x} {points[i][1] - min_y + margin + offset_y}"

        # Marques de coupure sur les segments raccourcis (2 lignes parallèles)
        break_marks = ""
        for seg_idx in shortened_segments:
            x1s = points[seg_idx][0] - min_x + margin + offset_x
            y1s = points[seg_idx][1] - min_y + margin + offset_y
            x2s = points[seg_idx + 1][0] - min_x + margin + offset_x
            y2s = points[seg_idx + 1][1] - min_y + margin + offset_y
            # Milieu du segment
            mx = (x1s + x2s) / 2
            my = (y1s + y2s) / 2
            # Direction du segment
            sdx = x2s - x1s
            sdy = y2s - y1s
            sl = math.sqrt(sdx**2 + sdy**2)
            if sl > 0:
                sdx /= sl; sdy /= sl
                # Perpendiculaire
                px = -sdy
                py = sdx
                gap = sl * 0.01  # Espacement entre les 2 lignes
                mark_len = sl * 0.03  # Longueur des marques
                for sign in [-1, 1]:
                    cx = mx + sdx * gap * sign
                    cy = my + sdy * gap * sign
                    bx1 = cx + px * mark_len
                    by1 = cy + py * mark_len
                    bx2 = cx - px * mark_len
                    by2 = cy - py * mark_len
                    break_marks += f'<line x1="{bx1}" y1="{by1}" x2="{bx2}" y2="{by2}" stroke="#333" stroke-width="0.8"/>'

        # Créer les marqueurs aux points (numéros ou simples points)
        num_font_size = font_size * 0.7
        circle_radius = num_font_size * 0.8
        circles = ""
        for i, (x, y) in enumerate(points):
            cx = x - min_x + margin + offset_x
            cy = y - min_y + margin + offset_y
            if self.show_numbers:
                num = i + 1
                circles += f'<circle cx="{cx}" cy="{cy}" r="{circle_radius}" fill="#333"/>'
                circles += f'<text x="{cx}" y="{cy}" dy="0.35em" font-family="Arial, sans-serif" font-size="{num_font_size}" font-weight="bold" fill="#fff" text-anchor="middle">{num}</text>'
            else:
                circles += f'<circle cx="{cx}" cy="{cy}" r="1.8" fill="#333"/>'

        # Fonction pour calculer la bissectrice intérieure en un point
        def compute_bisector(i, invert=False):
            x, y = points[i]
            x_next, y_next = points[i + 1]
            dx_cur = x_next - x
            dy_cur = y_next - y
            if i == 0:
                dx_prv, dy_prv = 1, 0
            else:
                x_prv, y_prv = points[i - 1]
                dx_prv = x - x_prv
                dy_prv = y - y_prv
            lp = math.sqrt(dx_prv ** 2 + dy_prv ** 2)
            lc = math.sqrt(dx_cur ** 2 + dy_cur ** 2)
            if lp == 0 or lc == 0:
                return None
            dx_prv /= lp; dy_prv /= lp
            dx_cur /= lc; dy_cur /= lc
            if invert:
                bx = dx_prv + (-dx_cur)
                by = dy_prv + (-dy_cur)
            else:
                bx = (-dx_prv) + dx_cur
                by = (-dy_prv) + dy_cur
            bl = math.sqrt(bx ** 2 + by ** 2)
            if bl > 0:
                bx /= bl; by /= bl
            else:
                if invert:
                    bx = dy_cur; by = -dx_cur
                else:
                    bx = -dy_cur; by = dx_cur
            return (bx, by)

        # Convertir un point brut en coordonnées SVG
        def to_svg(x, y):
            return (x - min_x + margin + offset_x, y - min_y + margin + offset_y)

        # 1. Placer les annotations d'angle et collecter leurs centres
        angle_annotations = ""
        angle_centers = []  # centres des textes d'angle pour éviter les collisions
        if self.show_angles:
            for i in range(len(points) - 1):
                angle = angles_list[i]['angle']
                if angle == 0:
                    continue
                bisect = compute_bisector(i)
                if not bisect:
                    continue
                bx, by = bisect
                cx, cy = to_svg(*points[i])
                # Arc de cercle
                if i == 0:
                    dx1, dy1 = -1, 0
                else:
                    dx1 = points[i-1][0] - points[i][0]
                    dy1 = points[i-1][1] - points[i][1]
                l1 = math.sqrt(dx1**2 + dy1**2)
                if l1 > 0:
                    dx1 /= l1; dy1 /= l1
                dx2 = points[i+1][0] - points[i][0]
                dy2 = points[i+1][1] - points[i][1]
                l2 = math.sqrt(dx2**2 + dy2**2)
                if l2 > 0:
                    dx2 /= l2; dy2 /= l2
                arc_r = font_size * 1.5
                ax1 = cx + dx1 * arc_r
                ay1 = cy + dy1 * arc_r
                ax2 = cx + dx2 * arc_r
                ay2 = cy + dy2 * arc_r
                cross = dx1 * dy2 - dy1 * dx2
                sweep = 1 if cross > 0 else 0
                angle_annotations += f'<path d="M {ax1} {ay1} A {arc_r} {arc_r} 0 0 {sweep} {ax2} {ay2}" stroke="#ff0000" stroke-width="0.4" stroke-dasharray="2,1" fill="none"/>'
                # Texte après l'arc
                text_off = arc_r + angle_font_size * 0.8
                tx = cx + bx * text_off
                ty = cy + by * text_off
                angle_centers.append((tx, ty))
                angle_annotations += f'<text x="{tx}" y="{ty}" dy="0.35em" font-family="Arial, sans-serif" font-size="{angle_font_size}" font-weight="bold" fill="#ff0000" text-anchor="middle">{abs(angle)}°</text>'

        # 2. Placer les longueurs : choisir le côté le plus éloigné des angles et autres longueurs
        length_annotations = ""
        length_centers = []  # centres des textes de longueur déjà placés
        if self.show_lengths:
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                longueur = angles_list[i]['longueur']
                dx = x2 - x1
                dy = y2 - y1
                seg_len = math.sqrt(dx * dx + dy * dy)
                if seg_len == 0:
                    continue
                nx = -dy / seg_len
                ny = dx / seg_len
                is_shortened = i in shortened_segments
                off = font_size * 2.0 if is_shortened else font_size * 1.3
                mid_x, mid_y = to_svg((x1 + x2) / 2, (y1 + y2) / 2)
                # Calculer les 2 positions candidates (côté +1 et côté -1)
                pos1 = (mid_x + nx * off, mid_y + ny * off)
                pos2 = (mid_x - nx * off, mid_y - ny * off)
                # Distance minimale aux angles et longueurs déjà placées
                obstacles = angle_centers + length_centers
                def min_dist(pos):
                    if not obstacles:
                        return float('inf')
                    return min(math.sqrt((pos[0]-ox)**2 + (pos[1]-oy)**2) for ox, oy in obstacles)
                # Choisir le côté le plus éloigné des obstacles
                d1 = min_dist(pos1)
                d2 = min_dist(pos2)
                tx, ty = pos1 if d1 >= d2 else pos2
                side = 1 if d1 >= d2 else -1
                length_centers.append((tx, ty))
                anc = "middle"
                bg_s = font_size * 0.5
                length_annotations += f'<text x="{tx}" y="{ty}" dy="0.35em" font-family="Arial, sans-serif" font-size="{font_size}" fill="#333" text-anchor="{anc}" style="paint-order: stroke fill;"><tspan style="stroke:#f5f5f5;stroke-width:{bg_s}px;">{longueur}</tspan></text>'
                length_annotations += f'<text x="{tx}" y="{ty}" dy="0.35em" font-family="Arial, sans-serif" font-size="{font_size}" fill="#333" text-anchor="{anc}">{longueur}</text>'

        annotations = angle_annotations + length_annotations

        # Créer la flèche du laquage si une position est sélectionnée
        corner_arrows = ""
        if self.position_laquage and self.position_laquage != 'none':
            diagonal = math.sqrt(width**2 + height**2)
            arrow_length = diagonal / 8
            center_x = width / 2
            center_y = height / 2

            # Coin du rectangle (viewBox)
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
                # Point de fin de la flèche (pointe)
                end_x = corner_x + dx * arrow_length
                end_y = corner_y + dy * arrow_length

                # Pointe de flèche
                arrow_size = 6
                perp_x = -dy
                perp_y = dx
                tip1_x = end_x - dx * arrow_size + perp_x * arrow_size / 2
                tip1_y = end_y - dy * arrow_size + perp_y * arrow_size / 2
                tip2_x = end_x - dx * arrow_size - perp_x * arrow_size / 2
                tip2_y = end_y - dy * arrow_size - perp_y * arrow_size / 2

                # La ligne s'arrête à la base de la pointe
                line_end_x = end_x - dx * arrow_size
                line_end_y = end_y - dy * arrow_size

                corner_arrows = f'<line x1="{corner_x}" y1="{corner_y}" x2="{line_end_x}" y2="{line_end_y}" stroke="#999" stroke-width="1"/>'
                corner_arrows += f'<polygon points="{end_x},{end_y} {tip1_x},{tip1_y} {tip2_x},{tip2_y}" fill="#999"/>'

        return {
            'width': width,
            'height': height,
            'path_d': path_d,
            'circles': circles,
            'annotations': annotations,
            'corner_arrows': corner_arrows,
            'break_marks': break_marks,
            'points': points,
            'stroke_w': stroke_w,
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
            <svg width="{svg_size}" height="{svg_size}" viewBox="0 0 {data['width']} {data['height']}" style="background:#f5f5f5;border:1px solid #999;">
                {data['corner_arrows']}
                <path d="{data['path_d']}" stroke="#333" stroke-width="{data['stroke_w']}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                {data['break_marks']}
                {data['annotations']}
                {data['circles']}
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
            <svg xmlns="http://www.w3.org/2000/svg" width="420" height="420" viewBox="0 0 {data['width']} {data['height']}" style="border:1px solid #999;">
                {data['corner_arrows']}
                <path d="{data['path_d']}" stroke="#333" stroke-width="{data['stroke_w']}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                {data['break_marks']}
                {data['annotations']}
                {data['circles']}
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

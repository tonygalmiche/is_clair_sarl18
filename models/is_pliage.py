# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from markupsafe import Markup
import math
import json
import base64
import io
import logging
import re

_logger = logging.getLogger(__name__)


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
    ], string='Taille du graphique', default='500')
    position_laquage = fields.Selection([
        ('none', 'Aucune'),
        ('top_left', 'En haut à gauche'),
        ('top_right', 'En haut à droite'),
        ('bottom_left', 'En bas à gauche'),
        ('bottom_right', 'En bas à droite'),
    ], string='Position du laquage', default='none')
    svg_preview = fields.Html(string='Aperçu SVG', compute='_compute_svg_preview', sanitize=False)
    ia_debug_svg = fields.Html(string='Debug IA', sanitize=False)
    ia_thinking = fields.Text(string='Réflexion IA', readonly=True)
    ia_duree = fields.Float(string='Durée traitement IA (s)', readonly=True, digits=(10, 2))
    dessin_pliage = fields.Image(string='Dessin du pliage', max_width=0, max_height=0)
    dessin_pliage_ia = fields.Image(string='Image envoyée à l\'IA', max_width=0, max_height=0, readonly=True)
    dessin_description = fields.Text(string='Description du dessin', help='Décrivez le dessin pour aider l\'IA, ex: "3 segments en forme de Z" ou "4 segments en escalier"')

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
        longueurs_positives = [l for l in longueurs if l > 0]
        if self.show_cut_lines and len(longueurs) >= 2 and longueurs_positives:
            min_l = min(longueurs_positives)
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
        lignes_positives = [l.longueur for l in lignes if l.longueur > 0]
        min_longueur = min(lignes_positives) if lignes_positives else 100
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
                # Si l'angle est > 180°, afficher l'angle complémentaire et inverser l'arc
                a = abs(angle)
                if a > 180:
                    display_angle = 360 - a
                    sweep = 1 - sweep
                    ax1, ay1, ax2, ay2 = ax2, ay2, ax1, ay1
                else:
                    display_angle = a
                angle_annotations += f'<path d="M {ax1} {ay1} A {arc_r} {arc_r} 0 0 {sweep} {ax2} {ay2}" stroke="#ff0000" stroke-width="0.4" stroke-dasharray="2,1" fill="none"/>'
                # Texte après l'arc
                text_off = arc_r + angle_font_size * 0.8
                tx = cx + bx * text_off
                ty = cy + by * text_off
                angle_centers.append((tx, ty))
                angle_annotations += f'<text x="{tx}" y="{ty}" dy="0.35em" font-family="Arial, sans-serif" font-size="{angle_font_size}" font-weight="bold" fill="#ff0000" text-anchor="middle">{display_angle}°</text>'

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

    def _prepare_image_for_ia(self, img_b64):
        """Prétraite l'image pour l'IA : haut contraste N&B, redimensionnée à 200x200 max, format BMP non compressé."""
        try:
            from PIL import Image, ImageEnhance
        except ImportError:
            _logger.warning("Pillow non installé, envoi de l'image brute")
            return None

        try:
            img_data = base64.b64decode(img_b64)
            img = Image.open(io.BytesIO(img_data))

            # Convertir en niveaux de gris
            img = img.convert('L')

            # Augmenter le contraste
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(3.0)

            # Seuillage pour obtenir du noir et blanc pur
            img = img.point(lambda x: 0 if x < 128 else 255, '1')

            # Reconvertir en RGB
            img = img.convert('RGB')

            # Redimensionner à 200x200 max en conservant les proportions
            img.thumbnail((200, 200), Image.LANCZOS)

            # Sauvegarder en BMP (non compressé) pour l'envoi à l'IA
            buf = io.BytesIO()
            img.save(buf, format='BMP')
            processed_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

            # Sauvegarder aussi en PNG pour l'affichage dans le champ Odoo
            buf_png = io.BytesIO()
            img.save(buf_png, format='PNG')
            self.dessin_pliage_ia = base64.b64encode(buf_png.getvalue()).decode('utf-8')

            return processed_b64
        except Exception as e:
            _logger.warning("Erreur prétraitement image : %s", str(e))
            return None

    def action_create_pliage_ia(self):
        """Envoie l'image du dessin à l'IA pour créer les lignes de pliage."""
        import time
        t_total = time.time()
        self.ensure_one()
        if not self.dessin_pliage:
            raise UserError("Veuillez d'abord ajouter une image dans le champ « Dessin du pliage ».")

        # Préparer l'image en base64
        img_b64 = self.dessin_pliage.decode('utf-8') if isinstance(self.dessin_pliage, bytes) else self.dessin_pliage

        # Prétraiter l'image (haut contraste noir et blanc)
        processed_b64 = self._prepare_image_for_ia(img_b64)
        if processed_b64:
            images_b64 = [(processed_b64, 'image/png')]
            _logger.info("IA pliage - Image prétraitée envoyée (N&B haut contraste)")
        else:
            # Fallback : image originale
            mime_type = 'image/png'
            try:
                raw = base64.b64decode(img_b64[:32])
                if raw[:3] == b'\xff\xd8\xff':
                    mime_type = 'image/jpeg'
            except Exception:
                pass
            images_b64 = [(img_b64, mime_type)]

        # Ajouter la description utilisateur si présente
        description_text = ""
        if self.dessin_description:
            description_text = "\n\nINFORMATION IMPORTANTE DE L'UTILISATEUR : %s\nCette information est FIABLE, utilise-la en priorité pour ton analyse." % self.dessin_description

        prompt = """
Tu es un expert en analyse d'images.
Tu vois une image d'un dessin à main levée montrant une ligne brisée formée de plusieurs segments droits reliés entre eux.%s

TA MISSION : 
- Identifier les segments de la ligne brisée
- Si tu vois 3 segments, tu dois retourner 4 coordonées x et y en pixels pour les 4 points des 3 segments


INSTRUCTIONS :
- Recherche le début de la ligne en haut à gauche
- Repère visuellement TOUS les points des segments y compris le premier et le dernier
- Pour chaque point, donne ses coordonnées (x, y) en pixels
- SYSTÈME DE COORDONNÉES : origine (0,0) en HAUT à GAUCHE, x vers la DROITE, y vers le BAS
- Liste les points dans l'ORDRE du tracé (du début à la fin de la ligne)
- La ligne peux former des U ou des zig zag et donc revenir en arrière au niveaux des coordonées x et y
- Les coordonées x et y doivent toujours partir du point en haut à gauche de l'image
- Plus le point est à droite de l'image, plus x doit être important
- Il est possible que le x du point 3 soit plus petit que le x du point 2

ATTENTION CRITIQUE : La ligne peut revenir en arrière sur l'axe X.
Un point peut avoir un X INFÉRIEUR au point précédent. 
Ne suppose JAMAIS que X augmente toujours. Mesure chaque point RÉELLEMENT.


Réponds UNIQUEMENT en JSON valide :
{
    "points": [
        {"numero":1, "x": 50, "y": 150}, 
        {"numero":2, "x": 600, "y": 150}, 
        {"numero":3, "x": 850, "y": 400}
    ],
    "nb_points": xx,
    "nb_segemnts": yy,
    "largeur": Largeur de l'images en pixels,
    "hauteur: Hauteur de l'image en pixels,
}""" % description_text


        company = self.env.company
        ia_model = company.is_vllm_model # or 'google/gemini-2.5-flash'
        ia_temperature = company.is_vllm_temperature
        ia_max_tokens = company.is_vllm_max_tokens or 8192
        vllm = self.env['is.vllm']
        t0 = time.time()
        result = vllm.vllm_send_prompt(prompt, images_b64=images_b64, model=ia_model, temperature=ia_temperature, max_tokens=ia_max_tokens)
        t_ia = round(time.time() - t0, 2)
        _logger.info("IA pliage - Durée appel IA : %.2f s", t_ia)

        if not result.get('success'):
            raise UserError("Erreur IA : %s" % result.get('error', 'Erreur inconnue'))

        response = result.get('response', '').strip()
        _logger.info("IA pliage - Réponse brute : %s", response)

        # Nettoyer la réponse : supprimer les blocs de "thinking" et le markdown
        clean = response
        # Si un bloc </think> est présent, extraire le thinking et ne garder que ce qui vient après
        think_match = re.search(r'<think(?:ing)?>(.*?)</think(?:ing)?\s*>', clean, re.DOTALL | re.IGNORECASE)
        if think_match:
            self.ia_thinking = think_match.group(1).strip()
            clean = clean[clean.index(think_match.group(0)) + len(think_match.group(0)):]
        else:
            think_end = re.search(r'</think(?:ing)?\s*>', clean, re.IGNORECASE)
            if think_end:
                self.ia_thinking = clean[:think_end.start()].strip()
                clean = clean[think_end.end():]
            else:
                self.ia_thinking = False
        clean = re.sub(r'^.*?(?:Thinking Process|Chain of Thought|Reasoning|Réflexion)\s*:?\s*.*?(?=\{)', '', clean, flags=re.DOTALL | re.IGNORECASE)
        code_block = re.search(r'```(?:json)?\s*(.*?)\s*```', clean, re.DOTALL)
        if code_block:
            clean = code_block.group(1)

        # Chercher le JSON qui contient "points"
        json_match = re.search(r'\{[^{}]*"points"\s*:\s*\[.*?\]\s*\}', clean, re.DOTALL)
        if not json_match:
            # Essayer "segments" pour rétrocompatibilité
            json_match = re.search(r'\{[^{}]*"segments"\s*:\s*\[.*?\]\s*\}', clean, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{[^{}]*\[.*?\][^{}]*\}', clean, re.DOTALL)
        if not json_match:
            raise UserError("L'IA n'a pas retourné un JSON valide.\n\nRéponse :\n%s" % response[:1000])

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise UserError("Erreur de parsing JSON : %s\n\nRéponse :\n%s" % (str(e), response))

        # Convertir les points en segments
        points = data.get('points', [])
        if not points:
            raise UserError("L'IA n'a retourné aucun point.\n\nRéponse :\n%s" % response)
        
        if len(points) < 2:
            raise UserError("L'IA doit retourner au moins 2 points.\n\nRéponse :\n%s" % response)

        _logger.info("IA pliage - %d points détectés : %s", len(points), points)
        
        # Convertir les points en segments pour le traitement
        segments = []
        for i in range(len(points) - 1):
            segments.append({
                'x1': float(points[i].get('x', 0)),
                'y1': float(points[i].get('y', 0)),
                'x2': float(points[i+1].get('x', 0)),
                'y2': float(points[i+1].get('y', 0))
            })
        
        _logger.info("IA pliage - %d segments construits à partir des points", len(segments))
        
        # Générer un SVG de debug pour visualiser les points bruts de l'IA
        debug_svg = self._generate_debug_svg_from_ia_points(points)
        self.ia_debug_svg = Markup(debug_svg)

        # Calculer longueurs et angles à partir des segments
        lignes_data = []
        for idx, seg in enumerate(segments):
            x1 = seg['x1']
            y1 = seg['y1']
            x2 = seg['x2']
            y2 = seg['y2']
            
            # Longueur du segment
            longueur = int(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))
            
            if idx == 0:
                # Premier segment : angle = 0
                angle_pliage = 0
            else:
                # Calculer l'angle entre ce segment et le précédent
                prev_seg = segments[idx - 1]
                
                # Vecteurs directeurs (système image standard : Y vers le bas)
                v1_x = prev_seg['x2'] - prev_seg['x1']
                v1_y = prev_seg['y2'] - prev_seg['y1']
                v2_x = x2 - x1
                v2_y = y2 - y1
                
                # Angles absolus de chaque vecteur (en degrés)
                angle1 = math.degrees(math.atan2(v1_y, v1_x))
                angle2 = math.degrees(math.atan2(v2_y, v2_x))
                
                # Différence d'angle (rotation de v1 vers v2)
                delta = angle2 - angle1
                
                # Normaliser entre 0 et 360
                if delta < 0:
                    delta += 360
                
                # Conversion en angle de pliage physique
                # Formule SVG : current_angle += (180 - angle_pliage)
                # Donc : angle_pliage = 180 - delta, normalisé entre -180 et 180
                angle_pliage = (180 - delta) % 360
                if angle_pliage > 180:
                    angle_pliage -= 360
                
                # Arrondir au multiple de 5
                angle_pliage = int(round(angle_pliage / 5) * 5)
            
            lignes_data.append({'angle': angle_pliage, 'longueur': longueur})

        _logger.info("IA pliage - Lignes converties : %s", lignes_data)

        # Supprimer les lignes existantes
        self.ligne_ids.unlink()

        # Créer les nouvelles lignes
        for idx, ligne in enumerate(lignes_data):
            angle = int(ligne.get('angle', 0))
            longueur = int(ligne.get('longueur', 100))
            self.env['is.pliage.ligne'].create({
                'pliage_id': self.id,
                'sequence': (idx + 1) * 10,
                'angle': angle,
                'longueur': longueur,
            })
        self.ia_duree = round(time.time() - t_total, 2)
        _logger.info("IA pliage - Durée totale : %.2f s", self.ia_duree)
    
    def _generate_debug_svg_from_ia_points(self, points):
        """Génère un SVG de debug affichant uniquement les points bruts retournés par l'IA."""
        if not points or len(points) < 2:
            return "<svg></svg>"
        
        all_x = [float(p.get('x', 0)) for p in points]
        all_y = [float(p.get('y', 0)) for p in points]
        
        min_x = min(all_x)
        max_x = max(all_x)
        min_y = min(all_y)
        max_y = max(all_y)
        
        margin_left = 40
        margin_right = 120  # Marge plus large pour les labels à droite
        margin_top = 40
        margin_bottom = 40
        width = max_x - min_x + margin_left + margin_right
        height = max_y - min_y + margin_top + margin_bottom
        
        svg_lines = []
        svg_lines.append(f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background: white;">')
        
        # Tracer les segments entre points consécutifs
        for i in range(len(points) - 1):
            x1 = float(points[i].get('x', 0)) - min_x + margin_left
            y1 = float(points[i].get('y', 0)) - min_y + margin_top
            x2 = float(points[i+1].get('x', 0)) - min_x + margin_left
            y2 = float(points[i+1].get('y', 0)) - min_y + margin_top
            svg_lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="black" stroke-width="3"/>')
        
        # Afficher chaque point avec son numéro et ses coordonnées
        for i, p in enumerate(points):
            px = float(p.get('x', 0)) - min_x + margin_left
            py = float(p.get('y', 0)) - min_y + margin_top
            cx = int(p.get('x', 0))
            cy = int(p.get('y', 0))
            svg_lines.append(f'<circle cx="{px}" cy="{py}" r="6" fill="blue"/>')
            svg_lines.append(f'<text x="{px+8}" y="{py-8}" font-size="12" fill="blue">P{i+1} ({cx},{cy})</text>')
        
        svg_lines.append('</svg>')
        _logger.info("IA - SVG debug généré")
        return '\n'.join(svg_lines)


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

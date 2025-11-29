/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, markup } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class PliageSvgField extends Component {
    static template = "is_clair_sarl18.PliageSvgField";
    static props = {
        ...standardFieldProps,
    };

    get svgContent() {
        // Utilise le SVG généré par Python (champ svg_preview)
        const htmlContent = this.props.record.data.svg_preview;
        if (htmlContent) {
            return markup(htmlContent);
        }
        return markup(`<div style="text-align:center;color:#888;padding:20px;">Aucune ligne de pliage</div>`);
    }

    get hasLines() {
        const lignesField = this.props.record.data.ligne_ids;
        return lignesField && lignesField.records && lignesField.records.length > 0;
    }

    getSvgOnly() {
        // Extrait le SVG pur du contenu HTML pour le téléchargement
        const htmlContent = this.props.record.data.svg_preview;
        if (!htmlContent) return null;

        // Extraire le SVG du HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlContent, 'text/html');
        const svgElement = doc.querySelector('svg');
        
        if (!svgElement) return null;

        // Ajouter le namespace XML et retourner le SVG complet
        svgElement.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        
        // Ajouter un fond
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('width', '100%');
        rect.setAttribute('height', '100%');
        rect.setAttribute('fill', '#f5f5f5');
        svgElement.insertBefore(rect, svgElement.firstChild);

        return `<?xml version="1.0" encoding="UTF-8"?>\n${svgElement.outerHTML}`;
    }

    onDownload() {
        const svg = this.getSvgOnly();
        if (!svg) return;

        const blob = new Blob([svg], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const name = this.props.record.data.name || 'pliage';
        a.download = `${name}.svg`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    onOpen() {
        const svg = this.getSvgOnly();
        if (!svg) return;

        const blob = new Blob([svg], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
    }
}

export const pliageSvgField = {
    component: PliageSvgField,
    supportedTypes: ["html"],
};

registry.category("fields").add("pliage_svg", pliageSvgField);

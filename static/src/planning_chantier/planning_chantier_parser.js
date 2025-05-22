//TODO : Je suis reparti du type de vue 'activity' "@mail/views/web/activity" qui est le plus simple
import { visitXML } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";

console.log('PlanningChantierParser')

export class PlanningChantierParser {
    parse(xmlDoc, models, modelName) {
        //const jsClass = xmlDoc.getAttribute("js_class");
        const title = xmlDoc.getAttribute("string");
        const fieldNodes = {};
        const templateDocs = {};
        //const fieldNextIds = {};

        //TODO : J'ai commenté cette partie, et je ne sais pas à quoi elle sert
        // visitXML(xmlDoc, (node) => {
        //     if (node.hasAttribute("t-name")) {
        //         templateDocs[node.getAttribute("t-name")] = node;
        //         return;
        //     }

        //     if (node.tagName === "field") {
        //         const fieldInfo = Field.parseFieldNode(
        //             node,
        //             models,
        //             modelName,
        //             "activity",
        //             jsClass
        //         );
        //         if (!(fieldInfo.name in fieldNextIds)) {
        //             fieldNextIds[fieldInfo.name] = 0;
        //         }
        //         const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
        //         fieldNodes[fieldId] = fieldInfo;
        //         node.setAttribute("field_id", fieldId);
        //     }

        //     // Keep track of last update so images can be reloaded when they may have changed.
        //     if (node.tagName === "img") {
        //         const attSrc = node.getAttribute("t-att-src");
        //         if (
        //             attSrc &&
        //             /\bactivity_image\b/.test(attSrc) &&
        //             !Object.values(fieldNodes).some((f) => f.name === "write_date")
        //         ) {
        //             fieldNodes.write_date_0 = { name: "write_date", type: "datetime" };
        //         }
        //     }
        // });
        return {
            fieldNodes,
            templateDocs,
            title,
        };
    }
}

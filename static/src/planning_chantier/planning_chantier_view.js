//TODO : Je suis reparti du type de vue 'activity' "@mail/views/web/activity" qui est le plus simple
import { registry } from "@web/core/registry";
import {PlanningChantierParser} from "./planning_chantier_parser";
import {PlanningChantierController} from "./planning_chantier_controller";
import {PlanningChantierModel} from "./planning_chantier_model";
import {PlanningChantierRenderer} from "./planning_chantier_renderer";


export const PlanningChantierView = {
    type: "planning_chantier",
    searchMenuTypes: ["filter", "favorite"],
    Controller: PlanningChantierController,
    Renderer: PlanningChantierRenderer,
    ArchParser: PlanningChantierParser,
    Model: PlanningChantierModel,
    // limit: 80,

    props: (genericProps, view) => {
        const { arch, relatedModels, resModel } = genericProps;
        const archInfo = new view.ArchParser().parse(arch, relatedModels, resModel);
        return {
            ...genericProps,
            archInfo,
            Model: view.Model,
            Renderer: view.Renderer,
        };
    },
};
registry.category("views").add("planning_chantier", PlanningChantierView);


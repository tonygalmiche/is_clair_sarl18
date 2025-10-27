//TODO : Je suis reparti du type de vue 'activity' "@mail/views/web/activity" qui est le plus simple

//import { MailColumnProgress } from "@mail/core/web/mail_column_progress";
//import { ActivityCell } from "@mail/views/web/activity/activity_cell";
//import { ActivityRecord } from "@mail/views/web/activity/activity_record";

import { Component, useState, onMounted, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


//const { useState, onMounted, onPatched, onWillUnmount } = owl.hooks;


//import { browser } from "@web/core/browser/browser";
//import { CheckBox } from "@web/core/checkbox/checkbox";
//import { Dropdown } from "@web/core/dropdown/dropdown";
//import { DropdownItem } from "@web/core/dropdown/dropdown_item";
//import { _t } from "@web/core/l10n/translation";


console.log('PlanningChantierRenderer')



export class PlanningChantierRenderer extends Component {



    static components = {
        //ActivityCell,
        //ActivityRecord,
        //ColumnProgress: MailColumnProgress,
        //Dropdown,
        //DropdownItem,
        //CheckBox,
    };
    static props = {
        //activityTypes: { type: Object },
        //activityResIds: { type: Array },
        fields: { type: Object },
        resModel: { type: String },
        records: { type: Array },
        archInfo: { type: Object },

        data: { type: Array },
        domain: { type: Array, optional: true },


        // Ajoutez cette ligne :
        onReloadData: { type: Function },

        //groupedActivities: { type: Object },
        //scheduleActivity: { type: Function },
        //onEmptyCell: { type: Function },
        //onSendMailTemplate: { type: Function },
        //openRecord: { type: Function },
    };
    static template = "planning_chantier.PlanningChantierRendererTemplate";

    setup() {
        console.log('PlanningChantierRenderer : setup')

        this.props.test = "toto";

        // Essayer d'utiliser le service ORM au lieu de RPC
        try {
            this.orm = useService("orm");
        } catch (error) {
            console.warn('Service ORM non disponible:', error);
            this.orm = null;
        }


        // this.state = useState({
        //     decale_planning: "",
        //     nb_semaines:"",
        //     dict:{},
        // });

        // Ajoutez cette initialisation du state
        this.state = useState({
            //nb_semaines: 8,
            decale_planning: "",
            //filtre_chantier: "",
            //filtre_equipe: "",
            //filtre_travaux: "",
            //chantier_state: "",
            dict: {},
            //mois: {},
            //semaines: {},
            //state_options: [],
        });

        this.activeFilter = useState({
            progressValue: {
                active: null,
            },
            activityTypeId: null,
        });

        onMounted(() => this.mounted());

        // Surveiller les changements de props (domain des filtres)
        onWillUpdateProps((nextProps) => {
            const newDomain = JSON.stringify(nextProps.domain || []);
            console.log('PlanningChantierRenderer onWillUpdateProps - ancien domain:', this.lastDomain);
            console.log('PlanningChantierRenderer onWillUpdateProps - nouveau domain:', newDomain);
            if (newDomain !== this.lastDomain) {
                this.lastDomain = newDomain;
                console.log('PlanningChantierRenderer onWillUpdateProps - domain a changé, rechargement des données');
                this.GetChantiers();
            }
        });

        // Ajouter le service d'action
        this.actionService = useService("action");
        
        // Surveiller les changements de domaine
        this.lastDomain = JSON.stringify(this.props.domain || []);
    }

    mounted() {
        console.log('PlanningChantierRenderer : mounted')
        
        if (this.orm) {
            this.GetChantiers();
        } else {
            console.error('Service ORM non disponible');
        }
    }



    // _patched() {
    //     console.log('_patched : this.ActivePatched=',this.ActivePatched);
    //     if (this.ActivePatched==true) {
    //         this.ActivePatched=false;
    //         this.GetChantiers();
    //     } else {
    //         this.ActivePatched=true;
    //     }
    //     //this.renderDhtmlxGantt();
    //     //this.GetDocuments();
    // }


    // Click pour colorier une ligne
    TrMouseLeave(ev) {
        const click=ev.target.attributes.click.value;
        if (click!="1"){
            const memstyle = ev.target.attributes.memstyle.value;
            ev.target.style=memstyle;
        }
    }
    TrMouseEnter(ev) {
        const click=ev.target.attributes.click.value;
        if (click!="1"){
            ev.target.style="background-color:#FFFF00;opacity: 0.5;";
        }
    }
    TrClick(ev) {
        var click=ev.target.parentElement.attributes.click;
        if (click!==undefined){
            click.value=-click.value
            if (click.value==1){
                ev.target.parentElement.style="background-color:rgb(204, 255, 204);opacity: 0.5;";
            } else {
                const memstyle = ev.target.parentElement.attributes.memstyle.value;
                ev.target.parentElement.style=memstyle;
            }
            ev.target.parentElement.attributes.click.value=click.value;
        }
    }



    //Alonger la durée du chantier par glissé/déposé
    tdMouseDown(ev) {
        if (this.state.autorise_modif==true){
            //On mémorise le chantier, le jour et la couleur lors du down de la souris
            var chantierid=ev.target.parentElement.attributes.chantierid;
            var jour=ev.target.attributes.jour;
            var color=ev.target.attributes.color;
            if (chantierid!==undefined && jour!==undefined && color!==undefined){
                //chantierid = parseInt(chantierid.value);
                chantierid = chantierid.value;
                jour       = parseInt(jour.value);
                color      = color.value;
                if (this.state.dict[chantierid]!==undefined) {
                    if (this.state.dict[chantierid]["jours"]!==undefined) {
                        if (this.state.dict[chantierid]["jours"][jour]!==undefined) {
                            const cursor = this.state.dict[chantierid]["jours"][jour].cursor;
                            if (cursor=="col-resize" || cursor=="move") {

                                console.log("TEST 4",chantierid,jour,color);


                                this.state.action=cursor;
                                this.state.chantierid=chantierid;
                                this.state.jour=this.state.dict[chantierid].fin;
                                this.state.color=color;
                            }
                        }
                    }
                }
            }
        }
    }
    tdMouseMove(ev) {
        //Redimensionnement d'un chantier (on change la durée)
        if (this.state.action=="col-resize"){
            //if (this.state.chantierid>0){
            if (this.state.chantierid!==undefined){
                const jour=ev.target.attributes.jour;
                if (jour!==undefined){
                    //Si le jour est supérieur au jour mémorisé, il faut allonger la durée
                    if(parseInt(jour.value)>parseInt(this.state.jour)){
                        for (let i = parseInt(this.state.jour); i <= parseInt(jour.value); i++) {
                            this.state.dict[this.state.chantierid]["jours"][i].color=this.state.color;
                            var cursor="move";
                            if (i==jour.value){
                                cursor="col-resize";
                            }
                            this.state.dict[this.state.chantierid]["jours"][i].cursor=cursor;
                            this.state.dict[this.state.chantierid].fin = parseInt(jour.value)+1;
                            const duree = this.state.dict[this.state.chantierid].fin - this.state.dict[this.state.chantierid].debut + 1;
                            this.state.dict[this.state.chantierid].duree = duree
                            this.state.jour = jour.value;
                        }
                    }
                    //Si le jour est inférieur au jour mémorisé, il faut réduire la durée
                    if(parseInt(jour.value)<parseInt(this.state.jour)){
                        this.state.dict[this.state.chantierid]["jours"][parseInt(jour.value)].cursor="col-resize";
                        for (let i = (parseInt(this.state.jour)+1); i > parseInt(jour.value); i--) {
                            this.state.dict[this.state.chantierid]["jours"][i].color="none";
                            this.state.dict[this.state.chantierid]["jours"][i].cursor="default";
                            this.state.dict[this.state.chantierid].fin = parseInt(jour.value)+1;
                            const duree = this.state.dict[this.state.chantierid].fin - this.state.dict[this.state.chantierid].debut + 1;
                            this.state.dict[this.state.chantierid].duree = duree
                            this.state.jour = jour.value;
                        }
                    }
                }
            }
        }

        //Déplacement d'un chantier (on change la date de début)
        if (this.state.action=="move"){
            if (this.state.chantierid!==undefined){
                var jour=ev.target.attributes.jour;
                var chantier = this.state.dict[this.state.chantierid];
                if (jour!==undefined){
                    jour = parseInt(jour.value);
                    //Si le jour est supérieur au jour mémorisé, il faut déplacer à droite
                    if(jour>parseInt(this.state.jour)){
                        for (let i = this.state.jour ; i<jour; i++) {
                            this.state.dict[this.state.chantierid]["jours"][i].color=this.state.color;
                            this.state.dict[this.state.chantierid]["jours"][i].cursor="move";
                            if (this.state.dict[this.state.chantierid]["jours"][i-chantier.duree] !==undefined) {
                                this.state.dict[this.state.chantierid]["jours"][i-chantier.duree].color="none";
                                this.state.dict[this.state.chantierid]["jours"][i-chantier.duree].cursor="default";    
                            }
                        }
                        this.state.debut = jour - chantier.duree;
                    }
                    //Si le jour est inférieur au jour mémorisé, il faut déplacer à gauche
                    if(jour<parseInt(this.state.jour)){
                        for (let i = jour ; i<this.state.jour; i++) {
                            if (this.state.dict[this.state.chantierid]["jours"][i]!==undefined) {
                                this.state.dict[this.state.chantierid]["jours"][i].color=this.state.color;
                                this.state.dict[this.state.chantierid]["jours"][i].cursor="move";    
                            }
                            if (this.state.dict[this.state.chantierid]["jours"][i+chantier.duree]!==undefined) {
                                this.state.dict[this.state.chantierid]["jours"][i+chantier.duree].color="none";
                                this.state.dict[this.state.chantierid]["jours"][i+chantier.duree].cursor="default";
                            }
                        }
                        this.state.debut = jour
                    }
                    this.state.jour = jour;
                }
            }
        }
    }
    tdMouseUp(ev) {
        if (this.state.dict[this.state.chantierid]!==undefined){
            const id = this.state.dict[this.state.chantierid]["id"];
            console.log("id=",id);
            if (this.state.action=="col-resize"){
                if (this.state.chantierid!==undefined){
                    const chantier = this.state.dict[this.state.chantierid];
                    const duree = chantier.duree;
                    if (duree>1) {
                        this.ModifDureeChantier(id,duree);
                    }
                }
            }
            if (this.state.action=="move"){
                this.moveChantier(id, this.state.debut, this.state.decale_planning);
            }
            this.state.chantierid=0;
            this.state.jour=0;
            this.state.color="";
            this.state.action="";
        }
    }

    


    tbodyMouseLeave(ev) {
        this.state.chantierid=0;
        this.state.jour=0;
        this.state.color="";
        this.state.action="";
    }


    // Actions
    MasquerChantierClick(ev){
        const id=ev.target.attributes.id.value;
        delete this.state.dict[id];
    }
    VoirChantierClick(ev) {
        const id=ev.target.attributes.id.value;

        console.log('TEST VoirChantierClick',ev,id);

        this.actionService.doAction({
            name:'Chantier',
            type: 'ir.actions.act_window',
            res_id: parseInt(id),
            res_model: 'is.chantier',
            views: [[false, 'form']],
        });
    }

    CreationAlerteClick(ev) {
        const id=ev.target.attributes.id.value;
        console.log('CreationAlerteClick',id);
        this.actionService.doAction({
            name:'Alerte',
            type: 'ir.actions.act_window',
            res_model: 'is.chantier.alerte',
            views: [[false, 'form']],
            view_mode: 'form',
        //    target: 'new',
            context: {
                //'active_id': id,
                'default_chantier_id': parseInt(id),
            }
        });
    }



    alerteClick(ev) {
        const id=ev.target.attributes.id.value;
        this.actionService.doAction({
            name:'Alerte',
            type: 'ir.actions.act_window',
            res_id: parseInt(id),
            res_model: 'is.chantier.alerte',
            views: [[false, 'form']],
        });
    }





    ModifierChantierClick(ev) {
        const id=ev.target.attributes.id.value;
        this.actionService.doAction({
            name:'Chantier',
            type: 'ir.actions.act_window',
            target: 'new',
            res_id: parseInt(id),
            res_model: 'is.chantier',
            views: [[false, 'form']],
        });
    }

    onChangeNbSemaines(ev){
        this.state.nb_semaines = ev.target.value;
        this.GetChantiers();
    }
    onChangeChantier(ev){
        this.state.filtre_chantier = ev.target.value;
        this.GetChantiers();
    }
    onChangeEquipe(ev){
        this.state.filtre_equipe = ev.target.value;
        this.GetChantiers();
    }
    onChangeTravaux(ev){
        this.state.filtre_travaux = ev.target.value;
        this.GetChantiers();
    }
    RafraichirClick(ev) {
        this.GetChantiers();
    }
    PrecedentClick(ev) {
        this.state.decale_planning = this.state.decale_planning-7;
        this.GetChantiers();
    }
    SuivantClick(ev) {
        this.state.decale_planning = this.state.decale_planning+7;
        this.GetChantiers();
    }
    onChangeState(ev) {
        this.state.chantier_state = ev.target.value;
        this.GetChantiers();
    }
    OKButtonClick(ev) {
        this.state.decale_planning = 0;
        this.GetChantiers();
    }



    async GetChantiers(){
        if (!this.orm) {
            console.error('Service ORM non disponible pour GetChantiers');
            return;
        }

        console.log('PlanningChantierRenderer GetChantiers - domain reçu du contrôleur:', this.props.domain);

        try {
            const params = {
                domain         : this.props.domain || [],
                decale_planning: this.state.decale_planning,
                nb_semaines    : this.state.nb_semaines,
                filtre_chantier: this.state.filtre_chantier,
                filtre_equipe  : this.state.filtre_equipe,
                filtre_travaux : this.state.filtre_travaux,
                chantier_state : this.state.chantier_state,
            };
            
            console.log('PlanningChantierRenderer GetChantiers - paramètres envoyés au backend:', params);
            
            const result = await this.orm.call(
                'is.chantier',
                'get_chantiers',
                [],
                params
            );
            
            this.state.dict            = result.dict;
            this.state.mois            = result.mois;
            this.state.semaines        = result.semaines;
            this.state.nb_semaines     = result.nb_semaines;
            this.state.decale_planning = result.decale_planning;
            this.state.autorise_modif  = result.autorise_modif;
            this.state.filtre_chantier = result.filtre_chantier;
            this.state.filtre_equipe   = result.filtre_equipe;
            this.state.filtre_travaux  = result.filtre_travaux;
            this.state.state_options   = result.state_options;
            this.state.chantier_state  = result.chantier_state;
        } catch (error) {
            console.error('Erreur lors du chargement des chantiers:', error);
        }
    }

    async ModifDureeChantier(chantierid,duree){
        if (!this.orm) {
            console.error('Service ORM non disponible pour ModifDureeChantier');
            return;
        }

        try {
            const result = await this.orm.call(
                'is.chantier',
                'modif_duree_chantier',
                [],
                {
                    chantierid     : chantierid,
                    duree          : duree,
                }
            );
            console.log("ModifDureeChantier : result=", result);
        } catch (error) {
            console.error('Erreur lors de la modification de la durée:', error);
        }
    }

    async moveChantier(chantierid, debut, decale_planning){
        if (!this.orm) {
            console.error('Service ORM non disponible pour moveChantier');
            return;
        }

        try {
            const result = await this.orm.call(
                'is.chantier',
                'move_chantier',
                [],
                {
                    chantierid     : chantierid,
                    debut          : debut,
                    decale_planning: decale_planning,
                }
            );
            console.log("moveChantier : result=", result);
        } catch (error) {
            console.error('Erreur lors du déplacement du chantier:', error);
        }
    }



    PDFClick(ev) {
        this.GetPlanningPDF();
    }

    async GetPlanningPDF(){
        if (!this.orm) {
            console.error('Service ORM non disponible pour GetPlanningPDF');
            return;
        }

        try {
            const result = await this.orm.call(
                'is.chantier',
                'get_planning_pdf',
                [],
                {}
            );
            
            console.log('## GetPlanningPDF result:', result);

            if (result) {
                // Option recommandée : utiliser le service d'action
                this.actionService.doAction({
                    type: 'ir.actions.act_url',
                    url: `/web/content/${result}?download=true`,
                    target: 'new',
                });
                // Option 2: Ouvrir dans un nouvel onglet
                //window.open(`/web/content/${result}?download=true`, '_blank');
                
                // Option 3: Alternative - Téléchargement direct
                // const link = document.createElement('a');
                // link.href = `/web/content/${result}?download=true`;
                // link.download = `planning_chantiers_${new Date().getTime()}.pdf`;
                // document.body.appendChild(link);
                // link.click();
                // document.body.removeChild(link);
            } else {
                this.env.services.notification.add(
                    "Impossible de générer le PDF. Veuillez vérifier la configuration.",
                    { type: 'warning' }
                );
            }
        } catch (error) {
            console.error('Erreur lors de la génération du PDF:', error);
            this.env.services.notification.add(
                "Erreur lors de la génération du PDF: " + error.message,
                { type: 'danger' }
            );
        }


        // rpc.query({
        //     model: 'is.chantier',
        //     method: 'get_planning_pdf',
        //     kwargs: {
        //     }
        // }).then(function (result) {
        //     self.env.bus.trigger('do-action', {
        //         action: {
        //             type: 'ir.actions.act_url',
        //             url: '/web/content/'+result+'?download=true',
        //         },
        //     });
        // });


    }





    // getGroupInfo(activityType) {
    //     const types = {
    //         done: {
    //             color: "secondary",
    //             inProgressBar: false,
    //             label: _t("done"), // activity_mixin.activity_state has no done state, so we add it manually here
    //             value: 0,
    //         },
    //         planned: {
    //             color: "success",
    //             inProgressBar: true,
    //             value: 0,
    //         },
    //         today: {
    //             color: "warning",
    //             inProgressBar: true,
    //             value: 0,
    //         },
    //         overdue: {
    //             color: "danger",
    //             inProgressBar: true,
    //             value: 0,
    //         },
    //     };
    //     for (const [type, label] of this.props.fields.activity_state.selection) {
    //         types[type].label = label;
    //     }
    //     const typeId = activityType.id;
    //     const isColumnFiltered = this.activeFilter.activityTypeId === activityType.id;
    //     const progressValue = isColumnFiltered ? this.activeFilter.progressValue : { active: null };

    //     let totalCountWithoutDone = 0;
    //     for (const activities of Object.values(this.props.groupedActivities)) {
    //         if (typeId in activities) {
    //             for (const [state, stateCount] of Object.entries(
    //                 activities[typeId].count_by_state
    //             )) {
    //                 types[state].value += stateCount;
    //                 if (state !== "done") {
    //                     totalCountWithoutDone += stateCount;
    //                 }
    //             }
    //         }
    //     }

    //     const progressBar = {
    //         bars: [],
    //         activeBar: isColumnFiltered ? this.activeFilter.progressValue.active : null,
    //     };
    //     for (const [value, count] of Object.entries(types)) {
    //         if (count.inProgressBar) {
    //             progressBar.bars.push({
    //                 count: count.value,
    //                 value,
    //                 string: types[value].label,
    //                 color: count.color,
    //             });
    //         }
    //     }

    //     const ongoingActivityCount = types.overdue.value + types.today.value + types.planned.value;
    //     const ongoingAndDoneCount = ongoingActivityCount + types.done.value;
    //     const labelAggregate = `${types.overdue.label} + ${types.today.label} + ${types.planned.label}`;
    //     const aggregateOn =
    //         ongoingAndDoneCount && this.isTypeDisplayDone(typeId)
    //             ? {
    //                   title: `${types.done.label} + ${labelAggregate}`,
    //                   value: ongoingAndDoneCount,
    //               }
    //             : undefined;
    //     return {
    //         aggregate: {
    //             title: labelAggregate,
    //             value: isColumnFiltered ? types[progressValue.active].value : ongoingActivityCount,
    //         },
    //         aggregateOn: aggregateOn,
    //         data: {
    //             count: totalCountWithoutDone,
    //             filterProgressValue: (name) => this.onSetProgressBarState(typeId, name),
    //             progressBar,
    //             progressValue,
    //         },
    //     };
    // }

    // getRecord(resId) {
    //     return this.props.records.find((r) => r.resId === resId);
    // }

    // isTypeDisplayDone(typeId) {
    //     return this.props.activityTypes.find((a) => a.id === typeId).keep_done;
    // }

    // onSetProgressBarState(typeId, bar) {
    //     const name = bar.value;
    //     if (this.activeFilter.progressValue.active === name) {
    //         this.activeFilter.progressValue.active = null;
    //         this.activeFilter.activityTypeId = null;
    //         this.activeFilter.resIds = new Set(Object.keys(this.props.groupedActivities));
    //     } else {
    //         this.activeFilter.progressValue.active = name;
    //         this.activeFilter.activityTypeId = typeId;
    //         this.activeFilter.resIds = new Set(
    //             Object.entries(this.props.groupedActivities)
    //                 .filter(
    //                     ([, resIds]) => typeId in resIds && name in resIds[typeId].count_by_state
    //                 )
    //                 .map(([key]) => parseInt(key))
    //         );
    //     }
    // }

    // get activeColumns() {
    //     return this.props.activityTypes.filter(
    //         (activityType) => this.storageActiveColumns[activityType.id]
    //     );
    // }

    // setupStorageActiveColumns() {
    //     const storageActiveColumnsList = browser.localStorage.getItem(this.storageKey)?.split(",");

    //     this.storageActiveColumns = useState({});
    //     for (const activityType of this.props.activityTypes) {
    //         if (storageActiveColumnsList) {
    //             this.storageActiveColumns[activityType.id] = storageActiveColumnsList.includes(
    //                 activityType.id.toString()
    //             );
    //         } else {
    //             this.storageActiveColumns[activityType.id] = true;
    //         }
    //     }
    // }

    // toggleDisplayColumn(typeId) {
    //     this.storageActiveColumns[typeId] = !this.storageActiveColumns[typeId];
    //     browser.localStorage.setItem(
    //         this.storageKey.join(","),
    //         Object.keys(this.storageActiveColumns).filter(
    //             (activityType) => this.storageActiveColumns[activityType]
    //         )
    //     );
    // }
}

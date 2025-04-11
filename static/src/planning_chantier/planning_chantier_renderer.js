/** @odoo-module **/
import AbstractRendererOwl from 'web.AbstractRendererOwl';
import core  from 'web.core';
import QWeb from 'web.QWeb';
import session from 'web.session';
import utils from 'web.utils';

const _t = core._t;
//const { useState } = owl.hooks;

const { useState, onMounted, onPatched, onWillUnmount } = owl.hooks;



var rpc = require('web.rpc');


class PlanningChantierRenderer extends AbstractRendererOwl {
    constructor(parent, props) {
        super(...arguments);
        this.qweb = new QWeb(this.env.isDebug(), {_s: session.origin});
        this.qweb.add_template(utils.json_node_to_xml(props.templates));
 
        //useState permet de faire un lien entre la vue XML et l'Object Javascript
        //Chaque modification de l'objet this.state entraine une modification de l'interface utilisateur
        this.state = useState({
            decale_planning: "",
            nb_semaines:"",
            dict:{},
        });
        this.ActivePatched=true;
        //onMounted(() => this._mounted());
        //onPatched(() => this._patched());
    }

    mounted() {
        this.GetChantiers();
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
        this.env.bus.trigger('do-action', {
            action: {
                name:'Chantier',
                type: 'ir.actions.act_window',
                res_id: parseInt(id),
                res_model: 'is.chantier',
                views: [[false, 'form']],
            },
        });
    }

    CreationAlerteClick(ev) {
        const id=ev.target.attributes.id.value;
        console.log('CreationAlerteClick',id);
        this.env.bus.trigger('do-action', {
            action: {
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
            },
        });
    }



    alerteClick(ev) {
        const id=ev.target.attributes.id.value;
        this.env.bus.trigger('do-action', {
            action: {
                name:'Alerte',
                type: 'ir.actions.act_window',
                res_id: parseInt(id),
                res_model: 'is.chantier.alerte',
                views: [[false, 'form']],
            },
        });
    }




    // chantier_id = fields.Many2one('is.chantier', 'Chantier', required=True, index=True)
    // affaire_id  = fields.Many2one(related="chantier_id.affaire_id")
    // alerte      = fields.Text('Alerte'                     , required=True)
    // date        = fields.Date('Date alerte', default=fields.Datetime.now, index=True, help="Date à laquelle l'alerte sera positionnée sur le planning des chantiers")



//     return {
//         type: 'ir.actions.act_window',
//         name: _t('Employee Termination'),
//         res_model: 'hr.departure.wizard',
//         views: [[false, 'form']],
//         view_mode: 'form',
//         target: 'new',
//         context: {
//             'active_id': id,
//             'toggle_active': true,
//         }
//     }
// }



    ModifierChantierClick(ev) {
        const id=ev.target.attributes.id.value;
        this.env.bus.trigger('do-action', {
            action: {
                name:'Chantier',
                type: 'ir.actions.act_window',
                target: 'new',
                res_id: parseInt(id),
                res_model: 'is.chantier',
                views: [[false, 'form']],
            },
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
        var self=this;
        rpc.query({
            model: 'is.chantier',
            method: 'get_chantiers',
            kwargs: {
                domain         : this.props.domain,
                decale_planning: this.state.decale_planning,
                nb_semaines    : this.state.nb_semaines,
                filtre_chantier: this.state.filtre_chantier,
                filtre_equipe  : this.state.filtre_equipe,
                filtre_travaux : this.state.filtre_travaux,
                chantier_state : this.state.chantier_state,
            }
        }).then(function (result) {
            self.state.dict            = result.dict;
            self.state.mois            = result.mois;
            self.state.semaines        = result.semaines;
            self.state.nb_semaines     = result.nb_semaines;
            self.state.decale_planning = result.decale_planning;
            self.state.autorise_modif  = result.autorise_modif;
            self.state.filtre_chantier = result.filtre_chantier;
            self.state.filtre_equipe   = result.filtre_equipe;
            self.state.filtre_travaux  = result.filtre_travaux;
            self.state.state_options   = result.state_options;
            self.state.chantier_state  = result.chantier_state;
        });
    }

    async ModifDureeChantier(chantierid,duree){
        var self=this;
        rpc.query({
            model: 'is.chantier',
            method: 'modif_duree_chantier',
            kwargs: {
                chantierid     : chantierid,
                duree          : duree,
            }
        }).then(function (result) {
            console.log("ModifDureeChantier : result=",result);
        });
    }



    async moveChantier(chantierid, debut, decale_planning){
        var self=this;
        rpc.query({
            model: 'is.chantier',
            method: 'move_chantier',
            kwargs: {
                chantierid     : chantierid,
                debut          : debut,
                decale_planning: decale_planning,
            }
        }).then(function (result) {
            console.log("moveChantier : result=",result);
        });
    }

    PDFClick(ev) {
        this.GetPlanningPDF();
    }
    async GetPlanningPDF(s){
        var self=this;
        rpc.query({
            model: 'is.chantier',
            method: 'get_planning_pdf',
            kwargs: {
            }
        }).then(function (result) {
            self.env.bus.trigger('do-action', {
                action: {
                    type: 'ir.actions.act_url',
                    url: '/web/content/'+result+'?download=true',
                },
            });
        });
    }
}

PlanningChantierRenderer.components = {};
PlanningChantierRenderer.template = 'is_clair_sarl.PlanningChantierTemplate';
export default PlanningChantierRenderer;

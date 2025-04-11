/** @odoo-module **/
import BasicModel from 'web.BasicModel';
import session from 'web.session';


const PlanningChantierModel = BasicModel.extend({
    // __get: function () {
    //     var result = this._super.apply(this, arguments);
    //     if (result && result.model === this.modelName && result.type === 'list') {
    //         _.extend(result, this.additionalData, this.additionalChantier);
    //         //_.extend(result, this.additionalData, this.additionalPartner);
    //         //_.extend(result, this.additionalData, {getKanbanActivityData: this.getKanbanActivityData});
    //     }

    //     console.log(result);


    //     return result;
    // },




    /**
     * @override
     * @param {Array[]} params.domain
     */
    __load: function (params) {
        console.log("PlanningChantierModel : __load : params=",params); 
        this.originalDomain = _.extend([], params.domain);
        //params.domain.push(['id', '=', false]);
        this.domain = params.domain;
        this.modelName = params.modelName;
        params.groupedBy = [];
        var def = this._super.apply(this, arguments);
        return Promise.all([def, this._fetchData()]).then(function (result) {
            return result[0];
        });
    },
    /**
     * @override
     * @param {Array[]} [params.domain]
     */
    __reload: function (handle, params) {
        console.log("PlanningChantierModel : __reload : params=",params); 
        if (params && 'domain' in params) {
            this.originalDomain = _.extend([], params.domain);
            //params.domain.push(['id', '=', false]);
            this.domain = params.domain;
        }
        if (params && 'groupBy' in params) {
            params.groupBy = [];
        }
        var def = this._super.apply(this, arguments);
        return Promise.all([def, this._fetchData()]).then(function (result) {
            return result[0];
        });
    },



    /**
     * Fetch activity data.
     *
     * @private
     * @returns {Promise}
     */
    _fetchData: function () {
        console.log("PlanningChantierModel : this.domain=",this.domain); 





        //var self = this;
        // this._rpc({
        //     model: "mail.activity",
        //     method: 'get_activity_data',
        //     kwargs: {
        //         res_model: this.modelName,
        //         domain: this.domain,
        //         context: session.user_context,
        //     }
        // }).then(function (result) {
        //     self.additionalData = result;
        //     console.log("_fetchData : additionalData : result=",result);
        //     console.log("_fetchData : additionalData : self=",self);
        // });

        // this._rpc({
        //     model: 'res.partner',
        //     method: 'get_vue_owl_99',
        //     kwargs: {
        //         domain: this.domain,
        //     }
        // }).then(function (result) {
        //     //console.log("get_vue_owl_99 : result=",result);
        //     //self.additionalPartner = result;
        //     self.additionalData = result;
        //     console.log("_fetchData : additionalData : result=",result);
        //     console.log("_fetchData : additionalData : self=",self);
        // });

        // this._rpc({
        //     model: 'is.chantier',
        //     method: 'get_chantiers',
        //     kwargs: {
        //         domain: this.domain,
        //     }
        // }).then(function (result) {
        //     //console.log("get_vue_owl_99 : result=",result);
        //     //self.additionalPartner = result;
        //     self.additionalChantier = result;
        //     console.log("_fetchData : additionalChantier : result=",result);
        //     //console.log("_fetchData : additionalChantier : self=",self);
        // });



    },








});

export default PlanningChantierModel;

/** @odoo-module **/
import KanbanRecord from 'web.KanbanRecord';

var PlanningChantierRecord = KanbanRecord.extend({
    /**
     * @override
     */
    init: function (parent, state) {
        this._super.apply(this,arguments);
        console.log("PlanningChantierRecord : __get : parent,state,this=",parent,state,this); 
        //this.fieldsInfo = state.fieldsInfo.activity;
    },
});

export default PlanningChantierRecord;

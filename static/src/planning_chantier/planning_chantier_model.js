//TODO : Je suis reparti du type de vue 'activity' "@mail/views/web/activity" qui est le plus simple
import { RelationalModel } from "@web/model/relational_model/relational_model";

console.log('PlanningChantierModel')

export class PlanningChantierModel extends RelationalModel {
    static DEFAULT_LIMIT = 100;

    async load(params = {}) {
        this.originalDomain = params.domain ? [...params.domain] : [];
        //await Promise.all([this.fetchActivityData(params), super.load(params)]);
        await Promise.all([this.fetchData(params), super.load(params)]);
    }


    async fetchData(params) {
        console.log('fetchData 1',params);
        this.data = await this.orm.call(params.resModel, "search_read", [], {
            fields : params.fields,
            domain : params.domain,
            order  : params.orderBy,
            context: params.context,
            limit  : params.limit,
        })
        console.log('fetchData 2',this.data);
    }


    async fetchActivityData(params) {
        console.log('fetchActivityData',params);
        this.activityData = await this.orm.call("mail.activity", "get_activity_data", [], {
            res_model: this.config.resModel,
            domain: params.domain || this.env.searchModel._domain,
            limit: params.limit || this.initialLimit,
            offset: params.offset || 0,
            fetch_done: true,
        });
        console.log(this.activityData);
    }



    //setup(params) {
    //    this.params = params;
        // this.model_name = params.resModel;
        // this.fields = this.params.fields;
        // this.date_start = this.params.date_start;
        // this.date_stop = this.params.date_stop;
        // this.date_delay = this.params.date_delay;
        // this.colors = this.params.colors;
        // this.last_group_bys = this.params.default_group_by.split(",");
        // const templates = useViewCompiler(KanbanCompiler, this.params.templateDocs);
        // this.recordTemplate = templates["timeline-item"];

        // this.keepLast = new KeepLast();
        // onWillStart(async () => {
        //     this.write_right = await this.orm.call(
        //         this.model_name,
        //         "check_access_rights",
        //         ["write", false]
        //     );
        //     this.unlink_right = await this.orm.call(
        //         this.model_name,
        //         "check_access_rights",
        //         ["unlink", false]
        //     );
        //     this.create_right = await this.orm.call(
        //         this.model_name,
        //         "check_access_rights",
        //         ["create", false]
        //     );
        // });
    //}
}

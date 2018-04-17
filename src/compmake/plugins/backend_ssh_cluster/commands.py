# -*- coding: utf-8 -*-
#
# @ui_command(section=COMMANDS_CLUSTER, dbchange=True)
# def clustmake(job_list, context, cq):
# ''' (experimental) Cluster equivalent of "make". '''
#     # job_list = list(job_list) # don't ask me why XXX
#     job_list = [x for x in job_list]
# 
#     if not job_list:
#         db = context.get_compmake_db()
#         job_list = list(top_targets(db))
# 
#     cluster_conf = get_compmake_config('cluster_conf')
# 
#     if not os.path.exists(cluster_conf):
#         msg = ('Configuration file %r does not exist.' % cluster_conf)
#         raise UserError(msg)
# 
#     hosts = parse_yaml_configuration(open(cluster_conf))
#     manager = ClusterManager(hosts=hosts, context=context, cq=cq)
#     manager.add_targets(job_list)
#     manager.process()
#     return raise_error_if_manager_failed(manager)

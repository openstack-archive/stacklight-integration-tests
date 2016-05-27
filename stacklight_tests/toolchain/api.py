# coding=utf-8
#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from datetime import date
from datetime import datetime
from devops.helpers import helpers as devops_helpers
from fuelweb_test.helpers.rally import RallyBenchmarkTest
from fuelweb_test import logger
from fuelweb_test import settings
from fuelweb_test.tests import base_test_case
import os
from proboscis import asserts
from stacklight_tests.elasticsearch_kibana import api as elasticsearch_api
from stacklight_tests.helpers import checkers
from stacklight_tests.helpers import helpers
from stacklight_tests.helpers import remote_ops
from stacklight_tests.helpers import ui_tester
from stacklight_tests.influxdb_grafana import api as influx_api
from stacklight_tests.lma_collector import api as collector_api
from stacklight_tests.lma_infrastructure_alerting import (
    api as infrastructure_alerting_api)
from stacklight_tests.toolchain import toolchain_settings
import time
import traceback


class ToolchainApi(object):
    def __init__(self):
        self.test = base_test_case.TestBasic()
        self.env = self.test.env
        self.settings = toolchain_settings
        self.helpers = helpers.PluginHelper(self.env)
        self.checkers = checkers
        self.remote_ops = remote_ops
        self.ui_tester = ui_tester
        self.plugins = [
            elasticsearch_api.ElasticsearchPluginApi(),
            influx_api.InfluxdbPluginApi(),
            collector_api.LMACollectorPluginApi(),
            infrastructure_alerting_api.InfraAlertingPluginApi()]

    def __getattr__(self, item):
        return getattr(self.test, item)

    def prepare_plugins(self):
        for plugin in self.plugins:
            plugin.prepare_plugin()

    def activate_plugins(self):
        msg = "Activate {} plugin"
        for plugin in self.plugins:
            logger.info(msg.format(plugin.get_plugin_settings().name))
            plugin.activate_plugin(
                options=plugin.get_plugin_settings().toolchain_options)

    def check_plugins_online(self):
        msg = "Check {} plugin"
        for plugin in self.plugins:
            logger.info(msg.format(plugin.get_plugin_settings().name))
            plugin.check_plugin_online()

    def elasticsearch_monitoring_check(self):
        kibana_url = self.plugins[0].get_kibana_url()
        timestamp = time.time()
        dt = date.today()
        data = '{{"facets":{{"terms":{{"terms":{{"field":"Hostname",' \
               '"size":10000,"order":"count","exclude":[]}},"facet_filter":' \
               '{{"fquery":{{"query":{{"filtered":{{"query":{{"bool":{{' \
               '"should":[{{"query_string":{{"query":"*"}}}}]}}}},"filter"' \
               ':{{"bool":{{"must":[{{"range":{{"Timestamp":{{"from":{0}' \
               '}}}}}}]}}}}}}}}}}}}}}}},"size": 0}}'.format(timestamp - 300)
        url = '{0}/log-{1}/_search?pretty'.format(kibana_url,
                                                  dt.strftime("%Y.%m.%d"))
        output = self.checkers.check_http_get_response(url=url, data=data)

        self.check_node_in_output(output)

    def influxdb_monitoring_check(self):
        influxdb_pluign = self.plugins[1]
        influxdb_settings = influxdb_pluign.get_plugin_settings()
        output = influxdb_pluign.do_influxdb_query(
            "SELECT last(value), hostname FROM cpu_user WHERE "
            "time > now() - 3m GROUP BY hostname",
            user=influxdb_settings.influxdb_rootuser,
            password=influxdb_settings.influxdb_rootpass)
        self.check_node_in_output(output)

    def lma_infrastructure_alerting_monitoring_check(self):
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, [])
        lma_infra_alerting_plugin = self.plugins[3]
        driver = lma_infra_alerting_plugin.open_nagios_page(
            'Hosts', "//table[@class='headertable']")
        time_difference = 600
        try:
            for node in nailgun_nodes:
                time_before = time.time() - time_difference
                check = False
                table = self.ui_tester.get_table(
                    driver, "/html/body/div[2]/table/tbody")
                for ind in xrange(2, self.ui_tester.get_table_size(table) + 1):
                    node_name = self.ui_tester.get_table_cell(
                        table, ind, 1).text.rstrip()
                    if node["hostname"] == node_name:
                        check = True
                        state = self.ui_tester.get_table_cell(
                            table, ind, 2).text.rstrip()
                        timestamp = datetime.strptime(
                            self.ui_tester.get_table_cell(
                                table, ind, 3).text.rstrip(),
                            '%Y-%m-%d %H:%M:%S')
                        asserts.assert_equal(
                            'UP', state, "Node {0} is in wrong state! {1} is"
                                         " not 'UP'".format(node["hostname"],
                                                            state))
                        asserts.assert_true(
                            time.mktime(timestamp.timetuple()) > time_before,
                            "Node {0} check is outdated! Must be {1} secs, now"
                            " {2}".format(node["hostname"], time_difference,
                                          time.time() -
                                          time.mktime(timestamp.timetuple())))
                        break
                asserts.assert_true(check, "Node {0} was not found in "
                                           "nagios!".format(node["hostname"]))
        finally:
            driver.close()
        # NOTE (vushakov): some services will fall to CRITICAL state during
        #     close to production load. Temporary removing service state check.
        # driver = lma_infra_alerting_plugin.open_nagios_page(
        #     'Services', "//table[@class='headertable']")
        # try:
        #     self.check_service_state_on_nagios(driver)
        # finally:
        #     driver.close()

    def check_service_state_on_nagios(self, driver, service_state=None,
                                      nodes=None):
        table = self.ui_tester.get_table(driver, "/html/body/table[3]/tbody")
        if not nodes:
            nodes = [self.ui_tester.get_table_cell(table, 2, 1).text]
        for node in nodes:
            node_services = self.get_services_for_node(table, node)
            if service_state:
                for service in service_state:
                    asserts.assert_equal(
                        service_state[service], node_services[service],
                        "Wrong service state found on node {0}: expected"
                        " {1} but found {2}".format(nodes,
                                                    service_state[service],
                                                    node_services[service]))
            else:
                for service in node_services:
                    asserts.assert_equal(
                        'OK', node_services[service],
                        "Wrong service state found on node {0}: expected"
                        " OK but found {1}".format(nodes,
                                                   node_services[service]))

    def get_services_for_node(self, table, node_name):
        services = {}
        node_start, node_end = '', ''
        for ind in xrange(2, self.ui_tester.get_table_size(table) + 1):
            if not self.ui_tester.get_table_row(table, ind).text:
                if node_start:
                    node_end = ind
                    break
                else:
                    continue
            if self.ui_tester.get_table_cell(table, ind, 1).text == node_name:
                node_start = ind

        for ind in xrange(node_start, node_end):
            services[self.ui_tester.get_table_cell(table, ind, 2).text] = \
                self.ui_tester.get_table_cell(table, ind, 3).text
        return services

    def check_node_in_output(self, output):
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, [])
        missing_nodes = []
        for node in nailgun_nodes:
            if '"{0}"'.format(node["hostname"]) not in output.text:
                missing_nodes.append(node["hostname"])
        asserts.assert_false(len(missing_nodes),
                             "Failed to find {0} nodes in the output! Missing"
                             " nodes are: {1}".format(len(missing_nodes),
                                                      missing_nodes))

    def restart_services_actions(self, queue, cluster_id):
        test = base_test_case.TestBasic()
        env = test.env
        fuel_web = env.fuel_web
        try:
            logger.info("Moving vip__management service to another node")
            nailgun_controllers = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, ['controller'])
            devops_nodes = fuel_web.get_devops_nodes_by_nailgun_nodes(
                nailgun_controllers)
            service_node = fuel_web.get_pacemaker_resource_location(
                devops_nodes[1].name, "vip__management")[0]

            for node in nailgun_controllers:
                if node['name'] == service_node.name + "_controller_ceph-osd":
                    nailgun_controllers.remove(node)

            self.move_resource(fuel_web, nailgun_controllers[0],
                               "vip__management", nailgun_controllers[0])
            self.monitoring_check()
            logger.info("Waiting for 1 hour")
            time.sleep(3600)
            logger.info("Moving vip__management service to another node")
            self.move_resource(fuel_web, nailgun_controllers[1],
                               "vip__management", nailgun_controllers[1])
            self.monitoring_check()

            nailgun_controllers = \
                fuel_web.get_nailgun_cluster_nodes_by_roles(cluster_id,
                                                            ['controller'])

            logger.info("Checking PID of hekad and collectd on all nodes.")
            pids = self.get_tasks_pids(fuel_web, ['hekad', 'collectd'])

            logger.info("Stopping lma_collector (heka).")
            self.manage_pcs_resource(fuel_web, nailgun_controllers,
                                     "lma_collector", "disable", "Stopped")
            logger.info("Checking PID of hekad on all controllers.")
            self.get_tasks_pids(fuel_web, ['hekad'], nailgun_controllers, 1)
            logger.info("Starting lma_collector (heka)")
            self.manage_pcs_resource(fuel_web, nailgun_controllers,
                                     "lma_collector", "enable", "Started")
            self.monitoring_check()

            nailgun_compute = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, ['compute'])
            nailgun_plugins = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, self.settings.stacklight_roles)

            logger.info("Restarting lma_collector on all nodes except"
                        " controllers.")
            self.manage_lma_collector_service(fuel_web, nailgun_compute,
                                              "restart")
            self.manage_lma_collector_service(fuel_web, nailgun_plugins,
                                              "restart")

            logger.info("Checking PID of hekad on all nodes")
            new_pids = self.get_tasks_pids(fuel_web, ['hekad'])

            for node in new_pids:
                asserts.assert_true(
                    new_pids[node]["hekad"] != pids[node]["hekad"],
                    "hekad on {0} hasn't changed it's pid! Was {1} now "
                    "{2}".format(node, pids[node]["hekad"],
                                 new_pids[node]["hekad"]))
            self.monitoring_check()

            logger.info("Stopping lma_collector on all nodes except"
                        " controllers.")
            self.manage_lma_collector_service(fuel_web, nailgun_compute,
                                              "stop")
            self.manage_lma_collector_service(fuel_web, nailgun_plugins,
                                              "stop")
            logger.info("Checking PID of hekad on all nodes except"
                        " controllers")
            self.get_tasks_pids(fuel_web, ['hekad'], nailgun_compute, 1)
            self.get_tasks_pids(fuel_web, ['hekad'], nailgun_plugins, 1)
            logger.info("Starting lma_collector on all nodes except"
                        " controllers.")
            self.manage_lma_collector_service(fuel_web, nailgun_compute,
                                              "start")
            self.manage_lma_collector_service(fuel_web, nailgun_plugins,
                                              "start")
            self.monitoring_check()

            msg = "hekad has not been restarted by pacemaker on node" \
                  " {0} after kill -9"
            for node in nailgun_controllers:
                with fuel_web.get_ssh_for_nailgun_node(node) as remote:
                    def wait_for_restart():
                        if remote.execute("pidof hekad")["exit_code"]:
                            return False
                        else:
                            return True
                    logger.info("Killing heka process with “kill -9” command "
                                "on {0}.".format(node["name"]))
                    exec_res = remote.execute("kill -9 `pidof hekad`")
                    asserts.assert_equal(0, exec_res['exit_code'],
                                         "Failed to kill -9 hekad on"
                                         " {0}".format(node["name"]))
                    logger.info("Waiting while pacemaker starts heka process "
                                "on {0}.".format(node["name"]))
                    devops_helpers.wait(wait_for_restart,
                                        timeout=60 * 5,
                                        timeout_msg=msg.format(node["name"]))
            queue.put(True)
        except Exception as ex:
            logger.error(ex)
            logger.error(traceback.format_exc())
            queue.put(False)
            queue.put(os.getpid())

    def manage_lma_collector_service(self, fuel_web, nodes, action):
        for node in nodes:
            with fuel_web.get_ssh_for_nailgun_node(node) as remote:
                exec_res = remote.execute("{0} lma_collector".format(action))
                asserts.assert_equal(0, exec_res['exit_code'],
                                     "Failed to {0} lma_collector on"
                                     " {1}".format(action, node["name"]))

    def manage_pcs_resource(self, fuel_web, nodes, resource, action, check):
        def check_state():
            grep = "grep {0} | grep {1} | grep {2}".format(
                nodes[0]["hostname"], nodes[1]["hostname"],
                nodes[2]["hostname"])
            with fuel_web.get_ssh_for_nailgun_node(nodes[0]) as remote:
                result = remote.execute(
                    "pcs status | grep {0} | {1}".format(check, grep))
                if not result['exit_code']:
                    return True
                else:
                    return False
        with fuel_web.get_ssh_for_nailgun_node(nodes[0]) as remote:
            exec_res = remote.execute("pcs resource {0} {1}".format(
                action, resource))
            asserts.assert_equal(0, exec_res['exit_code'],
                                 "Failed to {0} resource {1} on {2}".format(
                                     action, resource, nodes[0]["name"]))

        msg = "Failed to stop {0} on all nodes!".format(resource)
        devops_helpers.wait(check_state, timeout=5 * 60, timeout_msg=msg)

    def get_tasks_pids(self, fuel_web, processes, nodes=None, exit_code=0):
        nodes = nodes or \
            fuel_web.client.list_cluster_nodes(
                fuel_web.get_last_created_cluster())
        pids = {}
        for node in nodes:
            with fuel_web.get_ssh_for_nailgun_node(node) as remote:
                pids[node["name"]] = {}
                for process in processes:
                    result = remote.execute("pidof {0} ".format(process))
                    if exit_code:
                        asserts.assert_equal(exit_code, result['exit_code'],
                                             "process {0} is running on "
                                             "{1}".format(process,
                                                          node["name"]))
                    else:
                        pids[node["name"]][process] = \
                            result['stdout'][0].rstrip()

        return pids

    def move_resource(self, fuel_web, node, resource_name, move_to):
        with fuel_web.get_ssh_for_nailgun_node(node) as remote:
            exec_res = remote.execute("pcs resource move {0} {1}".format(
                resource_name, move_to["fqdn"]))
            asserts.assert_equal(0, exec_res['exit_code'],
                                 "Failed to move resource {0} to {1}".format(
                                     resource_name, move_to["fqdn"]))

    def monitoring_check(self):
        logger.info("Checking that lma_collector (heka) sending data to"
                    " Elasticsearch, InfluxDB, Nagios.")
        self.elasticsearch_monitoring_check()
        self.influxdb_monitoring_check()
        self.lma_infrastructure_alerting_monitoring_check()

    def create_load(self, queue, cluster_id):
        logger.info("Creating close to production load")
        send_flag = True
        workspace = ""
        if "WORKSPACE" in os.environ.keys():
            workspace = os.environ["WORKSPACE"]
        base_path = base_test_case.__file__.split("site-packages")[0]
        os.environ["WORKSPACE"] = base_path + "/site-packages"

        test = base_test_case.TestBasic()
        env = test.env
        fuel_web = env.fuel_web
        try:
            while(True):
                files = self.fill_ceph(fuel_web, cluster_id)
                fuel_web.check_ceph_status(1)
                if send_flag:
                    queue.put(True)
                    send_flag = False
                self.run_rally_benchmark(env, cluster_id)
                self.clean_ceph(fuel_web, files, cluster_id)
        except Exception as ex:
            logger.error(ex)
            queue.put(False)
            queue.put(os.getpid())
        finally:
            os.environ["WORKSPACE"] = workspace

    def fill_ceph(self, fuel_web, cluster_id):
        ceph_nodes = fuel_web.get_nailgun_cluster_nodes_by_roles(
            cluster_id, ['ceph-osd'])
        files = {}
        for node in ceph_nodes:
            with fuel_web.get_ssh_for_nailgun_node(node) as remote:
                file_name = "test_data"
                file_dir = remote.execute(
                    'mount | grep -m 1 ceph')['stdout'][0].split()[2]
                file_path = os.path.join(file_dir, file_name)
                files[node["name"]] = file_path
                result = remote.execute(
                    'fallocate -l 30G {0}'.format(file_path))['exit_code']
                asserts.assert_equal(result, 0, "The file {0} was not "
                                     "allocated".format(file_name))
        return files

    def clean_ceph(self, fuel_web, files, cluster_id):
        ceph_nodes = fuel_web.get_nailgun_cluster_nodes_by_roles(
            cluster_id, ['ceph-osd'])
        for node in ceph_nodes:
            with fuel_web.get_ssh_for_nailgun_node(node) as remote:
                result = remote.execute(
                    'rm -f {0}'.format(files[node["name"]]))['exit_code']
                asserts.assert_equal(result, 0, "The file {0} was not "
                                     "removed".format(files[node["name"]]))

    def run_rally_benchmark(self, env, cluster_id):
        settings.PATCHING_RUN_RALLY = True
        asserts.assert_true(settings.PATCHING_RUN_RALLY,
                            'PATCHING_RUN_RALLY was not set in true')
        rally_benchmarks = {}
        benchmark_results = {}
        for tag in set(settings.RALLY_TAGS):
            rally_benchmarks[tag] = RallyBenchmarkTest(
                container_repo=settings.RALLY_DOCKER_REPO,
                environment=env,
                cluster_id=cluster_id,
                test_type=tag
            )
            benchmark_results[tag] = rally_benchmarks[tag].run()
            logger.debug(benchmark_results[tag].show())

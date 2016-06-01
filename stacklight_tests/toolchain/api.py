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

import os
import time
import traceback

from devops.helpers import helpers as devops_helpers
from fuelweb_test import logger
from fuelweb_test.tests import base_test_case
from proboscis import asserts
from stacklight_tests.elasticsearch_kibana import api as elasticsearch_api
from stacklight_tests.helpers import checkers
from stacklight_tests.helpers import helpers
from stacklight_tests.helpers import load
from stacklight_tests.helpers import remote_ops
from stacklight_tests.helpers import ui_tester
from stacklight_tests.influxdb_grafana import api as influx_api
from stacklight_tests.lma_collector import api as collector_api
from stacklight_tests.lma_infrastructure_alerting import (
    api as infrastructure_alerting_api)
from stacklight_tests.toolchain import toolchain_settings


class ToolchainApi(object):
    def __init__(self):
        self.test = base_test_case.TestBasic()
        self.env = self.test.env
        self.settings = toolchain_settings
        self.helpers = helpers.PluginHelper(self.env)
        self.checkers = checkers
        self.remote_ops = remote_ops
        self.ui_tester = ui_tester
        self.load = load.CreateLoad()
        self.plugins_mapping = {
            "elasticsearch_kibana": elasticsearch_api.ElasticsearchPluginApi(),
            "influxdb_grafana": influx_api.InfluxdbPluginApi(),
            "lma_collector": collector_api.LMACollectorPluginApi(),
            "lma_infrastructure_alerting":
                infrastructure_alerting_api.InfraAlertingPluginApi()
        }
        self.plugins = set(self.plugins_mapping.values())

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

    def check_nodes_count(self, count, hostname, state):
        self.plugins_mapping[
            'elasticsearch_kibana'].check_elasticsearch_nodes_count(count)
        self.plugins_mapping[
            'influxdb_grafana'].check_influxdb_nodes_count(count)
        self.plugins_mapping[
            'lma_infrastructure_alerting'].check_node_in_nagios(
            hostname, state)

    def uninstall_plugins(self):
        for plugin in self.plugins:
            plugin.uninstall_plugin()

    def check_uninstall_failure(self):
        for plugin in self.plugins:
            plugin.check_uninstall_failure()

    def get_pids_of_services(self):
        return self.plugins_mapping["lma_collector"].verify_services()

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

            self.helpers.move_resource(fuel_web, nailgun_controllers[0],
                                       "vip__management",
                                       nailgun_controllers[0])
            self.monitoring_check()
            logger.info("Waiting for 1 hour")
            time.sleep(3600)
            logger.info("Moving vip__management service to another node")
            self.helpers.move_resource(fuel_web, nailgun_controllers[1],
                                       "vip__management",
                                       nailgun_controllers[1])
            self.monitoring_check()

            nailgun_controllers = \
                fuel_web.get_nailgun_cluster_nodes_by_roles(cluster_id,
                                                            ['controller'])

            logger.info("Checking PID of hekad and collectd on all nodes.")
            pids = self.helpers.get_tasks_pids(fuel_web, ['hekad', 'collectd'])

            logger.info("Stopping lma_collector (heka).")
            self.helpers.manage_pcs_resource(fuel_web, nailgun_controllers,
                                             "lma_collector", "disable",
                                             "Stopped")
            logger.info("Checking PID of hekad on all controllers.")
            self.helpers.get_tasks_pids(fuel_web, ['hekad'],
                                        nailgun_controllers, 1)
            logger.info("Starting lma_collector (heka)")
            self.helpers.manage_pcs_resource(fuel_web, nailgun_controllers,
                                             "lma_collector", "enable",
                                             "Started")
            self.monitoring_check()

            nailgun_compute = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, ['compute'])
            nailgun_plugins = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, self.settings.stacklight_roles)

            logger.info("Restarting lma_collector on all nodes except"
                        " controllers.")
            self.plugins_mapping[
                'lma_collector'].manage_lma_collector_service(
                fuel_web, nailgun_compute, "restart")
            self.plugins_mapping[
                'lma_collector'].manage_lma_collector_service(
                fuel_web, nailgun_plugins, "restart")

            logger.info("Checking PID of hekad on all nodes")
            new_pids = self.helpers.get_tasks_pids(fuel_web, ['hekad'])

            for node in new_pids:
                asserts.assert_true(
                    new_pids[node]["hekad"] != pids[node]["hekad"],
                    "hekad on {0} hasn't changed it's pid! Was {1} now "
                    "{2}".format(node, pids[node]["hekad"],
                                 new_pids[node]["hekad"]))
            self.monitoring_check()

            logger.info("Stopping lma_collector on all nodes except"
                        " controllers.")
            self.plugins_mapping[
                'lma_collector'].manage_lma_collector_service(
                fuel_web, nailgun_compute, "stop")
            self.plugins_mapping[
                'lma_collector'].manage_lma_collector_service(
                fuel_web, nailgun_plugins, "stop")
            logger.info("Checking PID of hekad on all nodes except"
                        " controllers")
            self.helpers.get_tasks_pids(fuel_web, ['hekad'], nailgun_compute,
                                        1)
            self.helpers.get_tasks_pids(fuel_web, ['hekad'], nailgun_plugins,
                                        1)
            logger.info("Starting lma_collector on all nodes except"
                        " controllers.")
            self.plugins_mapping[
                'lma_collector'].manage_lma_collector_service(
                fuel_web, nailgun_compute, "start")
            self.plugins_mapping[
                'lma_collector'].manage_lma_collector_service(
                fuel_web, nailgun_plugins, "start")
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
                    logger.info("Killing heka process with 'kill -9' command "
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

    def monitoring_check(self):
        logger.info("Checking that lma_collector (heka) sending data to"
                    " Elasticsearch, InfluxDB, Nagios.")
        self.plugins_mapping[
            'elasticsearch_kibana'].elasticsearch_monitoring_check()
        self.plugins_mapping[
            'influxdb_grafana'].influxdb_monitoring_check()
        self.plugins_mapping[
            'lma_infrastructure_alerting'].lma_infrastructure_alerting_check()

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
import yaml

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
        self.ELASTICSEARCH_KIBANA = elasticsearch_api.ElasticsearchPluginApi()
        self.INFLUXDB_GRAFANA = influx_api.InfluxdbPluginApi()
        self.LMA_COLLECTOR = collector_api.LMACollectorPluginApi()
        self.LMA_INFRASTRUCTURE_ALERTING = \
            infrastructure_alerting_api.InfraAlertingPluginApi()
        self.load = load.LoadGenerator()
        self._plugins = {
            self.ELASTICSEARCH_KIBANA,
            self.INFLUXDB_GRAFANA,
            self.LMA_COLLECTOR,
            self.LMA_INFRASTRUCTURE_ALERTING
        }
        self._disabled_plugins = set()

    def __getattr__(self, item):
        return getattr(self.test, item)

    def disable_plugin(self, plugin):
        """Disable a plugin."""
        self._disabled_plugins.add(plugin)

    def enable_plugin(self, plugin):
        """Enable a plugin."""
        self._disabled_plugins.remove(plugin)

    def call_plugin_method(self, plugin, f):
        """Call a method on a plugin but only if it's enabled."""
        if plugin in self.plugins:
            return f(plugin)

    @property
    def plugins(self):
        """Return the list of plugins that are enabled."""
        return list(self._plugins - self._disabled_plugins)

    def prepare_plugins(self):
        """Upload and install the plugins."""
        for plugin in self.plugins:
            plugin.prepare_plugin()

    def activate_plugins(self):
        """Enable and configure the plugins for the environment."""
        for plugin in self.plugins:
            logger.info("Activate plugin {}".format(
                plugin.get_plugin_settings().name))
            plugin.activate_plugin(
                options=plugin.get_plugin_settings().toolchain_options)

    def check_plugins_online(self):
        for plugin in self.plugins:
            logger.info("Checking plugin {}".format(
                plugin.get_plugin_settings().name))
            plugin.check_plugin_online()

    def check_nodes_count(self, count, hostname, state):
        """Check that all nodes are present in the different backends."""
        self.call_plugin_method(
            self.ELASTICSEARCH_KIBANA,
            lambda x: x.check_elasticsearch_nodes_count(count))
        self.call_plugin_method(
            self.INFLUXDB_GRAFANA,
            lambda x: x.check_influxdb_nodes_count(count))
        self.call_plugin_method(
            self.LMA_INFRASTRUCTURE_ALERTING,
            lambda x: x.check_node_in_nagios(hostname, state))

    def uninstall_plugins(self):
        """Uninstall the plugins from the environment."""
        for plugin in self.plugins:
            plugin.uninstall_plugin()

    def check_uninstall_failure(self):
        for plugin in self.plugins:
            plugin.check_uninstall_failure()

    def get_pids_of_services(self):
        """Check that all nodes run the required LMA collector services."""
        return self.LMA_COLLECTOR.verify_services()

    @staticmethod
    def get_network_template(template_name):
        template_path = os.path.join("network_templates",
                                     "{}.yaml".format(template_name))
        with open(helpers.get_fixture(template_path)) as f:
            return yaml.load(f)

    def check_nova_metrics(self):
        time_started = "{}s".format(int(time.time()))
        plugin = self.INFLUXDB_GRAFANA
        metrics = plugin.get_nova_instance_creation_time_metrics(time_started)
        asserts.assert_equal(
            metrics, [],
            "Spawned instances was found in Nova metrics "
            "before instance creation")

        test_name_pref = (
            'fuel_health.tests.smoke.'
            'test_nova_create_instance_with_connectivity.TestNovaNetwork.')
        instance_tests = (
            '{}test_004_create_servers'.format(test_name_pref),
            '{}test_009_create_server_with_file'.format(test_name_pref))
        for test_name in instance_tests:
            self.helpers.run_single_ostf(test_sets=['smoke'],
                                         test_name=test_name)

        updated_metrics = plugin.get_nova_instance_creation_time_metrics(
            time_started)

        asserts.assert_equal(
            len(updated_metrics), len(instance_tests),
            "There is a mismatch of created instances in Nova metrics, "
            "found {instances_found} instead of {tests_started}".format(
                instances_found=len(updated_metrics),
                tests_started=len(instance_tests))
        )

    def check_nova_logs(self):
        indices = self.ELASTICSEARCH_KIBANA.get_current_indices('log')
        logger.info("Found indexes {}".format(indices))
        output = self.ELASTICSEARCH_KIBANA.query_nova_logs(indices)
        msg = "Indexes {} don't contain Nova logs"
        asserts.assert_not_equal(output['hits']['total'], 0, msg.format(
            indices))
        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])
        computes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["compute"])
        target_nodes = controllers + computes
        expected_hostnames = set([node["hostname"] for node in target_nodes])
        actual_hostnames = set([hit['_source']['Hostname']
                                for hit in output['hits']['hits']])
        asserts.assert_equal(expected_hostnames, actual_hostnames)

    def restart_services_actions(self, queue, cluster_id):
        fuel_web = self.helpers.fuel_web
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

            self.helpers.move_resource(nailgun_controllers[0],
                                       "vip__management",
                                       nailgun_controllers[0])
            self.monitoring_check()
            logger.info("Waiting for 1 hour")
            time.sleep(3600)
            logger.info("Moving vip__management service to another node")
            self.helpers.move_resource(nailgun_controllers[1],
                                       "vip__management",
                                       nailgun_controllers[1])
            self.monitoring_check()

            nailgun_controllers = (
                fuel_web.get_nailgun_cluster_nodes_by_roles(cluster_id,
                                                            ['controller']))

            logger.info("Checking PID of hekad and collectd on all nodes.")
            pids = self.helpers.get_tasks_pids(['hekad', 'collectd'])

            self.manage_lma_collector(nailgun_controllers)
            self.monitoring_check()

            nailgun_compute = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, ['compute'])
            nailgun_plugins = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, self.settings.stacklight_roles)

            logger.info("Restarting lma_collector on all nodes except"
                        " controllers.")
            self.change_lma_collectors_state(
                nailgun_compute, nailgun_plugins, "restart")
            logger.info("Checking PID of hekad on all nodes")
            new_pids = self.helpers.get_tasks_pids(['hekad'])

            for node in new_pids:
                asserts.assert_true(
                    new_pids[node]["hekad"] != pids[node]["hekad"],
                    "hekad on {0} hasn't changed it's pid! Was {1} now "
                    "{2}".format(node, pids[node]["hekad"],
                                 new_pids[node]["hekad"]))
            self.monitoring_check()

            logger.info("Stopping lma_collector on all nodes except"
                        " controllers.")
            self.change_lma_collectors_state(
                nailgun_compute, nailgun_plugins, "stop")
            logger.info("Checking PID of hekad on all nodes except"
                        " controllers")
            self.helpers.get_tasks_pids(['hekad'], nailgun_compute, 1)
            self.helpers.get_tasks_pids(['hekad'], nailgun_plugins, 1)
            logger.info("Starting lma_collector on all nodes except"
                        " controllers.")
            self.change_lma_collectors_state(
                nailgun_compute, nailgun_plugins, "start")
            self.monitoring_check()

            self.killing_heka_on_controllers(nailgun_controllers)

            queue.put(True)
        except Exception as ex:
            logger.error(ex)
            logger.error(traceback.format_exc())
            queue.put(False)
            queue.put(os.getpid())

    def monitoring_check(self):
        logger.info("Checking that lma_collector (heka) sending data to"
                    " Elasticsearch, InfluxDB, Nagios.")
        self.ELASTICSEARCH_KIBANA.elasticsearch_monitoring_check()
        self.INFLUXDB_GRAFANA.influxdb_monitoring_check()
        self.LMA_INFRASTRUCTURE_ALERTING.lma_infrastructure_alerting_check()

    def manage_lma_collector(self, nailgun_controllers):
        logger.info("Stopping lma_collector (heka).")
        self.helpers.manage_pcs_resource(nailgun_controllers,
                                         "lma_collector", "disable",
                                         "Stopped")
        logger.info("Checking PID of hekad on all controllers.")
        self.helpers.get_tasks_pids(['hekad'],
                                    nailgun_controllers, 1)
        logger.info("Starting lma_collector (heka)")
        self.helpers.manage_pcs_resource(nailgun_controllers,
                                         "lma_collector", "enable",
                                         "Started")

    def change_lma_collectors_state(self, nailgun_compute, nailgun_plugins,
                                    action):
        self.LMA_COLLECTOR.manage_lma_collector_service(
            nailgun_compute, action)
        self.LMA_COLLECTOR.manage_lma_collector_service(
            nailgun_plugins, action)

    def killing_heka_on_controllers(self, nailgun_controllers):
        msg = "hekad has not been restarted by pacemaker on node {0} after" \
              " kill -9"
        for node in nailgun_controllers:
            with self.helpers.fuel_web.get_ssh_for_nailgun_node(node) \
                    as remote:
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

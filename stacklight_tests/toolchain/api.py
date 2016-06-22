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
        output = self.ELASTICSEARCH_KIBANA.query_elasticsearch(
            index_type="log", query_filter="programname:nova*")
        asserts.assert_not_equal(output['hits']['total'], 0,
                                 "Indexes don't contain Nova logs")
        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["controller"])
        computes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ["compute"])
        target_nodes = controllers + computes
        expected_hostnames = set([node["hostname"] for node in target_nodes])
        actual_hostnames = set([hit['_source']['Hostname']
                                for hit in output['hits']['hits']])
        asserts.assert_equal(expected_hostnames, actual_hostnames)

    def check_nova_notifications(self):
        nova_event_types = [
            "compute.instance.create.start", "compute.instance.create.end",
            "compute.instance.delete.start", "compute.instance.delete.end",
            "compute.instance.rebuild.start", "compute.instance.rebuild.end",
            "compute.instance.rebuild.scheduled",
            "compute.instance.resize.prep.start",
            "compute.instance.resize.prep.end",
            "compute.instance.resize.confirm.start",
            "compute.instance.resize.confirm.end",
            "compute.instance.resize.revert.start",
            "compute.instance.resize.revert.end",
            "compute.instance.exists", "compute.instance.update",
            "compute.instance.shutdown.start", "compute.instance.shutdown.end",
            "compute.instance.power_off.start",
            "compute.instance.power_off.end",
            "compute.instance.power_on.start", "compute.instance.power_on.end",
            "compute.instance.snapshot.start", "compute.instance.snapshot.end",
            "compute.instance.resize.start", "compute.instance.resize.end",
            "compute.instance.finish_resize.start",
            "compute.instance.finish_resize.end",
            "compute.instance.suspend.start", "compute.instance.suspend.end",
            "scheduler.select_destinations.start",
            "scheduler.select_destinations.end"]
        instance_event_types = nova_event_types[:-2]
        instance_id = self.ELASTICSEARCH_KIBANA.make_instance_actions()
        output_for_instance_id = self.ELASTICSEARCH_KIBANA.query_elasticsearch(
            index_type="notification",
            query_filter='instance_id:"{}"'.format(instance_id), size=500)
        instance_id_notifications = list(set(
            [hit["_source"]["event_type"]
             for hit in output_for_instance_id["hits"]["hits"]]))
        self.helpers.check_notifications(instance_id_notifications,
                                         instance_event_types)
        output_for_logger = self.ELASTICSEARCH_KIBANA.query_elasticsearch(
            index_type="notification", query_filter="Logger:nova", size=500)
        logger_notifications = list(set(
            [hit["_source"]["event_type"]
             for hit in output_for_logger["hits"]["hits"]]))
        self.helpers.check_notifications(logger_notifications,
                                         nova_event_types)

    def check_glance_notifications(self):
        glance_event_types = ["image.create", "image.prepare", "image.upload",
                              "image.activate", "image.update", "image.delete"]
        self.helpers.run_single_ostf(
            test_sets=['smoke'],
            test_name='fuel_health.tests.smoke.test_create_images.'
                      'GlanceSmokeTests.test_create_and_delete_image_v2')
        output = self.ELASTICSEARCH_KIBANA.query_elasticsearch(
            index_type="notification", query_filter="Logger:glance", size=500)
        notification_list = list(set([hit["_source"]["event_type"]
                                      for hit in output["hits"]["hits"]]))
        self.helpers.check_notifications(notification_list,
                                         glance_event_types)

    def check_keystone_notifications(self):
        keystone_event_types = [
            "identity.role.created", "identity.role.deleted",
            "identity.user.created", "identity.user.deleted",
            "identity.project.created", "identity.project.deleted",
            "identity.authenticate"
        ]
        self.helpers.run_single_ostf(
            test_sets=['smoke'],
            test_name='fuel_health.tests.smoke.test_user_create.'
                      'TestUserTenantRole.test_create_user')
        output = self.ELASTICSEARCH_KIBANA.query_elasticsearch(
            index_type="notification",
            query_filter="Logger:keystone", size=500)
        notification_list = list(set(
            [hit["_source"]["event_type"] for hit in output["hits"]["hits"]]))
        self.helpers.check_notifications(notification_list,
                                         keystone_event_types)

    def check_heat_notifications(self):
        heat_event_types = [
            "orchestration.stack.check.start",
            "orchestration.stack.check.end",
            "orchestration.stack.create.start",
            "orchestration.stack.create.end",
            "orchestration.stack.delete.start",
            "orchestration.stack.delete.end",
            "orchestration.stack.resume.start",
            "orchestration.stack.resume.end",
            "orchestration.stack.rollback.start",
            "orchestration.stack.rollback.end",
            "orchestration.stack.suspend.start",
            "orchestration.stack.suspend.end"
        ]
        test_class_main = ('fuel_health.tests.tests_platform.test_heat.'
                           'HeatSmokeTests')

        test_names = ['test_actions', 'test_advanced_actions', 'test_rollback']

        test_classes = []

        for test_name in test_names:
            test_classes.append('{0}.{1}'.format(test_class_main, test_name))

        for test_name in test_classes:
            self.helpers.run_single_ostf(
                test_sets=['smoke'], test_name=test_name)
        output = self.ELASTICSEARCH_KIBANA.query_elasticsearch(
            index_type="notification", query_filter="Logger:heat", size=500)
        notification_list = list(set(
            [hit["_source"]["event_type"] for hit in output["hits"]["hits"]]))
        self.helpers.check_notifications(notification_list, heat_event_types)

    def check_neutron_notifications(self):
        neutron_event_types = [
            "subnet.delete.start", "subnet.delete.end",
            "subnet.create.start", "subnet.create.end",
            "security_group_rule.create.start",
            "security_group_rule.create.end",
            "security_group.delete.start", "security_group.delete.end",
            "security_group.create.start", "security_group.create.end",
            "router.update.start", "router.update.end",
            "router.interface.delete", "router.interface.create",
            "router.delete.start", "router.delete.end",
            "router.create.start", "router.create.end",
            "port.delete.start", "port.delete.end",
            "port.create.start", "port.create.end",
            "network.delete.start", "network.delete.end",
            "network.create.start", "network.create.end",
            "floatingip.update.start", "floatingip.update.end",
            "floatingip.delete.start", "floatingip.delete.end",
            "floatingip.create.start", "floatingip.create.end"
        ]
        self.helpers.run_single_ostf(
            test_sets=['smoke'],
            test_name='fuel_health.tests.smoke.test_neutron_actions.'
                      'TestNeutron.test_check_neutron_objects_creation')
        output = self.ELASTICSEARCH_KIBANA.query_elasticsearch(
            index_type="notification",
            query_filter="Logger:neutron", size=500)
        notification_list = list(set(
            [hit["_source"]["event_type"] for hit in output["hits"]["hits"]]))
        self.helpers.check_notifications(notification_list,
                                         neutron_event_types)

    def check_cinder_notifications(self):
        cinder_event_types = ["volume.update.start", "volume.update.end"]
        volume_id = self.ELASTICSEARCH_KIBANA.make_volume_actions()
        output = self.ELASTICSEARCH_KIBANA.query_elasticsearch(
            index_type="notification",
            query_filter='volume_id:"{}"'.format(volume_id), size=500)
        notification_list = list(set([hit["_source"]["event_type"]
                                      for hit in output["hits"]["hits"]]))
        self.helpers.check_notifications(notification_list,
                                         cinder_event_types)

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

            self.helpers.pcmk_move_resource("vip__management",
                                            nailgun_controllers[0])
            self.monitoring_check()
            logger.info("Waiting for 1 hour")
            # time.sleep(3600)
            logger.info("Moving vip__management service to another node")
            self.helpers.pcmk_move_resource("vip__management",
                                            nailgun_controllers[1])
            self.monitoring_check()

            nailgun_controllers = (
                fuel_web.get_nailgun_cluster_nodes_by_roles(cluster_id,
                                                            ['controller']))

            logger.info("Checking PIDs of hekad and collectd on all nodes.")
            pids = self.helpers.get_tasks_pids(['hekad', 'collectd'])

            self.manage_lma_collector(nailgun_controllers)
            self.monitoring_check()

            nailgun_compute = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, ['compute'])
            nailgun_plugins = fuel_web.get_nailgun_cluster_nodes_by_roles(
                cluster_id, self.settings.stacklight_roles)

            logger.info("Restarting collectors on all nodes except"
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
        self.ELASTICSEARCH_KIBANA.check_nodes_in_elasticsearch()
        self.INFLUXDB_GRAFANA.get_metrics_per_node()
        self.LMA_INFRASTRUCTURE_ALERTING.lma_infrastructure_alerting_check()

    def manage_lma_collector(self, nailgun_controllers):
        if self.LMA_COLLECTOR.settings.version == "0.9.0":
            collector_processes = ["lma_collector"]
        else:
            collector_processes = ["metric_collector", "log_collector"]

        logger.info("Stopping lma_collector (heka).")
        self.helpers.pcmk_manage_pcs_resource(nailgun_controllers,
                                              collector_processes, "disable",
                                              "Stopped")
        logger.info("Checking PID of hekad on all controllers.")
        self.helpers.get_tasks_pids(['hekad'],
                                    nailgun_controllers, 1)
        logger.info("Starting lma_collector (heka)")
        self.helpers.pcmk_manage_pcs_resource(nailgun_controllers,
                                              collector_processes, "enable",
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

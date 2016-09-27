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
from stacklight_tests.kafka import api as kafka_api
from stacklight_tests.lma_collector import api as collector_api
from stacklight_tests.lma_infrastructure_alerting import (
    api as infrastructure_alerting_api)
from stacklight_tests.openstack_telemetry import api as telemetry_api
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
        self.KAFKA = kafka_api.KafkaPluginApi()
        self.LMA_COLLECTOR = collector_api.LMACollectorPluginApi()
        self.LMA_INFRASTRUCTURE_ALERTING = (
            infrastructure_alerting_api.InfraAlertingPluginApi())
        self.OPENSTACK_TELEMETRY = telemetry_api.OpenstackTelemeteryPluginApi()
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

    def add_plugin(self, plugin):
        self._plugins.add(plugin)

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
                test_sets=['tests_platform'], test_name=test_name)
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

    def check_alarms(self, alarm_type, filter_value, source, hostname, value,
                     time_interval="now() - 5m"):
        filter_by = "node_role"
        if alarm_type == "service":
            filter_by = "service"
        filters = [
            "time >= {}".format(time_interval),
            "source = '{}'".format(source),
            "{} = '{}'".format(filter_by, filter_value),
            "value = {}".format(value)
        ]
        if hostname is not None:
            filters.append("hostname = '{}'".format(hostname))

        query = "select last(value) from {select_from} where {filters}".format(
                select_from="{}_status".format(alarm_type),
                filters=" and ".join(filters))
        logger.info("InfluxDB query: {}".format(query))

        def check_result():
            result = self.INFLUXDB_GRAFANA.do_influxdb_query(
                query=query).json()["results"][0]
            return len(result)

        msg = ("Alarm of type: {}: entity: {}, source:{}, hostname: {}, "
               "value: {} wasn't triggered".format(alarm_type, filter_value,
                                                   source, hostname, value))
        devops_helpers.wait(check_result, timeout=60 * 5,
                            interval=10, timeout_msg=msg)

    def get_rabbitmq_memory_usage(self, interval="now() - 5m"):
        query = ("select last(value) from rabbitmq_used_memory "
                 "where time >= {interval}".format(interval=interval))
        result = self.INFLUXDB_GRAFANA.do_influxdb_query(query=query).json()
        return result["results"][0]["series"][0]["values"][0][1]

    def set_rabbitmq_memory_watermark(self, controller, limit, timeout=5 * 60):
        def check_result():
            with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
                exec_res = remote.execute(
                    "rabbitmqctl set_vm_memory_high_watermark {}".format(
                        limit))
                if exec_res['exit_code'] == 0:
                    return True
                else:
                    return False
        msg = "Failed to set vm_memory_high_watermark to {}".format(limit)
        devops_helpers.wait(check_result, timeout=timeout,
                            interval=10, timeout_msg=msg)

    def change_verify_service_state(self, service_name, action, new_state,
                                    service_state_in_influx,
                                    down_backends_in_haproxy, toolchain_node,
                                    controller_nodes, nagios_driver):
        """Verify that the alerts for services show up in the Grafana
            and Nagios UI.

        :param service_name: name of the service to change state of.
            Format [service name, service name
            on dashboard] e.g. ['nova-api', 'nova']
        :type service_name: list.
        :param action: action to perform (e.g. stop, start).
        :type action: str
        :param new_state: new state of the service.
        :type new_state: str
        :param service_state_in_influx: new state of the service in influx.
        :type new_state: int
        :param down_backends_in_haproxy: amout of backends in 'down' state.
        :type down_backends_in_haproxy: int
        :param toolchain_node: toolchain node with
            infrastructure_alerting_ui vip.
        :type toolchain_node: dict
        :param controller_nodes: list of the controller nodes to change
            service state on.
        :type controller_nodes: list
        :param nagios_driver: selenium web driver
            service state on.
        :type nagios_driver: WebDriver
        """

        logger.info("Changing state of service {0}. "
                    "New state is {1}".format(service_name[0], new_state))
        with self.fuel_web.get_ssh_for_nailgun_node(toolchain_node) as remote:
            self.remote_ops.clear_local_mail(remote)
        for node in controller_nodes:
            with self.helpers.fuel_web.get_ssh_for_nailgun_node(
                    node) as remote:
                self.remote_ops.manage_service(remote, service_name[0], action)
        self.LMA_INFRASTRUCTURE_ALERTING.wait_service_state_on_nagios(
            nagios_driver, {service_name[1]: new_state})
        self.INFLUXDB_GRAFANA.check_cluster_status(
            service_name[1], service_state_in_influx)
        self.INFLUXDB_GRAFANA.check_count_of_haproxy_backends(
            service_name[0], expected_count=down_backends_in_haproxy)
        with self.helpers.fuel_web.get_ssh_for_nailgun_node(
                toolchain_node) as remote:
            self.checkers.check_local_mail(
                remote, toolchain_node["name"], service_name[1], new_state)

    def change_verify_node_service_state(self, services, state, influx_state,
                                         percent, toolchain_node,
                                         controller_nodes, nagios_driver):
        """Verify that the alerts for nodes show up in the Grafana
            and Nagios UI.

        :param services: list of services to check new status of. Format
            ['mysql', 'mysql-nodes.mysql-fs']
        :type services: list
        :param state: new state of the service.
        :type state: str
        :param influx_state: new influx state.
        :type influx_state: int
        :param percent: amount of space to be filled on a node.
        :type percent: int
        :param toolchain_node: toolchain node with
            infrastructure_alerting_ui vip.
        :type toolchain_node: dict
        :param controller_nodes: list of the controller nodes to change
            service state on.
        :type controller_nodes: list
        :param nagios_driver: selenium web driver
            service state on.
        :type nagios_driver: WebDriver

        """

        with self.fuel_web.get_ssh_for_nailgun_node(toolchain_node) as remote:
            self.remote_ops.clear_local_mail(remote)

        with self.fuel_web.get_ssh_for_nailgun_node(
                controller_nodes[0]) as remote:
            self.remote_ops.fill_up_filesystem(
                remote, "/dev/mapper/mysql-root", percent,
                "/var/lib/mysql/test/bigfile")

        self.LMA_INFRASTRUCTURE_ALERTING.wait_service_state_on_nagios(
            nagios_driver, {services[0]: 'OK'})
        self.LMA_INFRASTRUCTURE_ALERTING.wait_service_state_on_nagios(
            nagios_driver, {services[1]: state},
            [controller_nodes[0]['hostname']])
        self.INFLUXDB_GRAFANA.check_cluster_status(services[0],
                                                   self.settings.OKAY)

        with self.fuel_web.get_ssh_for_nailgun_node(
                controller_nodes[1]) as remote:
            self.remote_ops.fill_up_filesystem(
                remote, "/dev/mapper/mysql-root", percent,
                "/var/lib/mysql/test/bigfile")

        for node in controller_nodes:
            self.LMA_INFRASTRUCTURE_ALERTING.wait_service_state_on_nagios(
                nagios_driver, {services[0]: state})
            self.LMA_INFRASTRUCTURE_ALERTING.wait_service_state_on_nagios(
                nagios_driver, {services[1]: state}, [node['hostname']])
        self.INFLUXDB_GRAFANA.check_cluster_status(services[0], influx_state)

        with self.helpers.fuel_web.get_ssh_for_nailgun_node(
                toolchain_node) as remote:
            self.checkers.check_local_mail(
                remote, toolchain_node["name"], services[0], state)

        for node in controller_nodes:
            with self.fuel_web.get_ssh_for_nailgun_node(node) as remote:
                self.remote_ops.clean_filesystem(remote,
                                                 "/var/lib/mysql/test/bigfile")

        for node in controller_nodes:
            self.LMA_INFRASTRUCTURE_ALERTING.wait_service_state_on_nagios(
                nagios_driver, {services[0]: 'OK'})
            self.LMA_INFRASTRUCTURE_ALERTING.wait_service_state_on_nagios(
                nagios_driver, {services[1]: 'OK'}, [node['hostname']])
        self.INFLUXDB_GRAFANA.check_cluster_status(services[0],
                                                   self.settings.OKAY)

        with self.helpers.fuel_web.get_ssh_for_nailgun_node(
                toolchain_node) as remote:
            self.checkers.check_local_mail(
                remote, toolchain_node["name"], services[0], 'OK')

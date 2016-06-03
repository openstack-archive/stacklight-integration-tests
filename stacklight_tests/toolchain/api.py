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

import time

from fuelweb_test import logger
from fuelweb_test.tests import base_test_case
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


class ToolchainApi(object):
    def __init__(self):
        self.test = base_test_case.TestBasic()
        self.env = self.test.env
        self.settings = toolchain_settings
        self.helpers = helpers.PluginHelper(self.env)
        self.checkers = checkers
        self.remote_ops = remote_ops
        self.ui_tester = ui_tester
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

    def check_nova_metrics(self):
        time_started = "{}s".format(int(time.time()))
        metrics = self.plugins_mapping[
            "influxdb_grafana"].get_nova_instance_creation_time_metrics(
                time_started)
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

        updated_metrics = self.plugins_mapping[
            "influxdb_grafana"].get_nova_instance_creation_time_metrics(
                time_started)

        asserts.assert_equal(
            len(updated_metrics), len(instance_tests),
            "There is a mismatch of created instances in Nova metrics, "
            "found {instances_found} instead of {tests_started}".format(
                instances_found=len(updated_metrics),
                tests_started=len(instance_tests))
        )

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

from fuelweb_test import logger
from fuelweb_test.tests import base_test_case
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
    # NOTE: the values here must match with the order in which the plugins are
    # listed in self._plugins
    ELASTICSEARCH_KIBANA = 0
    INFLUXDB_GRAFANA = 1
    LMA_COLLECTOR = 2
    LMA_INFRASTRUCTURE_ALERTING = 3

    def __init__(self):
        self.test = base_test_case.TestBasic()
        self.env = self.test.env
        self.settings = toolchain_settings
        self.helpers = helpers.PluginHelper(self.env)
        self.checkers = checkers
        self.remote_ops = remote_ops
        self.ui_tester = ui_tester
        self._plugins = [
            # ELASTICSEARCH_KIBANA
            elasticsearch_api.ElasticsearchPluginApi(),
            # INFLUXDB_GRAFANA
            influx_api.InfluxdbPluginApi(),
            # LMA_COLLECTOR
            collector_api.LMACollectorPluginApi(),
            # LMA_INFRASTRUCTURE_ALERTING
            infrastructure_alerting_api.InfraAlertingPluginApi()
        ]
        self._all_plugins = set([
            self.ELASTICSEARCH_KIBANA,
            self.INFLUXDB_GRAFANA,
            self.LMA_COLLECTOR,
            self.LMA_INFRASTRUCTURE_ALERTING
        ])
        self._disabled_plugins = set()

    def __getattr__(self, item):
        return getattr(self.test, item)

    def disable_plugin_by_id(self, plugin_id):
        """Disable a plugin."""
        self._disabled_plugins.add(plugin_id)

    def enable_plugin_by_id(self, plugin_id):
        """Enable a plugin."""
        self._disabled_plugins.remove(plugin_id)

    def get_plugin_by_id(self, plugin_id):
        """Return the plugin instance.

        The method returns None if the plugin doesn't exist or is disabled.
        """
        if plugin_id not in self._disabled_plugins:
            return self._plugins[plugin_id]
        else:
            return None

    def call_plugin_method(self, plugin_id, f):
        """Call a method on a plugin but only if it's enabled."""
        plugin = self.get_plugin_by_id(plugin_id)
        if plugin:
            return f(plugin)

    @property
    def plugins(self):
        """Return the list of plugins that are enabled."""
        return [self._plugins[i]
                for i in self._all_plugins - self._disabled_plugins]

    def prepare_plugins(self):
        """Upoad and install the plugins."""
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
        return self.call_plugin_method(
            self.LMA_COLLECTOR,
            lambda x: x.verify_services())

    @staticmethod
    def get_network_template(template_name):
        template_path = os.path.join("network_templates",
                                     "{}.yaml".format(template_name))
        with open(helpers.get_fixture(template_path)) as f:
            return yaml.load(f)

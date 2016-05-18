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
from fuelweb_test import logger
from fuelweb_test.tests import base_test_case

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

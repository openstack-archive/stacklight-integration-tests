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

from stacklight_tests import base_test
from stacklight_tests.lma_collector import plugin_settings


class LMACollectorPluginApi(base_test.PluginApi):
    def get_plugin_settings(self):
        return plugin_settings

    def prepare_plugin(self):
        self.helpers.prepare_plugin(self.settings.plugin_path)

    def activate_plugin(self, options=None):
        if options is None:
            options = self.settings.default_options
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, options)

    def get_plugin_vip(self):
        pass

    def check_plugin_online(self):
        # Run OSTF test to check pacemaker status
        self.helpers.run_single_ostf(
            test_sets=['ha'],
            test_name='fuel_health.tests.ha.test_pacemaker_status.'
                      'TestPacemakerStatus.test_check_pacemaker_resources')

        # Check that heka and collectd processes are started on all nodes
        nodes = self.helpers.get_all_ready_nodes()
        msg = "Check services on the {} node"
        for node in nodes:
            logger.info(msg.format(node['name']))
            _ip = node['ip']
            self.helpers.verify_service(_ip, 'hekad', 2)
            self.helpers.verify_service(_ip, 'collectd -C', 1)

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(self.settings.name,
                                             self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)

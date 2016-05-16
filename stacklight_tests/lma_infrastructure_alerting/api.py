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
from proboscis import asserts

from stacklight_tests import base_test
from stacklight_tests.lma_infrastructure_alerting import(
    plugin_settings as infra_alerting_plugin_settings)


class InfraAlertingPluginApi(base_test.PluginApi):
    def get_plugin_settings(self):
        return infra_alerting_plugin_settings

    def prepare_plugin(self):
        self.helpers.prepare_plugin(self.settings.plugin_path)

    def activate_plugin(self):
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, self.settings.options)

    def get_plugin_vip(self):
        return self.helpers.get_plugin_vip(self.settings.vip_name)

    def check_plugin_online(self):
        lma_alerting_vip = self.get_plugin_vip()

        logger.info("Check that the Nagios server is running")
        self.checkers.check_http_get_response(
            "http://{0}:{1}@{2}:8001".format(
                self.settings.nagios_user, self.settings.nagios_password,
                lma_alerting_vip))

    def get_nagios_main_page(self):
        return self.ui_tester.get_driver("http://{0}:{1}@{2}:8001".format(
            self.settings.nagios_user, self.settings.nagios_password,
            self.get_plugin_vip()), "//frame[2]", "Nagios Core")

    def get_primary_lma_node(self):
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, self.settings.role_name)
        lma_node = self.fuel_web.get_devops_nodes_by_nailgun_nodes(
            nailgun_nodes)[0]
        with self.fuel_web.get_ssh_for_node(lma_node.name) as remote:
            result = remote.execute(
                "crm status | grep vip__infrastructure_alerting_mgmt_vip"
                " | awk '{print $4}'")
            return self.fuel_web.get_devops_node_by_nailgun_fqdn(
                result['stdout'][0].rstrip())

    def check_node_in_nagios(self, changed_node, state):
        driver = self.get_nagios_main_page()

        try:
            driver = self.ui_tester.get_nagios_hosts_page(driver)
            asserts.assert_equal(state, self.ui_tester.node_is_present(
                driver, changed_node), "Failed to find node '{0}' on nagios!"
                .format(changed_node))
        finally:
            driver.close()

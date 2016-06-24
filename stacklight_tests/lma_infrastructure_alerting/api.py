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

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from stacklight_tests import base_test
from stacklight_tests.lma_infrastructure_alerting import(
    plugin_settings as infra_alerting_plugin_settings)


class InfraAlertingPluginApi(base_test.PluginApi):
    def get_plugin_settings(self):
        return infra_alerting_plugin_settings

    def prepare_plugin(self):
        self.helpers.prepare_plugin(self.settings.plugin_path)

    def activate_plugin(self, options=None):
        if options is None:
            options = self.settings.default_options
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, options)

    def get_plugin_vip(self):
        try:
            return self.helpers.get_plugin_vip(
                'infrastructure_alerting_mgmt_vip')
        except Exception:
            return self.helpers.get_plugin_vip(self.settings.vip_name)

    def check_plugin_online(self):
        nagios_url = self.get_nagios_url()
        logger.info("Nagios UI is at {}".format(nagios_url))
        logger.info("Check that the '{}' user is authorized".format(
            self.settings.nagios_user))
        self.checkers.check_http_get_response(
            nagios_url,
            auth=(self.settings.nagios_user, self.settings.nagios_password)
        )
        logger.info("Check that the Nagios UI requires authentication")
        self.checkers.check_http_get_response(
            nagios_url, expected_code=401,
            auth=(self.settings.nagios_user, 'rogue')
        )

    def get_authenticated_nagios_url(self):
        return "http://{0}:{1}@{2}:8001".format(self.settings.nagios_user,
                                                self.settings.nagios_password,
                                                self.get_plugin_vip())

    def get_nagios_url(self):
        return "http://{}:8001/".format(self.get_plugin_vip())

    def open_nagios_page(self, link_text, anchor):
        driver = self.ui_tester.get_driver(self.get_authenticated_nagios_url(),
                                           "//frame[2]", "Nagios Core")
        driver.switch_to.default_content()
        driver.switch_to.frame(driver.find_element_by_name("side"))
        link = driver.find_element_by_link_text(link_text)
        link.click()
        driver.switch_to.default_content()
        driver.switch_to.frame(driver.find_element_by_name("main"))
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, anchor)))
        return driver

    def check_node_in_nagios(self, changed_node, state):
        driver = self.open_nagios_page(
            'Hosts', "//table[@class='headertable']")
        try:
            asserts.assert_equal(state, self.node_is_present(
                driver, changed_node), "Failed to find node '{0}' on nagios!"
                .format(changed_node))
        finally:
            driver.close()

    def node_is_present(self, driver, name):
        table = self.ui_tester.get_table(driver,
                                         "/html/body/div[2]/table/tbody")
        for ind in xrange(2, self.ui_tester.get_table_size(table) + 1):
            node_name = self.ui_tester.get_table_cell(
                table, ind, 1).text.rstrip()
            if name == node_name:
                return True

        return False

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(self.settings.name,
                                             self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)

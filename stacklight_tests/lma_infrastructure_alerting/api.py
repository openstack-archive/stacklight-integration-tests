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

import datetime
import time

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
        return self.helpers.get_plugin_vip(self.settings.vip_name)

    def check_plugin_online(self):
        logger.info("Check that the Nagios server is running")
        self.checkers.check_http_get_response(self.get_nagios_url())

    def get_nagios_url(self):
        return "http://{0}:{1}@{2}:8001".format(self.settings.nagios_user,
                                                self.settings.nagios_password,
                                                self.get_plugin_vip())

    def open_nagios_page(self, driver, link_text, anchor):
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
        with self.ui_tester.ui_driver(
                self.get_nagios_url(), "//frame[2]", "Nagios Core") as driver:
            driver = self.open_nagios_page(
                driver, 'Hosts', "//table[@class='headertable']")
            asserts.assert_equal(state, self.node_is_present(
                driver, changed_node), "Failed to find node '{0}' on nagios!"
                .format(changed_node))

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

    def lma_infrastructure_alerting_check(self, interval=600):
        nailgun_nodes = self.helpers.get_all_ready_nodes()
        with self.ui_tester.ui_driver(
                self.get_nagios_url(), "//frame[2]", "Nagios Core") as driver:
            driver = self.open_nagios_page(
                driver, 'Hosts', "//table[@class='headertable']")
            for node in nailgun_nodes:
                time_before = time.time() - interval
                check = False
                table = self.ui_tester.get_table(
                    driver, "/html/body/div[2]/table/tbody")
                for ind in xrange(2, self.ui_tester.get_table_size(table) + 1):
                    node_name = self.ui_tester.get_table_cell(
                        table, ind, 1).text.rstrip()
                    if node["hostname"] == node_name:
                        check = True
                        state = self.ui_tester.get_table_cell(
                            table, ind, 2).text.rstrip()
                        timestamp = datetime.datetime.strptime(
                            self.ui_tester.get_table_cell(
                                table, ind, 3).text.rstrip(),
                            '%Y-%m-%d %H:%M:%S')
                        asserts.assert_equal(
                            'UP', state, "Node {0} is in wrong state! {1} is"
                                         " not 'UP'".format(node["hostname"],
                                                            state))
                        asserts.assert_true(
                            time.mktime(timestamp.timetuple()) > time_before,
                            "Node {0} check is outdated! Must be {1} secs, now"
                            " {2}".format(node["hostname"], interval,
                                          time.time() -
                                          time.mktime(timestamp.timetuple())))
                        break
                asserts.assert_true(check, "Node {0} was not found in "
                                           "nagios!".format(node["hostname"]))
        # NOTE (vushakov): some services will fall to CRITICAL state during
        #     close to production load. Temporary removing service state check.
        # driver = lma_infra_alerting_plugin.open_nagios_page(
        #     'Services', "//table[@class='headertable']")
        # try:
        #     self.check_service_state_on_nagios(driver)
        # finally:
        #     driver.close()

    def get_services_for_node(self, table, node_name):
        services = {}
        node_start = node_end = ''
        for ind in xrange(2, self.ui_tester.get_table_size(table) + 1):
            if not self.ui_tester.get_table_row(table, ind).text:
                if node_start:
                    node_end = ind
                    break
                else:
                    continue
            if self.ui_tester.get_table_cell(table, ind, 1).text == node_name:
                node_start = ind

        for ind in range(node_start, node_end):
            services[self.ui_tester.get_table_cell(table, ind, 2).text] = \
                self.ui_tester.get_table_cell(table, ind, 3).text
        return services

    def check_service_state_on_nagios(self, driver, service_state=None,
                                      nodes=None):
        table = self.ui_tester.get_table(driver, "/html/body/table[3]/tbody")
        if not nodes:
            nodes = [self.ui_tester.get_table_cell(table, 2, 1).text]
        for node in nodes:
            node_services = self.get_services_for_node(table, node)
            if service_state:
                for service in service_state:
                    asserts.assert_equal(
                        service_state[service], node_services[service],
                        "Wrong service state found on node {0}: expected"
                        " {1} but found {2}".format(nodes,
                                                    service_state[service],
                                                    node_services[service]))
            else:
                for service in node_services:
                    asserts.assert_equal(
                        'OK', node_services[service],
                        "Wrong service state found on node {0}: expected"
                        " OK but found {1}".format(nodes,
                                                   node_services[service]))

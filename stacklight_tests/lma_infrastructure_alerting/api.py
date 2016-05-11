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
import requests
import time

from stacklight_tests import base_test
from stacklight_tests.lma_infrastructure_alerting import plugin_settings\
    as infra_alerting_plugin_settings

from stacklight_tests.influxdb_grafana import plugin_settings\
    as influxdb_plugin_settings
from stacklight_tests.lma_collector import plugin_settings \
    as collector_plugin_settings


class InfraAlertingPluginApi(base_test.PluginApi):
    def get_plugin_settings(self):
        return infra_alerting_plugin_settings

    def prepare_plugin(self, dependencies=False):
        self.helpers.prepare_plugin(self.settings.plugin_path)
        if dependencies:
            self.helpers.prepare_plugin(influxdb_plugin_settings.plugin_path)
            self.helpers.prepare_plugin(collector_plugin_settings.plugin_path)

    def activate_plugin(self, dependencies=False):
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, self.settings.options)
        if dependencies:
            self.helpers.activate_plugin(influxdb_plugin_settings.name,
                                         influxdb_plugin_settings.version,
                                         influxdb_plugin_settings.options)
            self.helpers.activate_plugin(collector_plugin_settings.name,
                                         collector_plugin_settings.version,
                                         collector_plugin_settings.options)

    def get_plugin_vip(self):
        return self.helpers.get_plugin_vip(self.settings.vip_name)

    def check_plugin_online(self):
        lma_alerting_vip = self.get_plugin_vip()

        logger.info("Check that the Nagios server is running")
        self.checkers.check_http_get_response("http://{0}:{1}@{2}:8001".format(
                self.settings.nagios_user, self.settings.nagios_password,
                lma_alerting_vip))

    def get_influxdb_master_node(self):
        influx_master_node = self.helpers.get_master_node_by_role(
            self.settings.role_name)
        return influx_master_node

    def get_alerting_tasks_pids(self):
        c_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller', 'compute'])

        processes = ['heka', 'collectd']
        pids = {}

        for node in c_nodes:
            with self.fuel_web.get_ssh_for_node(node.name) as remote:
                pids[node.name] = {}
                for process in processes:
                    result = remote.execute("ps axf | grep {0} | grep -v grep "
                                            "| awk '{{print $1}}'"
                                            .format(process))
                    pids[node.name][process] = result['stdout'][0].rstrip()

        infra_alerting_node = self.get_devops_master_node_by_role(
            self.settings.role_name)

        pids[infra_alerting_node.name] = {}
        with self.fuel_web.get_ssh_for_node(infra_alerting_node.name) \
                as remote:
            result = remote.execute("ps axf | grep influxdb | grep -v grep |"
                                    " awk '{print $1}'")
            pids[infra_alerting_node.name]['influxdb'] = \
                result['stdout'][0].rstrip()

        return pids

    def check_node_in_nagios(self, changed_node, state):
        driver = self.get_nagios_main_page()

        try:
            driver = self.ui_tester.get_nagios_hosts_page(driver)
            asserts.assert_equal(state, self.ui_tester.node_is_present(
                driver, changed_node), "Failed to find node '{0}' on nagios!"
                                 .format(changed_node))
        finally:
            driver.close()

    def check_service_state_on_nagios(self, service_state, driver,
                                      node_name=None):
        driver = self.ui_tester.get_nagios_services_page(driver)
        table = self.ui_tester.get_table(driver, "/html/body/table[3]/tbody")
        if not node_name:
            node_name = self.ui_tester.get_table_cell(table, 2, 1).text
        node_services = self.ui_tester.get_services_for_node(table, node_name)
        for service in service_state:
            for key in node_services:
                if key == service:
                    asserts.assert_equal(service_state[service],
                                         node_services[key], "Wrong service"
                                         " state found on node {0}: expected"
                                         " {1} but found {2}"
                                         .format(node_name,
                                                 service_state[service],
                                                 node_services[key]))

    def change_verify_service_state(self, service, action, state, lma_node,
                                    service_nodes, driver):
        logger.info("Changing state of service {0}. New state is {1}"
                    .format(service[0], state))
        self.helpers.clear_local_mail(lma_node)
        self.helpers.change_service_state(service, action, service_nodes)
        self.check_service_state_on_nagios({service[1]: state}, driver)
        self.helpers.check_local_mail(lma_node, "{0} is {1}"
                                      .format(service[1], state))

    def change_verify_node_service_state(self, services, state, parameter,
                                         lma_node, service_nodes, driver):
        self.helpers.clear_local_mail(lma_node)

        self.helpers.fill_mysql_space(service_nodes[0], parameter)

        self.check_service_state_on_nagios(
            {services[0]: 'OK', services[1]: state}, driver,
            self.helpers.get_fuel_node_name(service_nodes[0]))

        self.helpers.fill_mysql_space(service_nodes[1], parameter)

        for node in service_nodes:
            self.check_service_state_on_nagios(
                {services[0]: state, services[1]: state}, driver,
                self.helpers.get_fuel_node_name(node))

        self.helpers.check_local_mail(lma_node, "{0} is {1}"
                                      .format(services[0], state))

        self.helpers.clean_mysql_space(service_nodes)

        for node in service_nodes:
            self.check_service_state_on_nagios(
                {services[0]: 'OK', services[1]: 'OK'}, driver,
                self.helpers.get_fuel_node_name(node))

        self.helpers.check_local_mail(lma_node, "{0} is {1}"
                                      .format(services[0], 'OK'))

    def get_nagios_main_page(self):
        return self.ui_tester.get_driver("http://{0}:{1}@{2}:8001".format(
                self.settings.nagios_user, self.settings.nagios_password,
                self.get_plugin_vip()), "//frame[2]", "Nagios Core")

    def get_devops_master_node_by_role(self, node_role):
        node = self.helpers.get_master_node_by_role(node_role)
        return self.fuel_web.get_devops_node_by_nailgun_fqdn(node['fqdn'])

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

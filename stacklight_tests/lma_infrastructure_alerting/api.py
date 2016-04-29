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

from devops.helpers import helpers as devops_helpers
from fuelweb_test import logger
from proboscis import asserts
import requests
import time

from stacklight_tests import base_test
from stacklight_tests.lma_infrastructure_alerting import plugin_settings as infra_alerting_plugin_settings

from stacklight_tests.influxdb_grafana import plugin_settings as influxdb_plugin_settings
from stacklight_tests.lma_collector import plugin_settings as collector_plugin_settings

class NotFound(Exception):
    message = "Not Found."


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
                                         influxdb_plugin_settings.version, influxdb_plugin_settings.options)
            self.helpers.activate_plugin(collector_plugin_settings.name,
                                         collector_plugin_settings.version, collector_plugin_settings.options)

    def get_plugin_vip(self):
        networks = self.fuel_web.client.get_networks(self.helpers.cluster_id)
        return networks.get('infrastructure_alerting')

    def check_plugin_online(self):
        lma_alerting_vip = self.get_plugin_vip()

        logger.info("Check that the Nagios server is running")
        r = requests.get(
            "http://{0}:{1}@{2}:8001".format(
                self.settings.nagios_user, self.settings.nagios_password, lma_alerting_vip))
        msg = "Nagios server responded with {}, expected 200".format(
            r.status_code)
        asserts.assert_equal(r.status_code, 200, msg)

    def add_remove_node(self, node_updates):
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        # remove 1 node with specified role.
        target_node = ''
        for key in node_updates:
            target_node = self.get_fuel_node_name(key)
        self.fuel_web.update_nodes(self.helpers.cluster_id, node_updates, False, True)

        self.fuel_web.deploy_cluster_wait(self.helpers.cluster_id, check_services=False)
        self.check_nagios_online(self.helpers.cluster_id)
        self.fuel_web.run_ostf(cluster_id=self.helpers.cluster_id, should_fail=1)
        self.check_node_in_nagios(self.helpers.cluster_id, target_node, False)

        # add 1 node with specified role.l
        self.fuel_web.update_nodes(self.helpers.cluster_id, node_updates)

        self.fuel_web.deploy_cluster_wait(self.helpers.cluster_id, check_services=False)
        self.check_nagios_online(self.helpers.cluster_id)
        self.fuel_web.run_ostf(cluster_id=self.helpers.cluster_id, should_fail=1)
        for key in node_updates:
            target_node = self.get_fuel_node_name(key)
        self.check_node_in_nagios(self.helpers.cluster_id, target_node, True)

#TODO: Check this method!
    def get_influxdb_master_node(self):
        influx_master_node = self.helpers.get_master_node_by_role(
            [self.settings.role_name])
        return influx_master_node

#TODO: Check this method!
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
                                            "| awk '{{print $1}}'".format(process))
                    pids[node.name][process] = result['stdout'][0].rstrip()

        infra_alerting_node = self.get_devops_master_node_by_role([self.settings.role_name])

        with self.fuel_web.get_ssh_for_node(infra_alerting_node.name) as remote:
            result = remote.execute("ps axf | grep influxdb | grep -v grep | awk '{print $1}'")
            pids[infra_alerting_node.name]['influxdb'] = result['stdout'][0].rstrip()

        return pids

#TODO: HELPERS
    def get_fuel_node_name(self, changed_node):
        with self.env.d_env.get_admin_remote() as remote:
            result = remote.execute("fuel nodes | grep {0} | awk '{{print $1}}'".format(changed_node))
            return 'node-' + result['stdout'][0].rstrip()

    def check_node_in_nagios(self, changed_node, state):
        driver = self.get_nagios_main_page()

        try:
            driver = self.ui_tester.get_hosts_page(driver)
            asserts.assert_equal(state, self.ui_tester.node_is_present(driver, changed_node))
        finally:
            driver.close()

    def check_service_state_on_nagios(self, service_state, driver, node_name=None):
        driver = self.ui_tester.get_services_page(driver)
        table = self.ui_tester.get_table(driver, "/html/body/table[3]/tbody")
        if not node_name:
            node_name = self.ui_tester.get_table_cell(table, 2, 1).text
        node_services = self.ui_tester.get_services_for_node(table, node_name)
        for service in service_state:
            for key in node_services:
                if key == service:
                    asserts.assert_equal(service_state[service], node_services[key])

    def change_verify_service_state(self, service, action, state, lma_node, service_nodes, driver):
        self.helpers.clear_local_mail(lma_node)
        self.helpers.change_service_state(service, action, service_nodes)
        self.check_service_state_on_nagios({service[1]: state}, driver)
        self.helpers.check_local_mail(lma_node, "{0} is {1}".format(service[1], state))

    def change_verify_node_service_state(self, services, state, parameter, lma_node, service_nodes, driver):
        self.helpers.clear_local_mail(lma_node)

        self.helpers.fill_mysql_space(service_nodes[0], parameter)

        self.check_service_state_on_nagios({services[0]: 'OK', services[1]: state},
                                           driver, self.get_fuel_node_name(service_nodes[0]))

        self.helpers.fill_mysql_space(service_nodes[1], parameter)

        for node in service_nodes:
            self.check_service_state_on_nagios({services[0]: state, services[1]: state},
                                               driver, self.get_fuel_node_name(node))

        self.helpers.check_local_mail(lma_node, "{0} is {1}".format(services[0], state))

        self.helpers.clean_mysql_space(service_nodes)

        for node in service_nodes:
            self.check_service_state_on_nagios({services[0]: 'OK', services[1]: 'OK'},
                                               driver, self.get_fuel_node_name(node))

        self.helpers.check_local_mail(lma_node, "{0} is {1}".format(services[0], 'OK'))

    def get_nagios_main_page(self):
        return self.ui_tester.get_driver("http://{0}:{1}@{2}:8001".format(
                self.settings.nagios_user, self.setting.nagios_password,
                self.get_alerting_ip(self.helpers.cluster_id)), "//frame[2]", "Nagios Core")

    def get_devops_master_node_by_role(self, node_role):
        node = self.helpers.get_master_node_by_role(node_role)
        return self.fuel_web.get_devops_node_by_nailgun_fqdn(node['fqdn'])

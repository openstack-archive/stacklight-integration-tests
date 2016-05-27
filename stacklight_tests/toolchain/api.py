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
import datetime

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

import time
from datetime import datetime
from datetime import date
from proboscis import asserts

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

    def elasticsearch_monitoring_check(self):
        kibana_url = self.plugins[0].get_kibana_url()
        timestamp = time.time()
        dt = date.today()
        # data = '{{"facets":{{"terms":{{"terms":{{"field":"Hostname","size":10000,"order":"count","exclude":[]}},"facet_filter":{{"fquery":{{"query":{{"filtered":{{"query":{{"bool":{{"should":[{{"query_string":{{"query":"*"}}}}]}}}},"filter":{{"bool":{{"must":[{{"range":{{"Timestamp":{{"from":{0},"to":{1} }}}}}}]}}}}}}}}}}}}}}}},"size": 0}}'.format(timestamp-300, timestamp)
        data = '{{"facets":{{"terms":{{"terms":{{"field":"Hostname",' \
               '"size":10000,"order":"count","exclude":[]}},"facet_filter":' \
               '{{"fquery":{{"query":{{"filtered":{{"query":{{"bool":{{' \
               '"should":[{{"query_string":{{"query":"*"}}}}]}}}},"filter"' \
               ':{{"bool":{{"must":[{{"range":{{"Timestamp":{{"from":{0}' \
               '}}}}}}]}}}}}}}}}}}}}}}},"size": 0}}'.format(timestamp-300)
        url = '{0}/log-{1}/_search?pretty'.format(kibana_url, dt.strftime("%Y.%m.%d"))
        output = self.checkers.check_http_get_response(url=url, data=data)

        self.check_node_in_output(output)

    def influxdb_monitoring_check(self):
        influxdb_pluign = self.plugins[1]
        influxdb_settings = influxdb_pluign.get_plugin_settings()
        output = influxdb_pluign.do_influxdb_query(
            "SELECT last(value), hostname FROM cpu_user WHERE "
            "time > now() - 3m GROUP BY hostname",
            user=influxdb_settings.influxdb_rootuser,
            password=influxdb_settings.influxdb_rootpass)
        self.check_node_in_output(output)

    def lma_infrastructure_alerting_monitoring_check(self):
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, [])
        lma_infra_alerting_plugin = self.plugins[3]
        driver = lma_infra_alerting_plugin.open_nagios_page(
            'Hosts', "//table[@class='headertable']")
        time_difference = 600
        try:
            for node in nailgun_nodes:
                time_before = time.time()-time_difference
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
                        timestamp = datetime.strptime(
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
                            " {2}".format(node["hostname"], time_difference,
                                          time.time() -
                                          time.mktime(timestamp.timetuple())))
                        break
                asserts.assert_true(check, "Node {0} was not found in "
                                           "nagios!".format(node["hostname"]))
        finally:
            driver.close()
        # NOTE (vushakov): some services will fall to CRITICAL state during
        #     close to production load. Temporary removing service state check.
        # driver = lma_infra_alerting_plugin.open_nagios_page(
        #     'Services', "//table[@class='headertable']")
        # try:
        #     self.check_service_state_on_nagios(driver)
        # finally:
        #     driver.close()

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

    def get_services_for_node(self, table, node_name):
        services = {}
        node_start, node_end = '', ''
        for ind in xrange(2, self.ui_tester.get_table_size(table)+1):
            if not self.ui_tester.get_table_row(table, ind).text:
                if node_start:
                    node_end = ind
                    break
                else:
                    continue
            if self.ui_tester.get_table_cell(table, ind, 1).text == node_name:
                node_start = ind

        for ind in xrange(node_start, node_end):
            services[self.ui_tester.get_table_cell(table, ind, 2).text] = \
                self.ui_tester.get_table_cell(table, ind, 3).text
        return services

    def check_node_in_output(self, output):
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, [])
        missing_nodes = []
        for node in nailgun_nodes:
            if '"{0}"'.format(node["hostname"]) not in output.text:
                missing_nodes.append(node["hostname"])
        asserts.assert_false(len(missing_nodes),
                             "Failed to find {0} nodes in the output! Missing"
                             " nodes are: {1}".format(len(missing_nodes),
                                                      missing_nodes))
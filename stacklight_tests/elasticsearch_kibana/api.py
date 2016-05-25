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

from stacklight_tests import base_test
from stacklight_tests.elasticsearch_kibana import plugin_settings


class ElasticsearchPluginApi(base_test.PluginApi):
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
        return self.helpers.get_plugin_vip(self.settings.vip_name)

    def get_elasticsearch_url(self, query=''):
        return "http://{}:9200/{}".format(self.get_plugin_vip(), query)

    def get_kibana_url(self):
        return "http://{}:9200/".format(self.get_plugin_vip())

    def check_plugin_online(self):
        logger.info("Check that Elasticsearch is ready")
        msg = "Elasticsearch responded with {0}, expected {1}"
        self.checkers.check_http_get_response(
            self.get_elasticsearch_url(), msg=msg)

        logger.info("Check that Kibana is running")
        msg = "Kibana responded with {0}, expected {1}"
        self.checkers.check_http_get_response(self.get_kibana_url(), msg=msg)

    def check_elasticsearch_nodes_count(self, expected_count):
        logger.debug("Get information about Elasticsearch nodes")
        url = self.get_elasticsearch_url(query='_nodes')
        response = self.checkers.check_http_get_response(url)
        nodes_count = len(response.json()['nodes'])

        logger.debug("Check that the number of nodes is equal to the expected")
        msg = ("Expected count of elasticsearch nodes {}, "
               "actual count {}".format(expected_count, nodes_count))
        asserts.assert_equal(expected_count, nodes_count, msg)

    def get_elasticsearch_master_node(self, excluded_nodes_fqdns=()):
        elasticsearch_master_node = self.helpers.get_master_node_by_role(
            self.settings.role_name, excluded_nodes_fqdns=excluded_nodes_fqdns)
        return elasticsearch_master_node

    def wait_for_rotation_elasticsearch_master(self, old_master,
                                               timeout=5 * 60):
        logger.info('Wait a influxDB master node rotation')
        msg = "Failed influxDB master rotation from {0}".format(old_master)
        devops_helpers.wait(
            lambda: old_master != self.get_elasticsearch_master_node(
                excluded_nodes_fqdns=(old_master,))['fqdn'],
            timeout=timeout, timeout_msg=msg)

    def wait_plugin_online(self, timeout=5 * 60):
        def check_availability():
            try:
                self.check_plugin_online()
                return True
            except (AssertionError, requests.ConnectionError):
                return False

        logger.info('Wait a plugin become online')
        msg = "Plugin has not become online after waiting period"
        devops_helpers.wait(
            check_availability, timeout=timeout, timeout_msg=msg)

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(
            self.settings.name, self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)

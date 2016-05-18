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
from stacklight_tests.elasticsearch_kibana import plugin_settings


class ElasticsearchPluginApi(base_test.PluginApi):
    def get_plugin_settings(self):
        return plugin_settings

    def prepare_plugin(self):
        self.helpers.prepare_plugin(self.settings.plugin_path)

    def activate_plugin(self, toolchain=False):
        options = (self.settings.toolchain_options if toolchain
                   else self.settings.bvt_options)
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, options)

    def get_plugin_vip(self):
        return self.helpers.get_plugin_vip(self.settings.vip_name)

    def get_elasticsearch_url(self, query=''):
        return "http://{}:9200/{}".format(self.get_plugin_vip(), query)

    def get_kibana_url(self):
        return "http://{}:9200/".format(self.get_plugin_vip())

    def check_plugin_online(self):
        logger.debug("Check that Elasticsearch is ready")
        msg = "Elasticsearch responded with {0}, expected {1}"
        self.checkers.check_http_get_response(
            self.get_elasticsearch_url(), msg=msg)

        logger.debug("Check that Kibana is running")
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

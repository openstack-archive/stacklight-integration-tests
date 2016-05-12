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

    def activate_plugin(self):
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, self.settings.options)

    def get_plugin_vip(self):
        return self.helpers.get_plugin_vip(self.settings.vip_name)

    def make_request_to_elasticsearch(self, params='', expected_code=200):
        msg = "Elasticsearch responded with {0}, expected {1}"
        r = self.checkers.check_http_get_response(
            self.settings.elasticsearch_url.format(
                self.get_plugin_vip(), params),
            expected_code=expected_code, msg=msg)
        return r

    def check_plugin_online(self):
        logger.debug("Check that Elasticsearch is ready")
        self.make_request_to_elasticsearch()

        logger.debug("Check that Kibana is running")
        msg = "Kibana responded with {0}, expected {1}"
        self.checkers.check_http_get_response(
            self.settings.kibana_url.format(self.get_plugin_vip()), msg=msg)

    def check_elasticsearch_nodes_count(self, expected_count):
        response = self.make_request_to_elasticsearch(params='/_nodes')
        nodes_count = len(response.json()['nodes'])
        msg = ("Expected count of elasticsearch nodes {}, "
               "actual count {}".format(expected_count, nodes_count))
        asserts.assert_equal(expected_count, nodes_count, msg)

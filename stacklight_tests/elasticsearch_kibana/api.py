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
import json
import time

# import elasticsearch
from fuelweb_test import logger
from proboscis import asserts

from stacklight_tests import base_test
from stacklight_tests.elasticsearch_kibana import plugin_settings


class ElasticsearchPluginApi(base_test.PluginApi):
    def __init__(self):
        super(ElasticsearchPluginApi, self).__init__()
        self._es_client = None

    @property
    def es(self):
        if self._es_client is None:
            self._es_client = elasticsearch.Elasticsearch(
                [{'host': self.get_plugin_vip(), 'port': 9200}])
        return self._es_client

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
        return "http://{}:80/".format(self.get_plugin_vip())

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

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(
            self.settings.name, self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)

    def get_current_indices(self, index_type):
        indices = self.es.indices.get_aliases().keys()
        return filter(lambda x: index_type in x, sorted(indices))[-2:]

    def query_nova_logs(self, indices):
        query = {"query": {"filtered": {
            "query": {"bool": {"should": [{"query_string": {
                "query": "programname:nova*"}}]}},
            "filter": {"bool": {"must": [{"range": {"Timestamp": {
                "from": "now-1h"}}}]}}}}, "size": 100}
        output = self.es.search(index=indices, body=query)
        return output

    def elasticsearch_monitoring_check(self, interval=300 * 1000):
        timestamp = int(round(time.time() * 1000)) - interval
        dt = datetime.datetime.fromtimestamp(timestamp / 1000)
        elasticsearch_url = self.get_elasticsearch_url()
        data = self.get_elasticsearch_json(timestamp - interval)

        url = '{0}/log-{1}/_search?pretty'.format(elasticsearch_url,
                                                  dt.strftime("%Y.%m.%d"))
        output = self.checkers.check_http_get_response(url=url,
                                                       data=json.dumps(data))
        lines = json.loads(output.text)
        nodes = [line["term"] for line in lines["facets"]["terms"]["terms"]]
        self.helpers.check_node_in_output(nodes)

    def get_elasticsearch_json(self, timestamp):
        return {"facets": {
            "terms": {"terms": {"field": "Hostname", "size": 10000, "order":
                                "count", "exclude": []}, "facet_filter": {
                "fquery": {"query": {"filtered": {"query": {"bool": {
                    "should": [{"query_string": {"query": "*"}}]}}, "filter": {
                    "bool": {"must": [{"range": {"Timestamp": {
                        "from": timestamp}}}]}}}}}}}}, "size": 0}

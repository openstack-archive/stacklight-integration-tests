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

import elasticsearch
from fuelweb_test.helpers import os_actions
from fuelweb_test import logger
from proboscis import asserts

from stacklight_tests import base_test
from stacklight_tests.elasticsearch_kibana import plugin_settings


class ElasticsearchPluginApi(base_test.PluginApi):
    def __init__(self):
        super(ElasticsearchPluginApi, self).__init__()
        self.es = elasticsearch.Elasticsearch([{'host': self.get_plugin_vip(),
                                                'port': 9200}])
        self.os_conn = os_actions.OpenStackActions(
            self.fuel_web.get_public_vip(self.helpers.cluster_id))
        self.nova = self.os_conn.nova

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

    def do_elasticsearch_query(self, indices, query):
        return self.es.search(index=indices, body=query)

    @staticmethod
    def make_query_for_notifications(query_string):
        query = {"query": {"filtered": {
            "query": {"bool": {"should": {"query_string": {
                "query": ""}}}},
            "filter": {"bool": {"must": {"range": {"Timestamp": {
                "from": "now-1h"}}}}}}}, "size": 500}
        query["query"]["filtered"]["query"]["bool"]["should"]["query_string"][
            "query"] = query_string
        return query

    def query_nova_notifications(self):
        net_name = self.fuel_web.get_cluster_predefined_networks_name(
            self.helpers.cluster_id)['private_net']
        flavors = self.nova.flavors.list(sort_key="memory_mb")
        logger.info("Launch an instance")
        instance = self.os_conn.create_server_for_migration(label=net_name,
                                                            flavor=flavors[0])
        logger.info("Update the instance")
        self.nova.servers.update(instance, name="test-server")
        self.os_conn.verify_instance_status(instance, "ACTIVE")
        image = self.os_conn._get_cirros_image()
        logger.info("Rebuild the instance")
        self.nova.servers.rebuild(instance, image, name="rebuilded_instance")
        self.os_conn.verify_instance_status(instance, "ACTIVE")
        logger.info("Resize the instance")
        self.nova.servers.resize(instance, flavors[1])
        self.os_conn.verify_instance_status(instance, "VERIFY_RESIZE")
        logger.info("Confirm the resize")
        self.nova.servers.confirm_resize(instance)
        self.os_conn.verify_instance_status(instance, "ACTIVE")
        logger.info("Resize the instance")
        self.nova.servers.resize(instance, flavors[2])
        self.os_conn.verify_instance_status(instance, "VERIFY_RESIZE")
        logger.info("Revert the resize")
        self.nova.servers.revert_resize(instance)
        self.os_conn.verify_instance_status(instance, "ACTIVE")
        logger.info("Stop the instance")
        self.nova.servers.stop(instance)
        self.os_conn.verify_instance_status(instance, "SHUTOFF")
        logger.info("Start the instance")
        self.nova.servers.start(instance)
        self.os_conn.verify_instance_status(instance, "ACTIVE")
        logger.info("Suspend the instance")
        self.nova.servers.suspend(instance)
        self.os_conn.verify_instance_status(instance, "SUSPENDED")
        logger.info("Resume the instance")
        self.nova.servers.resume(instance)
        self.os_conn.verify_instance_status(instance, "ACTIVE")
        logger.info("Create an instance snapshot")
        self.nova.servers.create_image(instance, "test-image")
        self.os_conn.verify_instance_status(instance, "ACTIVE")
        logger.info("Delete the instance")
        self.nova.servers.delete(instance)
        logger.info("Check that the instance is deleted")
        self.os_conn.verify_srv_deleted(instance)
        query = self.make_query_for_notifications("instance_id={}".format(
            instance.id))
        indices = self.get_current_indexes("notification")
        output = self.do_elasticsearch_query(indices, query)
        return list(set([hit["_source"]["event_type"]
                         for hit in output["hits"]["hits"]]))

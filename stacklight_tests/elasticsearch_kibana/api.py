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
from fuelweb_test import logger
from proboscis import asserts

from stacklight_tests import base_test
from stacklight_tests.elasticsearch_kibana.kibana_ui import api as ui_api
from stacklight_tests.elasticsearch_kibana import plugin_settings


class ElasticsearchPluginApi(base_test.PluginApi):
    def __init__(self):
        super(ElasticsearchPluginApi, self).__init__()
        self._es_client = None
        self._kibana_port = None
        self._kibana_protocol = None

    @property
    def es(self):
        if self._es_client is None:
            self._es_client = elasticsearch.Elasticsearch(
                [{'host': self.get_elasticsearch_vip(), 'port': 9200}])
        return self._es_client

    @property
    def kibana_port(self):
        if self._kibana_port is None:
            if self.kibana_protocol == 'http':
                self._kibana_port = 80
            else:
                self._kibana_port = 443
        return self._kibana_port

    @property
    def kibana_protocol(self):
        if self._kibana_protocol is None:
            self._kibana_protocol = self.get_http_protocol()
        return self._kibana_protocol

    def get_plugin_settings(self):
        return plugin_settings

    def prepare_plugin(self):
        self.helpers.prepare_plugin(self.settings.plugin_path)

    def activate_plugin(self, options=None):
        if options is None:
            options = self.settings.default_options
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, options)

    def get_elasticsearch_vip(self):
        return self.helpers.get_vip_address('es_vip_mgmt')

    def get_elasticsearch_url(self, path=''):
        return "http://{}:9200/{}".format(self.get_elasticsearch_vip(), path)

    def get_kibana_vip(self):
        if self.settings.version.startswith("0."):
            # 0.x versions of the plugin uses the same VIP for Elasticsearch
            # and Kibana
            return self.get_elasticsearch_vip()
        else:
            return self.helpers.get_vip_address('kibana')

    def get_kibana_url(self):
        return "{0}://{1}:{2}/".format(
            self.kibana_protocol, self.get_kibana_vip(), self.kibana_port)

    def check_plugin_online(self):
        elasticsearch_url = self.get_elasticsearch_url()
        logger.info("Checking Elasticsearch service at {}".format(
            elasticsearch_url))
        msg = "Elasticsearch responded with {0}, expected {1}"
        self.checkers.check_http_get_response(elasticsearch_url, msg=msg)

        kibana_url = self.get_kibana_url()
        logger.info("Checking Kibana service at {}".format(kibana_url))
        msg = "Kibana responded with {0}, expected {1}"
        self.checkers.check_http_get_response(
            kibana_url, msg=msg,
            auth=(self.settings.kibana_username,
                  self.settings.kibana_password)
        )

    def check_plugin_ldap(self, authz=False):
        """Check dashboard is available when using LDAP for authentication.

        :param authz: adds checking LDAP for authorisation
        :type authz: boolean
        """
        ui_api.check_kibana_ldap(self.get_kibana_url(), authz)

    def check_elasticsearch_nodes_count(self, expected_count):
        logger.debug("Get information about Elasticsearch nodes")
        url = self.get_elasticsearch_url(path='_nodes')
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

    def query_elasticsearch(self, index_type, time_range="now-1h",
                            query_filter="*", size=100):
        all_indices = self.es.indices.get_aliases().keys()
        indices = filter(lambda x: index_type in x, sorted(all_indices))
        return self.es.search(index=indices, body={
            "query": {"filtered": {
                "query": {"bool": {"should": {"query_string": {
                    "query": query_filter}}}},
                "filter": {"bool": {"must": {"range": {
                    "Timestamp": {"from": time_range}}}}}}},
            "size": size})

    def make_instance_actions(self):
        net_name = self.fuel_web.get_cluster_predefined_networks_name(
            self.helpers.cluster_id)['private_net']
        os_conn = self.helpers.os_conn
        flavors = os_conn.nova.flavors.list(sort_key="memory_mb")
        logger.info("Launch an instance")
        instance = os_conn.create_server_for_migration(
            label=net_name, flavor=flavors[0])
        logger.info("Update the instance")
        os_conn.nova.servers.update(instance, name="test-server")
        self.helpers.wait_for_resource_status(
            os_conn.nova.servers, instance, "ACTIVE")
        image = self.helpers.os_conn._get_cirros_image()
        logger.info("Rebuild the instance")
        os_conn.nova.servers.rebuild(
            instance, image, name="rebuilded_instance")
        self.helpers.wait_for_resource_status(
            os_conn.nova.servers, instance, "ACTIVE")
        logger.info("Resize the instance")
        os_conn.nova.servers.resize(instance, flavors[1])
        self.helpers.wait_for_resource_status(
            os_conn.nova.servers, instance, "VERIFY_RESIZE")
        logger.info("Confirm the resize")
        os_conn.nova.servers.confirm_resize(instance)
        self.helpers.wait_for_resource_status(
            os_conn.nova.servers, instance, "ACTIVE")
        logger.info("Resize the instance")
        os_conn.nova.servers.resize(instance, flavors[2])
        self.helpers.wait_for_resource_status(
            os_conn.nova.servers, instance, "VERIFY_RESIZE")
        logger.info("Revert the resize")
        os_conn.nova.servers.revert_resize(instance)
        self.helpers.wait_for_resource_status(
            os_conn.nova.servers, instance, "ACTIVE")
        logger.info("Stop the instance")
        os_conn.nova.servers.stop(instance)
        self.helpers.wait_for_resource_status(
            os_conn.nova.servers, instance, "SHUTOFF")
        logger.info("Start the instance")
        os_conn.nova.servers.start(instance)
        self.helpers.wait_for_resource_status(
            os_conn.nova.servers, instance, "ACTIVE")
        logger.info("Suspend the instance")
        os_conn.nova.servers.suspend(instance)
        self.helpers.wait_for_resource_status(
            os_conn.nova.servers, instance, "SUSPENDED")
        logger.info("Resume the instance")
        os_conn.nova.servers.resume(instance)
        self.helpers.wait_for_resource_status(
            os_conn.nova.servers, instance, "ACTIVE")
        logger.info("Create an instance snapshot")
        snapshot = os_conn.nova.servers.create_image(instance, "test-image")
        self.helpers.wait_for_resource_status(
            os_conn.nova.images, snapshot, "ACTIVE")
        logger.info("Delete the instance")
        os_conn.nova.servers.delete(instance)
        logger.info("Check that the instance was deleted")
        os_conn.verify_srv_deleted(instance)
        return instance.id

    def make_volume_actions(self):
        cinder = self.helpers.os_conn.cinder
        logger.info("Create a volume")
        volume = cinder.volumes.create(size=1)
        self.helpers.wait_for_resource_status(
            cinder.volumes, volume.id, "available")
        logger.info("Update the volume")
        if cinder.version == 1:
            cinder.volumes.update(volume, display_name="updated_volume")
        else:
            cinder.volumes.update(volume, name="updated_volume")
        self.helpers.wait_for_resource_status(
            cinder.volumes, volume.id, "available")
        logger.info("Delete the volume")
        cinder.volumes.delete(volume)
        return volume.id

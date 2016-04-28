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
import os

from devops.helpers import helpers as devops_helpers
from fuelweb_test import logger
from proboscis import asserts
import requests

from stacklight_tests import base_test
from stacklight_tests.influxdb_grafana import plugin_settings
from stacklight_tests import settings


class BaseTestInfluxdbPlugin(base_test.BaseTestStackLightPlugins):
    """Common test class to operate with InfluxDB-Grafana plugin."""
    @property
    def options(self):
        options = {
            'influxdb_rootpass/value': self.settings.influxdb_rootpass,
            'influxdb_username/value': self.settings.influxdb_user,
            'influxdb_userpass/value': self.settings.influxdb_pass,
            'grafana_username/value': self.settings.grafana_user,
            'grafana_userpass/value': self.settings.grafana_pass,
            'mysql_mode/value': self.settings.mysql_mode,
            'mysql_dbname/value': self.settings.mysql_dbname,
            'mysql_username/value': self.settings.mysql_user,
            'mysql_password/value': self.settings.mysql_pass,
        }
        return options

    def get_vip(self, cluster_id):
        return self.helpers.get_plugin_vip(cluster_id, self.settings.vip_name)

    def get_plugin_settings(self):
        return plugin_settings

    def prepare_plugin(self):
        self.env.admin_actions.upload_plugin(
            plugin=settings.INFLUXDB_GRAFANA_PLUGIN_PATH)
        self.env.admin_actions.install_plugin(
            plugin_file_name=os.path.basename(
                settings.INFLUXDB_GRAFANA_PLUGIN_PATH))
        self.helpers.prepare_plugin(self.settings.plugin_path)

    def activate_plugin(self, cluster_id):
        msg = "Plugin couldn't be enabled. Check plugin version. Test aborted"
        asserts.assert_true(
            self.fuel_web.check_plugin_exists(cluster_id, self.settings.name),
            msg)
        self.helpers.activate_plugin(cluster_id, self.settings.name,
                                     self.settings.version, self.options)

    def make_request_to_influx(self, cluster_id,
                               db=plugin_settings.influxdb_db_name,
                               user=plugin_settings.influxdb_rootuser,
                               password=plugin_settings.influxdb_rootpass,
                               query="",
                               expected_code=200):
        influxdb_vip = self.get_vip(cluster_id)
        params = {
            "db": db,
            "u": user,
            "p": password,
            "q": query,
        }
        r = requests.get(self.settings.influxdb_url.format(influxdb_vip),
                         params=params)
        msg = "InfluxDB responded with {0}, expected {1}".format(r.status_code,
                                                                 expected_code)
        asserts.assert_equal(r.status_code, expected_code, msg)
        return r

    def check_plugin_online(self, cluster_id):
        self.make_request_to_influx(cluster_id,
                                    query="show measurements")

        logger.debug("Check that the Grafana server is running")

        r = requests.get(self.settings.grafana_url.format(
            self.settings.grafana_user, self.settings.grafana_pass,
            self.get_vip(cluster_id)))
        msg = "Grafana server responded with {0}, expected {1}".format(
            r.status_code, 200)
        asserts.assert_equal(r.status_code, 200, msg)

    def check_influxdb_nodes_count(self, cluster_id, nodes_count=1):
        response = self.make_request_to_influx(
            cluster_id,
            user=self.settings.influxdb_rootuser,
            password=self.settings.influxdb_rootpass,
            query="show servers")

        nodes_count_responsed = len(
            response.json()["results"][0]["series"][0]["values"])

        msg = "InfluxDB nodes count expected, received instead: {}".format(
            nodes_count_responsed)
        asserts.assert_equal(nodes_count, nodes_count_responsed, msg)

    def get_influxdb_master_node(self, cluster_id):
        influx_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            cluster_id, self.settings._role_name)
        with self.fuel_web.get_ssh_for_nailgun_node(influx_nodes[0]) as remote:
            stdout = remote.check_call(
                'pcs status cluster | grep "Current DC:"')["stdout"][0]
        for influx_node in influx_nodes:
            if influx_node['fqdn'] in stdout:
                return influx_node

    def wait_for_rotation_influx_master(self, cluster_id,
                                        old_master, timeout=5 * 60):
        logger.info('Wait a influxDB master node rotation')
        msg = "Failed influxDB master rotation from {0}".format(old_master)
        devops_helpers.wait(
            lambda: old_master != self.get_influxdb_master_node(
                cluster_id)['fqdn'],
            timeout=timeout, timeout_msg=msg)

    def wait_plugin_online(self, cluster_id, timeout=5 * 60):
        def check_aviability():
            try:
                self.check_plugin_online(cluster_id)
                return True
            except (AssertionError, requests.ConnectionError):
                return False
        logger.info('Wait a plugin become online')
        msg = "Plugin has not become online after waiting period"
        devops_helpers.wait(check_aviability, timeout=timeout, timeout_msg=msg)

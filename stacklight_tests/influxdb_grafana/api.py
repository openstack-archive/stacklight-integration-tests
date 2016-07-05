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

import json

from fuelweb_test import logger
from proboscis import asserts

from stacklight_tests import base_test
from stacklight_tests.influxdb_grafana.grafana_ui import api as ui_api
from stacklight_tests.influxdb_grafana import plugin_settings


class InfluxdbPluginApi(base_test.PluginApi):
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

    def get_grafana_url(self, path=''):
        vip = self.get_plugin_vip()
        port = 80
        if self.check_port(vip, 8000):
            port = 8000
        return "http://{0}:{1}/{2}".format(vip, port, path)

    def get_influxdb_url(self, path=''):
        return "http://{0}:8086/{1}".format(self.get_plugin_vip(), path)

    def do_influxdb_query(self,
                          query,
                          db=plugin_settings.influxdb_db_name,
                          user=plugin_settings.influxdb_user,
                          password=plugin_settings.influxdb_pass,
                          expected_code=200):
        return self.checkers.check_http_get_response(
            url=self.get_influxdb_url('query'),
            expected_code=expected_code,
            params={"db": db, "u": user, "p": password, "q": query})

    def check_plugin_online(self):
        logger.info("InfluxDB service is at {}".format(
            self.get_influxdb_url()))
        logger.info("Check that the InfluxDB server replies to ping requests")
        self.checkers.check_http_get_response(
            url=self.get_influxdb_url('ping'),
            expected_code=204)

        logger.info("Check that the InfluxDB API requires authentication")
        self.do_influxdb_query("show measurements",
                               user=plugin_settings.influxdb_user,
                               password='rogue', expected_code=401)

        logger.info("Check that the InfluxDB user is authorized")
        self.do_influxdb_query("show measurements")

        logger.info("Check that the InfluxDB user doesn't have admin rights")
        self.do_influxdb_query("show servers", expected_code=401)

        logger.info("Check that the InfluxDB root user has admin rights")
        self.do_influxdb_query("show servers",
                               user=plugin_settings.influxdb_rootuser,
                               password=plugin_settings.influxdb_rootpass)

        logger.info("Grafana service is at {}".format(
            self.get_grafana_url()))
        logger.info("Check that the Grafana UI server is running")
        self.checkers.check_http_get_response(
            self.get_grafana_url('login'))

        logger.info("Check that the Grafana admin user is authorized")
        self.checkers.check_http_get_response(
            self.get_grafana_url('api/org'),
            auth=(plugin_settings.grafana_user, plugin_settings.grafana_pass))

        logger.info("Check that the Grafana API requires authentication")
        self.checkers.check_http_get_response(
            self.get_grafana_url('api/org'),
            auth=(plugin_settings.grafana_user, 'rogue'), expected_code=401)

    def check_influxdb_nodes_count(self, count=1):
        logger.debug('Check the number of InfluxDB servers')
        response = self.do_influxdb_query(
            "show servers",
            user=self.settings.influxdb_rootuser,
            password=self.settings.influxdb_rootpass)

        nodes_count_responsed = len(
            response.json()["results"][0]["series"][0]["values"])

        msg = "Expected {0} InfluxDB nodes, got {1}".format(
            count, nodes_count_responsed)
        asserts.assert_equal(count, nodes_count_responsed, msg)

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(self.settings.name,
                                             self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)

    def check_grafana_dashboards(self):
        ui_api.check_grafana_dashboards(self.get_grafana_url())

    def get_nova_instance_creation_time_metrics(self, time_point=None):
        """Gets instance creation metrics for provided interval

        :param time_point: time interval
        :type time_point: str
        :returns: list of metrics
        :rtype: list
        """
        logger.info("Getting Nova instance creation metrics")
        interval = "now() - 1h" if time_point is None else time_point
        query = (
            "select value "
            "from openstack_nova_instance_creation_time "
            "where time >= {interval}".format(interval=interval))
        result = self.do_influxdb_query(query=query)
        result = json.loads(
            result.content)["results"][0]

        if result:
            return result["series"][0]["values"]
        return []

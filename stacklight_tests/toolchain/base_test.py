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

from stacklight_tests import base_test
from stacklight_tests.influxdb_grafana import api as influx_grafana_api


class Collector(base_test.PluginApi):
    def __init__(self):
        super(Collector, self).__init__()
        self.plugins = [influx_grafana_api.InfluxdbPluginApi()]

    def get_plugin_settings(self):
        pass

    def prepare_plugin(self):
        for plugin in self.plugins:
            plugin.prepare_plugin()

    def activate_plugin(self, cluster_id):
        for plugin in self.plugins:
            plugin.activate_plugin(cluster_id)

    def get_plugin_vip(self, cluster_id):
        pass

    def check_plugin_online(self, cluster_id):
        for plugin in self.plugins:
            plugin.check_plugin_online(cluster_id)

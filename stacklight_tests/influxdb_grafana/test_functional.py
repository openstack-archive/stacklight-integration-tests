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

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from proboscis import test

from stacklight_tests.influxdb_grafana import api


@test(groups=["plugins"])
class TestFunctionalInfluxdbPlugin(api.InfluxdbPluginApi):
    """Class for functional testing of plugin."""

    @test(depends_on_groups=["deploy_influxdb_grafana"],
          groups=["check_display_dashboards_influxdb_grafana",
                  "influxdb_grafana", "functional"])
    @log_snapshot_after_test
    def check_display_dashboards_influxdb_grafana(self):
        """Verify that the dashboards show up in the Grafana UI.

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Open the Grafana URL (
                open the "Dashboard" tab and click the "Grafana" link)
            3. Sign-in using the credentials provided
                during the configuration of the environment
            4. Go to the Main dashboard and verify that everything is ok
            5. Repeat the previous step for the following dashboards:
                Apache
                Cinder
                Elasticsearch
                Glance
                HAProxy
                Heat
                Hypervisor
                InfluxDB
                Keystone
                LMA self-monitoring
                Memcached
                MySQL
                Neutron
                Nova
                RabbitMQ
                System

        Duration 40m
        """

        self.env.revert_snapshot("deploy_influxdb_grafana_plugin")

        self.check_plugin_online()

        self.check_grafana_dashboards()

        self.env.make_snapshot("check_display_dashboards_influxdb_grafana")

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

from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestFunctionalToolchain(api.ToolchainApi):
    """Class for functional testing of plugins toolchain."""

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_display_grafana_dashboards_toolchain",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def check_display_grafana_dashboards_toolchain(self):
        """Verify that the dashboards show up in the Grafana UI.

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Open the Grafana URL (
                open the "Dashboard" tab and click the "Grafana" link)
            3. Sign-in using the credentials provided
                during the configuration of the environment
            4. Go to the Main dashboard and verify that everything is ok
            5. Repeat the previous step for the following dashboards:
                * Apache
                * Cinder
                * Elasticsearch
                * Glance
                * HAProxy
                * Heat
                * Hypervisor
                * InfluxDB
                * Keystone
                * LMA self-monitoring
                * Memcached
                * MySQL
                * Neutron
                * Nova
                * RabbitMQ
                * System

        Duration 20m
        """

        self.env.revert_snapshot("deploy_toolchain")

        self.check_plugins_online()

        self.plugins_mapping["influxdb_grafana"].check_grafana_dashboards()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_nova_metrics_toolchain",
                  "toolchain", "functional"])
    @log_snapshot_after_test
    def check_nova_metrics_toolchain(self):
        """Verify that the Nova metrics are collecting.

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Check that plugins are online
            3. Check Nova metrics in InfluxDB during OSTF tests

        Duration 20m
        """

        self.env.revert_snapshot("deploy_toolchain")

        self.check_plugins_online()

        self.plugins_mapping["influxdb_grafana"].check_nova_metrics()

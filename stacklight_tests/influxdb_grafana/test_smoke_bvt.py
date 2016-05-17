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
class TestInfluxdbPlugin(api.InfluxdbPluginApi):
    """Class for smoke testing the InfluxDB-Grafana plugin."""

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["install_influxdb_grafana", "install",
                  "influxdb_grafana", "smoke"])
    @log_snapshot_after_test
    def install_influxdb_grafana(self):
        """Install InfluxDB-Grafana plugin and check it exists

        Scenario:
            1. Upload the InfluxDB/Grafana plugin to the master node
            2. Install the plugin
            3. Create a cluster
            4. Check that the plugin can be enabled

        Duration 20m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.create_cluster()

        self.activate_plugin()

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["deploy_influxdb_grafana", "deploy",
                  "influxdb_grafana", "smoke"])
    @log_snapshot_after_test
    def deploy_influxdb_grafana(self):
        """Deploy a cluster with the InfluxDB-Grafana plugin

        Scenario:
            1. Upload the InfluxDB/Grafana plugin to the master node
            2. Install the plugin
            3. Create the cluster
            4. Add 1 node with controller role
            5. Add 1 node with compute and cinder roles
            6. Add 1 node with influxdb_grafana role
            7. Deploy the cluster
            8. Check that InfluxDB/Grafana are running
            9. Run OSTF

        Duration 60m
        Snapshot deploy_influxdb_grafana
        """
        self.check_run("deploy_influxdb_grafana")
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.create_cluster()

        self.activate_plugin()

        self.helpers.deploy_cluster(self.base_nodes)

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_influxdb_grafana", is_make=True)

    @test(depends_on_groups=['prepare_slaves_9'],
          groups=["deploy_ha_influxdb_grafana", "deploy", "deploy_ha"
                  "influxdb_grafana", "smoke"])
    @log_snapshot_after_test
    def deploy_ha_influxdb_grafana(self):
        """Deploy a cluster with the InfluxDB-Grafana plugin in HA mode

        Scenario:
            1. Upload the InfluxDB/Grafana plugin to the master node
            2. Install the plugin
            3. Create the cluster
            4. Add 3 nodes with controller role
            5. Add 3 nodes with compute and cinder roles
            6. Add 3 nodes with influxdb_grafana role
            7. Deploy the cluster
            8. Check that InfluxDB/Grafana are running
            9. Run OSTF

        Duration 120m
        Snapshot deploy_ha_influxdb_grafana
        """
        self.check_run("deploy_ha_influxdb_grafana")
        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugin()

        self.create_cluster()

        self.activate_plugin()

        self.helpers.deploy_cluster(self.full_ha_nodes)

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_ha_influxdb_grafana", is_make=True)

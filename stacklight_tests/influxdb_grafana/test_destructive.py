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
class TestDestructiveInfluxdbPlugin(api.InfluxdbPluginApi):
    """Class for testing plugin failover after network disaster."""

    @test(depends_on_groups=["deploy_ha_influxdb_grafana"],
          groups=["check_disaster_influxdb_grafana", "influxdb_grafana",
                  "destructive", "check_cluster_outage_influxdb_grafana"])
    @log_snapshot_after_test
    def check_cluster_outage_influxdb_grafana(self):
        """Verify that the backends and dashboards recover
        after a network outage of the whole InfluxDB/Grafana cluster.

        Scenario:
            1. Revert the snapshot with 9 deployed nodes in HA configuration
            2. Simulate a network outage of the whole InfluxDB/Grafana cluster
            3. Wait for at least 7 minutes before network recovery
            4. Wait for all services to be back online
            5. Run OSTF
            6. Check that the cluster's state is okay

        Duration 40m
        Snapshot check_cluster_outage_influxdb_grafana
        """
        self.env.revert_snapshot("deploy_ha_influxdb_grafana")

        self.helpers.emulate_whole_network_disaster(
            delay_before_recover=7 * 60)

        self.wait_plugin_online()

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("check_cluster_outage_influxdb_grafana")

    @test(depends_on_groups=["deploy_influxdb_grafana"],
          groups=["check_disaster_influxdb_grafana", "influxdb_grafana",
                  "destructive", "check_node_outage_influxdb_grafana"])
    @log_snapshot_after_test
    def check_node_outage_influxdb_grafana(self):
        """Verify that the backends and dashboards recover after
        a network outage on a standalone InfluxDB/Grafana node.

        Scenario:
            1. Revert the snapshot with 3 deployed nodes
            2. Simulate network interruption on the InfluxDB/Grafana node
            3. Wait for at least 30 seconds before recover network availability
            5. Run OSTF
            6. Check that plugin is working

        Duration 20m
        Snapshot check_node_outage_influxdb_grafana
        """
        self.env.revert_snapshot("deploy_influxdb_grafana")

        with self.fuel_web.get_ssh_for_nailgun_node(
                self.get_influxdb_master_node()) as remote:
            self.remote_ops.simulate_network_interrupt_on_node(remote)

        self.wait_plugin_online()

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("check_node_outage_influxdb_grafana")

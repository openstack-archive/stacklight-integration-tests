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
from stacklight_tests.influxdb_grafana import test_smoke_bvt


@test(groups=["plugins"])
class TestDestructiveInfluxdbPlugin(api.InfluxdbPluginApi):
    """Class for testing plugin failover after network disaster."""

    @test(depends_on=[
        test_smoke_bvt.TestInfluxdbPlugin.deploy_ha_influxdb_grafana_plugin],
        groups=["check_disaster_influxdb_grafana", "influxdb_grafana",
                "destructive", "check_failofer_network_all_influxdb_grafana"])
    @log_snapshot_after_test
    def emulate_network_disaster_whole_cluster_influxdb_grafana_plugin(self):
        """Verify that the backends and dashboards recover
        after a network interruption in the whole cluster.

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Simulate network interruption in the whole cluster
            3. Wait for at least 7 minutes before recover network availability
            4. Recover network availability
            5. Wait while all services are started
            6. Run OSTF
            7. Check that plugin is working
            8. Check that data continues to be pushed by the various nodes
               once the network interruption has ended

        Duration 40m
        """

        self.env.revert_snapshot("deploy_ha_influxdb_grafana_plugin")

        self.helpers.emulate_whole_network_disaster(
            delay_before_recover=7 * 60)

        self.wait_plugin_online()

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

        self.env.make_snapshot(
            "emulate_network_disaster_whole_cluster_influxdb_grafana_plugin")

    @test(depends_on=[
        test_smoke_bvt.TestInfluxdbPlugin.deploy_influxdb_grafana_plugin],
        groups=["check_disaster_influxdb_grafana", "influxdb_grafana",
                "destructive", "check_failover_network_node_influxdb_grafana"])
    @log_snapshot_after_test
    def emulate_network_disaster_on_influxdb_grafana_plugin_node(self):
        """Verify that the backends and dashboards recover after
        a network failure on plugin node.

        Scenario:
            1. Revert snapshot with 3 deployed nodes
            2. Simulate network interruption on plugin node
            3. Wait for at least 30 seconds before recover network availability
            4. Recover network availability
            5. Run OSTF
            6. Check that plugin is working
        Duration 20m
        """
        self.env.revert_snapshot("deploy_influxdb_grafana_plugin")

        with self.fuel_web.get_ssh_for_nailgun_node(
                self.get_influxdb_master_node()) as remote:
            self.remote_ops.simulate_network_interrupt_on_node(remote)

        self.wait_plugin_online()

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot(
            "emulate_network_disaster_on_influxdb_grafana_plugin_node")

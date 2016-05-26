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
class TestNodesInfluxdbPlugin(api.InfluxdbPluginApi):
    """Class for system tests for InfluxDB-Grafana plugin."""

    @test(depends_on_groups=["deploy_ha_influxdb_grafana"],
          groups=["check_scaling_influxdb_grafana", "scaling",
                  "influxdb_grafana", "system",
                  "check_add_delete_controller_influxdb_grafana"])
    @log_snapshot_after_test
    def add_remove_controller_influxdb_grafana(self):
        """Verify that the number of controllers can scale up and down

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Remove one controller node and update the cluster
            3. Check that plugin is working
            4. Run OSTF
            5. Add one controller node (return previous state) and
               update the cluster
            6. Check that plugin is working
            7. Run OSTF

        Duration 120m
        Snapshot add_remove_controller_influxdb_grafana
        """
        self.env.revert_snapshot("deploy_ha_influxdb_grafana")

        manipulated_node = {'slave-03': ['controller']}

        # NOTE(rpromyshlennikov): We set "check_services=False" and
        # "should_fail=1" parameters in deploy_cluster_wait and run_ostf
        # methods because after removing one node
        # nova has been keeping it in service list

        # Remove controller
        self.helpers.remove_node_from_cluster(manipulated_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

        # Add controller
        self.helpers.add_node_to_cluster(manipulated_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

        self.env.make_snapshot("add_remove_controller_influxdb_grafana")

    @test(depends_on_groups=["deploy_ha_influxdb_grafana"],
          groups=["check_scaling_influxdb_grafana", "scaling",
                  "influxdb_grafana", "system",
                  "add_remove_compute_influxdb_grafana"])
    @log_snapshot_after_test
    def add_remove_compute_influxdb_grafana(self):
        """Verify that the number of computes can scale up and down

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Remove one compute node and update the cluster
            3. Check that plugin is working
            4. Run OSTF
            5. Add one compute node (return previous state) and
               update the cluster
            6. Check that plugin is working
            7. Run OSTF

        Duration 120m
        Snapshot add_remove_compute_influxdb_grafana
        """
        self.env.revert_snapshot("deploy_ha_influxdb_grafana")

        manipulated_node = {'slave-04': ['compute', 'cinder']}

        # NOTE(rpromyshlennikov): We set "check_services=False" and
        # "should_fail=1" parameters in deploy_cluster_wait and run_ostf
        # methods because after removing one node
        # nova has been keeping it in service list

        # Remove compute
        self.helpers.remove_node_from_cluster(manipulated_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

        # Add controller
        self.helpers.add_node_to_cluster(manipulated_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

        self.env.make_snapshot("add_remove_compute_influxdb_grafana")

    @test(depends_on_groups=["deploy_ha_influxdb_grafana"],
          groups=["check_scaling_influxdb_grafana", "scaling",
                  "influxdb_grafana", "system",
                  "add_remove_influxdb_grafana_node"])
    @log_snapshot_after_test
    def add_remove_influxdb_grafana_node(self):
        """Verify that the number of InfluxDB-Grafana nodes
        can scale up and down

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Remove one InfluxDB-Grafana node and update the cluster
            3. Check that plugin is working
            4. Run OSTF
            5. Add one InfluxDB-Grafana node (return previous state) and
               update the cluster
            6. Check that plugin is working
            7. Run OSTF

        Duration 120m
        Snapshot add_remove_node_with_influxdb_grafana
        """
        self.env.revert_snapshot("deploy_ha_influxdb_grafana")

        self.check_influxdb_nodes_count(3)

        manipulated_node = {'slave-07': self.settings.role_name}

        # Remove InfluxDB-Grafana node
        self.helpers.remove_node_from_cluster(manipulated_node)

        self.check_plugin_online()

        # NOTE(rpromyshlennikov): shouldn't fail,
        # but it'll be fixed in next releases
        self.check_influxdb_nodes_count(2)

        self.fuel_web.run_ostf()

        # Add InfluxDB-Grafana node
        self.helpers.add_node_to_cluster(manipulated_node)

        self.check_plugin_online()

        self.check_influxdb_nodes_count(3)

        self.helpers.run_ostf()

        self.env.make_snapshot("add_remove_influxdb_grafana_node")

    @test(depends_on_groups=["deploy_ha_influxdb_grafana"],
          groups=["check_failover_influxdb_grafana" "failover",
                  "influxdb_grafana", "system", "destructive",
                  "shutdown_influxdb_grafana_node"])
    @log_snapshot_after_test
    def shutdown_influxdb_grafana_node(self):
        """Verify that failover for InfluxDB cluster works.

        Scenario:
            1. Connect to any influxdb_grafana node and run command
               'crm status'.
            2. Shutdown node were vip_influxdb was started.
            3. Check that vip_influxdb was started on another influxdb_grafana
               node.
            4. Check that plugin is working.
            5. Check that no data lost after shutdown.
            6. Run OSTF.

        Duration 30m
        Snaphost shutdown_influxdb_grafana_node
        """
        self.env.revert_snapshot("deploy_ha_influxdb_grafana")

        vip_name = "".join(["vip__", self.settings.vip_name])

        target_node = self.helpers.get_plugin_node_with_running_vip(
            self.settings.role_name, vip_name)

        self.helpers.hard_shutdown_node(target_node)

        self.helpers.wait_for_rotation_plugin_vip(
            target_node, self.settings.role_name, vip_name)

        self.check_plugin_online()

        # TODO(rpromyshlennikov): check no data lost

        self.helpers.run_ostf()

        self.env.make_snapshot("shutdown_influxdb_grafana_node")

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
                  "add_remove_controller_influxdb_grafana"])
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

        # Add compute
        self.helpers.add_node_to_cluster(manipulated_node)

        self.check_plugin_online()

        self.helpers.run_ostf(should_fail=1)

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

    @test(depends_on_groups=["deploy_ha_influxdb_grafana"],
          groups=["check_failover_influxdb_grafana" "failover",
                  "influxdb_grafana", "system", "destructive",
                  "shutdown_influxdb_grafana_node"])
    @log_snapshot_after_test
    def shutdown_influxdb_grafana_node(self):
        """Verify that failover for InfluxDB cluster works.

        Scenario:
            1. Shutdown node were vip_influxdb was started.
            2. Check that vip_influxdb was started on another influxdb_grafana
               node.
            3. Check that plugin is working.
            4. Check that no data lost after shutdown.
            5. Run OSTF.

        Duration 30m
        """
        self.env.revert_snapshot("deploy_ha_influxdb_grafana")

        vip_name = self.helpers.full_vip_name(self.settings.vip_name)

        target_node = self.helpers.get_node_with_vip(
            self.settings.role_name, vip_name)

        self.helpers.power_off_node(target_node)

        self.helpers.wait_for_vip_migration(
            target_node, self.settings.role_name, vip_name)

        self.check_plugin_online()

        # TODO(rpromyshlennikov): check no data lost

        self.helpers.run_ostf()

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["influxdb_grafana_createmirror_deploy_plugin",
                  "system", "influxdb_grafana", "createmirror"])
    @log_snapshot_after_test
    def influxdb_grafana_createmirror_deploy_plugin(self):
        """Run fuel-createmirror and deploy environment

        Scenario:
            1. Upload and install the InfluxDB/Grafana plugin
               to the master node.
            2. Run the following command on the master node:
               fuel-createmirror
            3. Create an environment with enabled plugin and deploy it.
            4. Run OSTF.

        Duration 60m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.helpers.fuel_createmirror()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugin()

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['compute'],
                'slave-03': self.settings.role_name
            }
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

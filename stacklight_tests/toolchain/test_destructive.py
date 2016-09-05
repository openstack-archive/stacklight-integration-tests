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

from devops.helpers import helpers as devops_helpers
from fuelweb_test.helpers.decorators import log_snapshot_after_test
from proboscis import asserts
from proboscis import test

from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestDestructiveToolchainPlugin(api.ToolchainApi):
    """Class for testing plugin failover after network disaster."""

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["check_disaster_toolchain", "toolchain",
                  "destructive", "check_cluster_outage_toolchain"])
    @log_snapshot_after_test
    def check_cluster_outage_toolchain(self):
        """Verify that the backends and dashboards recover
        after a network outage of the whole cluster with plugins toolchain.

        Scenario:
            1. Revert the snapshot with 9 deployed nodes in HA configuration
            2. Simulate a network outage of the whole cluster
               with plugins toolchain
            3. Wait for at least 7 minutes before network recovery
            4. Wait for all services to be back online
            5. Run OSTF
            6. Check that the cluster's state is okay

        Duration 40m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        self.helpers.emulate_whole_network_disaster(
            delay_before_recover=7 * 60)

        self.INFLUXDB_GRAFANA.wait_plugin_online()
        self.ELASTICSEARCH_KIBANA.wait_plugin_online()
        self.LMA_INFRASTRUCTURE_ALERTING.wait_plugin_online()

        # NOTE(rpromyshlennikov): OpenStack cluster can't recover after it,
        # but plugins toolchain is working properly
        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["check_disaster_toolchain", "toolchain",
                  "destructive", "check_node_outage_toolchain"])
    @log_snapshot_after_test
    def check_node_outage_toolchain(self):
        """Verify that the backends and dashboards recover after
        a network outage on a standalone plugins toolchain node.

        Scenario:
            1. Revert the snapshot with 3 deployed nodes
            2. Simulate network interruption on the Toolchain node
            3. Wait for at least 30 seconds before recover network availability
            4. Run OSTF
            5. Check that plugins toolchain is working

        Duration 20m
        """
        self.env.revert_snapshot("deploy_toolchain")

        with self.fuel_web.get_ssh_for_nailgun_node(
                self.helpers.get_master_node_by_role(
                    self.settings.stacklight_roles)
        ) as remote:
            self.remote_ops.simulate_network_interrupt_on_node(remote)

        self.INFLUXDB_GRAFANA.wait_plugin_online()
        self.ELASTICSEARCH_KIBANA.wait_plugin_online()
        self.LMA_INFRASTRUCTURE_ALERTING.wait_plugin_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["toolchain",
                  "destructive", "check_plugins_after_reboot_toolchain"])
    @log_snapshot_after_test
    def check_plugins_after_reboot_toolchain(self):
        """Verify that the backends and dashboards recover after
        reboot of a standalone plugins toolchain node.

        Scenario:
            1. Revert the snapshot with 3 deployed nodes
            2. Reboot plugins node
            3. Wait 5 minutes to became plugins online
            4. Run OSTF
            5. Check that plugins toolchain is working

        Duration 10m
        """

        self.env.revert_snapshot("deploy_toolchain")

        stl_devops_node = self.fuel_web.get_devops_node_by_nailgun_node(
            self.helpers.get_master_node_by_role(
                self.settings.stacklight_roles))
        self.fuel_web.warm_restart_nodes([stl_devops_node])

        self.INFLUXDB_GRAFANA.wait_plugin_online()
        self.ELASTICSEARCH_KIBANA.wait_plugin_online()
        self.LMA_INFRASTRUCTURE_ALERTING.wait_plugin_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["toolchain",
                  "destructive", "check_plugins_during_rescheduling"])
    @log_snapshot_after_test
    def check_plugins_during_rescheduling(self):
        """Verify that the backends and dashboards recover after
        rescheduling of a toolchain master node.

        Scenario:
            1. Revert the snapshot with 9 deployed nodes
            2. Shutdown master node
            3. Wait 5 minutes to reschedule master node
            4. Check that plugins toolchain is working
            5. Turn on "old master" node
            6. Shutdown new master and 3rd node with plugins
            7. Wait 5 minutes to reschedule master node
            8. Check that plugins toolchain is working
            9. Run OSTF

        Duration 20m
        """
        def wait_new_master(current_master, excluded_nodes=()):
            excluded_nodes = excluded_nodes + (current_master,)
            excluded_nodes_fqdns = [node["fqdn"] for node in excluded_nodes]
            devops_helpers.wait(
                lambda: self.helpers.get_master_node_by_role(
                    self.settings.stacklight_roles,
                    excluded_nodes_fqdns)["fqdn"] != current_master["fqdn"],
                timeout=5 * 60
            )
            return self.helpers.get_master_node_by_role(
                self.settings.stacklight_roles)

        self.env.revert_snapshot("deploy_ha_toolchain")

        # Determinate and power off stacklight master node
        stl_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, self.settings.stacklight_roles)
        stl_master_node = self.helpers.get_master_node_by_role(
            self.settings.stacklight_roles)
        current_stl_d_node = self.fuel_web.get_devops_node_by_nailgun_node(
            stl_master_node)
        self.helpers.power_off_node(current_stl_d_node)

        # Make sure that stacklight working properly after master rescheduling
        new_stl_master_node = wait_new_master(stl_master_node)
        asserts.assert_not_equal(stl_master_node["fqdn"],
                                 new_stl_master_node["fqdn"])
        self.INFLUXDB_GRAFANA.wait_plugin_online()
        self.ELASTICSEARCH_KIBANA.wait_plugin_online()
        self.LMA_INFRASTRUCTURE_ALERTING.wait_plugin_online()
        self.fuel_web.warm_start_nodes([current_stl_d_node])

        # Power off last 2 stacklight nodes
        nodes_to_power_off = tuple(node for node in stl_nodes
                                   if node["fqdn"] != stl_master_node["fqdn"])
        self.helpers.power_off_nodes([
            self.fuel_web.get_devops_node_by_nailgun_node(node)
            for node in nodes_to_power_off
        ])

        # Make sure that stacklight working properly after master rescheduling
        last_stl_master_node = wait_new_master(new_stl_master_node,
                                               nodes_to_power_off)
        asserts.assert_equal(stl_master_node["fqdn"],
                             last_stl_master_node["fqdn"])
        self.INFLUXDB_GRAFANA.wait_plugin_online()
        self.ELASTICSEARCH_KIBANA.wait_plugin_online()
        self.LMA_INFRASTRUCTURE_ALERTING.wait_plugin_online()

        self.helpers.run_ostf()

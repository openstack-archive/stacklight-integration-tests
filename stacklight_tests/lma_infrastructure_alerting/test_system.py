# coding=utf-8
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

from proboscis import asserts
from proboscis import test

from fuelweb_test.helpers.decorators import log_snapshot_after_test

from stacklight_tests.lma_infrastructure_alerting import api

@test(groups=["plugins"])
class TestLMAInfraAlertingPluginSystem(api.InfraAlertingPluginApi):
    """Class for system testing the LMA Infrastructure Alerting plugin."""

    @test(depends_on_groups=['deploy_ha_lma_infrastructure_alerting'],
          groups=["add_remove_controller_lma_infrastructure_alerting",
                  "system", "lma_infrastructure_alerting", "scaling"])
    @log_snapshot_after_test
    def add_remove_controller_lma_infrastructure_alerting(self):
        """Add/remove controller nodes in existing environment

        Scenario:
            1.  Remove 1 node with the controller role.
            2.  Re-deploy the cluster.
            3.  Check the plugin services using the CLI
            4.  Check in the Nagios UI that the removed node is no
            longer monitored.
            5.  Run the health checks (OSTF).
            6.  Add 1 new node with the controller role.
            7.  Re-deploy the cluster.
            8.  Check the plugin services using the CLI.
            9.  Check in the Nagios UI that the new node is monitored.
            10. Run the health checks (OSTF).

        Duration 60m
        """
        self.env.revert_snapshot("deploy_ha_lma_infrastructure_alerting")

        target_node = self.helpers.get_fuel_node_name('slave-02_controller')
        self.helpers.remove_node_from_cluster({'slave-02': ['controller']})
        self.helpers.run_ostf(should_fail=1)
        self.check_plugin_online()
        self.check_node_in_nagios(target_node, False)

        self.helpers.add_node_to_cluster({'slave-02': ['controller']})
        self.helpers.run_ostf(should_fail=1)
        self.check_plugin_online()
        target_node = self.helpers.get_fuel_node_name('slave-02_controller')
        self.check_node_in_nagios(target_node, True)

    @test(depends_on_groups=['deploy_ha_lma_infrastructure_alerting'],
          groups=["add_remove_compute_lma_infrastructure_alerting", "system",
                  "lma_infrastructure_alerting", "scaling"])
    @log_snapshot_after_test
    def add_remove_compute_lma_infrastructure_alerting(self):
        """Add/remove compute nodes in existing environment

        Scenario:
            1.  Remove 1 node with the compute role.
            2.  Re-deploy the cluster.
            3.  Check the plugin services using the CLI
            4.  Check in the Nagios UI that the removed node is no
             longer monitored.
            5.  Run the health checks (OSTF).
            6.  Add 1 new node with the compute role.
            7.  Re-deploy the cluster.
            8.  Check the plugin services using the CLI.
            9.  Check in the Nagios UI that the new node is monitored.
            10. Run the health checks (OSTF).

        Duration 60m
        """
        self.env.revert_snapshot("deploy_ha_lma_infrastructure_alerting")

        target_node = self.helpers.get_fuel_node_name(
            'slave-04_compute_cinder')
        self.helpers.remove_node_from_cluster(
            {'slave-04': ['compute', 'cinder']}, False, True)
        self.helpers.run_ostf(should_fail=1)
        self.check_plugin_online()
        self.check_node_in_nagios(target_node, False)

        self.helpers.add_node_to_cluster({'slave-04': ['compute', 'cinder']})
        self.helpers.run_ostf(should_fail=1)
        self.check_plugin_online()
        target_node = self.helpers.get_fuel_node_name(
            'slave-04_compute_cinder')
        self.check_node_in_nagios(target_node, True)

    @test(depends_on_groups=['deploy_ha_lma_infrastructure_alerting'],
          groups=["add_remove_infrastructure_alerting_node", "system",
                  "lma_infrastructure_alerting", "scaling"])
    @log_snapshot_after_test
    def add_remove_infrastructure_alerting_node(self):
        """Add/remove infrastructure alerting nodes in existing environment

        Scenario:
            1.  Remove 1 node with the infrastructure_alerting role.
            2.  Re-deploy the cluster.
            3.  Check the plugin services using the CLI
            4.  Check that Nagios UI works correctly.
            5.  Run the health checks (OSTF).
            6.  Add 1 new node with the infrastructure_alerting role.
            7.  Re-deploy the cluster.
            8.  Check the plugin services using the CLI.
            9.  Check that Nagios UI works correctly.
            10. Run the health checks (OSTF).

        Duration 60m
        """
        self.env.revert_snapshot("deploy_ha_lma_infrastructure_alerting")

        target_node = self.helpers.get_fuel_node_name(
            'slave-05_{0}'.format(self.settings.role_name[0]))
        self.helpers.remove_node_from_cluster(
            {'slave-05': self.settings.role_name})
        self.helpers.run_ostf(should_fail=1)
        self.check_plugin_online()
        self.check_node_in_nagios(target_node, False)

        self.helpers.add_node_to_cluster(
            {'slave-05': self.settings.role_name})
        self.helpers.run_ostf(should_fail=1)
        self.check_plugin_online()
        target_node = self.helpers.get_fuel_node_name(
            'slave-05_{0}'.format(self.settings.role_name[0]))
        self.check_node_in_nagios(target_node, True)

    @test(depends_on_groups=['deploy_ha_lma_infrastructure_alerting'],
          groups=["shutdown_infrastructure_alerting_node", "system",
                  "lma_infrastructure_alerting", "shutdown"])
    @log_snapshot_after_test
    def shutdown_infrastructure_alerting_node(self):
        """Shutdown infrastructure alerting node

        Scenario:
            1.  Connect to any infrastructure_alerting node and run
             command ‘crm status’.
            2.  Shutdown node were vip_infrastructure_alerting_mgmt_vip
             was started.
            3.  Check that vip_infrastructure_alerting was started
             on another infrastructure_alerting node.
            4.  Check that Nagios UI works correctly.
            5.  Check that no data lost after shutdown.
            6.  Run OSTF.

        Duration 60m
        """
        self.env.revert_snapshot("deploy_ha_lma_infrastructure_alerting")

        target_node = self.get_primary_lma_node()
        self.fuel_web.warm_shutdown_nodes([target_node])
        new_node = self.get_primary_lma_node(target_node.name)
        asserts.assert_not_equal(target_node, new_node)

        self.check_plugin_online()
        self.helpers.run_ostf()

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["lma_infrastructure_alerting_createmirror_deploy_plugin",
                  "system", "lma_infrastructure_alerting", "createmirror"])
    @log_snapshot_after_test
    def lma_infrastructure_alerting_createmirror_deploy_plugin(self):
        """Run fuel-createmirror and deploy environment

        Scenario:
            1.  Copy the plugins to the Fuel Master node and
             install the plugins.
            2.  Run the following command on the master node:
                    fuel-createmirror
            3.  Create an environment with enabled plugins in the
            Fuel Web UI and deploy it.
            4.  Run OSTF.

        Duration 60m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.helpers.fuel_createmirror()

        self.create_cluster()

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

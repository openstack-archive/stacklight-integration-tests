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
from proboscis import asserts
from proboscis import test

from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestToolchain(api.ToolchainApi):
    """Class for smoke testing the LMA Toolchain plugins."""

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["install_toolchain", "install", "toolchain", "smoke"])
    @log_snapshot_after_test
    def install_toolchain(self):
        """Install the LMA Toolchain plugins and check it exists

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create a cluster
            4. Check that the plugins can be enabled

        Duration 20m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["deploy_toolchain", "deploy", "toolchain", "smoke"])
    @log_snapshot_after_test
    def deploy_toolchain(self):
        """Deploy a cluster with the LMA Toolchain plugins

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 1 node with controller role
            5. Add 1 node with compute and cinder roles
            6. Add 1 node with plugin roles
            7. Deploy the cluster
            8. Check that LMA Toolchain plugins are running
            9. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain
        """
        self.check_run("deploy_toolchain")
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

        self.helpers.deploy_cluster(self.settings.base_nodes)

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_toolchain", is_make=True)

    @test(depends_on_groups=['prepare_slaves_9'],
          groups=["deploy_nova_toolchain", "deploy", "toolchain", "smoke"])
    @log_snapshot_after_test
    def deploy_nova_toolchain(self):
        """Deploy a nova cluster with the LMA Toolchain plugins

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 1 node with controller and cinder role
            5. Add 4 node with compute
            6. Add 1 node with plugin roles
            7. Deploy the cluster
            8. Create 2 nova aggregates with respectively 2+1 hosts
            9. Check that LMA Toolchain plugins are running
            10. Run OSTF

        Duration 60m
        Snapshot deploy_nova_toolchain
        """
        self.check_run("deploy_nova_toolchain")
        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

        self.helpers.deploy_cluster(self.settings.nova_nodes)

        # Get all nodes names with compute role
        compute_nodes_names = map(
            lambda(l): l[0],
            filter(
                lambda(name,roles): any('compute' in s for s in roles),
                self.settings.nova_nodes.iteritems()))
        # Check that there are enough compute nodes for proper testing
        asserts.assert_true(
            len(compute_nodes_names) > 3,
            "Not enough compute nodes {0} (must be > 3)".format(
                len(compute_nodes_names)))
        # Sort list
        compute_nodes_names.sort()
        # Create nova aggregates 1st with 2 nodes second with 1 node
        # (this leaves 1 compute node not assigned to ny aggregate)
        self.helpers.create_nova_aggregates(
            { "aggregate-1": compute_nodes_names[0:2], 
              "aggregate-2": compute_nodes_names[2:3]})

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_nova_toolchain", is_make=True)

    @test(depends_on_groups=['prepare_slaves_9'],
          groups=["deploy_ha_toolchain", "deploy", "deploy_ha", "toolchain",
                  "smoke"])
    @log_snapshot_after_test
    def deploy_ha_toolchain(self):
        """Deploy a cluster with the LMA Toolchain plugins in HA mode

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 3 nodes with controller role
            5. Add 3 nodes with compute and cinder roles
            6. Add 3 nodes with plugin roles
            7. Deploy the cluster
            8. Check that LMA Toolchain plugins are running
            9. Run OSTF

        Duration 120m
        Snapshot deploy_ha_toolchain
        """
        self.check_run("deploy_ha_toolchain")
        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

        self.helpers.deploy_cluster(self.settings.full_ha_nodes)

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_ha_toolchain", is_make=True)

    @test(depends_on=[deploy_toolchain],
          groups=["uninstall_deployed_toolchain", "uninstall", "toolchain",
                  "smoke"])
    @log_snapshot_after_test
    def uninstall_deployed_toolchain(self):
        """Uninstall the LMA Toolchain plugins with a deployed environment

        Scenario:
            1.  Try to remove the plugins using the Fuel CLI
            2.  Check plugins can't be uninstalled on deployed cluster.
            3.  Remove the environment.
            4.  Remove the plugins.

        Duration 20m
        """
        self.env.revert_snapshot("deploy_toolchain")

        self.check_uninstall_failure()

        self.fuel_web.delete_env_wait(self.helpers.cluster_id)

        self.uninstall_plugins()

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["uninstall_toolchain", "uninstall", "toolchain", "smoke"])
    @log_snapshot_after_test
    def uninstall_toolchain(self):
        """Uninstall the LMA Toolchain plugins

        Scenario:
            1.  Install the plugins.
            2.  Remove the plugins.

        Duration 5m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.uninstall_plugins()

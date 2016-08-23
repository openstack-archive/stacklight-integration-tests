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

from stacklight_tests.helpers.helpers import get_plugin_name
from stacklight_tests.helpers.helpers import get_plugin_version
from stacklight_tests.settings import DETACH_RABBITMQ_PLUGIN_PATH
from stacklight_tests.toolchain import api
from stacklight_tests.toolchain import toolchain_settings as settings


@test(groups=["plugins"])
class TestToolchainPostInstallation(api.ToolchainApi):
    """Class for testing that the LMA Toolchain plugins can be installed in an
    existing environment.
    """

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["deploy_environment_without_toolchain", "deploy",
                  "toolchain", "post_installation"])
    @log_snapshot_after_test
    def deploy_environment_without_toolchain(self):
        """Deploy a cluster without the LMA Toolchain plugins.

        Scenario:
            1. Create the cluster
            2. Add 1 node with the controller role
            3. Add 1 node with the compute and cinder roles
            4. Deploy the cluster
            5. Run OSTF

        Duration 60m
        Snapshot deploy_environment_without_toolchain
        """
        self.check_run("deploy_environment_without_toolchain")

        self.env.revert_snapshot("ready_with_5_slaves")

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.helpers.deploy_cluster({
            'slave-01': ['controller'],
            'slave-02': ['compute', 'cinder'],
        })

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_environment_without_toolchain",
                               is_make=True)

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["deploy_mu_environment_with_detach_rabbitmq", "deploy",
                  "toolchain", "post_installation"])
    @log_snapshot_after_test
    def deploy_mu_environment_with_detach_rabbitmq(self):
        """Deploy a cluster with maintenance updates and the detach-rabbitmq
        plugin.

        Scenario:
            1. Apply the maintenance updates.
            2. Create the cluster
            3. Add 1 node with the controller role
            4. Add 1 node with the compute and cinder roles
            5. Add 1 node with the standalone-rabbitmq role
            6. Deploy the cluster
            7. Run OSTF

        Duration 60m
        Snapshot deploy_mu_environment_without_toolchain
        """
        self.check_run("deploy_mu_environment_without_toolchain")

        self.env.revert_snapshot("ready_with_5_slaves")

        self.helpers.apply_maintenance_update()
        self.helpers.prepare_plugin(DETACH_RABBITMQ_PLUGIN_PATH)
        self.helpers.activate_plugin(
            get_plugin_name(DETACH_RABBITMQ_PLUGIN_PATH),
            get_plugin_version(DETACH_RABBITMQ_PLUGIN_PATH))

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.helpers.deploy_cluster({
            'slave-01': ['controller'],
            'slave-02': ['compute', 'cinder'],
            'slave-03': ['standalone-rabbitmq']
        })

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_mu_environment_without_toolchain",
                               is_make=True)

    @test(depends_on=[deploy_environment_without_toolchain],
          groups=["deploy_toolchain_in_existing_environment", "deploy",
                  "toolchain", "detached_plugins"])
    @log_snapshot_after_test
    def deploy_toolchain_in_existing_environment(self):
        """Deploy the LMA Toolchain plugins in an existing environment.

        Scenario:
            1. Upload the plugins to the master node
            2. Install the plugins
            3. Configure the plugins
            4. Add 3 nodes with the plugin roles
            5. Deploy the cluster
            6. Redeploy the nodes that existed before the last deploy (MOS 8
               only)
            7. Check that LMA Toolchain plugins are running
            8. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_in_existing_environment
        """
        self._deploy_toolchain_in_existing_environment(
            "deploy_toolchain_in_existing_environment", {
                'slave-03': settings.stacklight_roles,
                'slave-04': settings.stacklight_roles,
                'slave-05': settings.stacklight_roles
            })

    @test(depends_on=[deploy_mu_environment_with_detach_rabbitmq],
          groups=["deploy_toolchain_in_environment_with_detach_rabbitmq",
                  "deploy", "toolchain", "detached_plugins"])
    @log_snapshot_after_test
    def deploy_toolchain_in_environment_with_detach_rabbitmq(self):
        """Deploy the LMA Toolchain plugins in an existing environment with
            maintenance updates and the detach_rabbitmq plugin.

        Scenario:
            1. Upload the plugins to the master node
            2. Install the plugins
            3. Configure the plugins
            4. Add 1 node with the plugin roles
            5. Deploy the cluster
            6. Redeploy the nodes that existed before the last deploy (MOS 8
               only)
            7. Check that LMA Toolchain plugins are running
            8. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_in_environment_with_detach_rabbitmq
        """
        self._deploy_toolchain_in_existing_environment(
            "deploy_toolchain_in_environment_with_detach_rabbitmq", {
                'slave-04': settings.stacklight_roles,
            })

    def _deploy_toolchain_in_existing_environment(self, snapshot_name, nodes):
        self.check_run(snapshot_name)

        existing_nodes = self.helpers.get_all_ready_nodes()

        self.prepare_plugins()

        self.activate_plugins()

        self.helpers.deploy_cluster(nodes)
        if self.helpers.get_fuel_release() == '8.0':
            # The 'hiera' and post-deployment tasks have to be re-executed
            # "manually" for the existing nodes on MOS 8. With later versions
            # of MOS, these tasks should be re-executed automatically.
            self.helpers.run_tasks(
                existing_nodes, tasks=['hiera'], start="post_deployment_start",
                timeout=20 * 60)

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot(snapshot_name, is_make=True)

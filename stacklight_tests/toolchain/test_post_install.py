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
            6. Check that LMA Toolchain plugins are running
            7. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_in_existing_environment
        """
        self.check_run("deploy_toolchain_in_existing_environment")

        existing_nodes = self.helpers.get_all_ready_nodes()

        self.prepare_plugins()

        self.activate_plugins()

        self.helpers.deploy_cluster({
            'slave-03': settings.stacklight_roles,
            'slave-04': settings.stacklight_roles,
            'slave-05': settings.stacklight_roles
        })
        if self.helpers.get_fuel_release() == '8.0':
            # The 'hiera' and post-deployment tasks have to be re-executed
            # "manually" for the existing nodes on MOS 8. With later versions
            # of MOS, these tasks should be re-executed automatically.
            self.helpers.run_tasks(
                existing_nodes, tasks=['hiera'], start="post_deployment_start",
                timeout=20 * 60)

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_toolchain_in_existing_environment",
                               is_make=True)

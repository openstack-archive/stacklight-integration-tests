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

from stacklight_tests.lma_collector import api


@test(groups=["plugins"])
class TestLMACollectorPlugin(api.LMACollectorPluginApi):
    """Class for smoke testing the LMA Collector plugin."""

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["install_lma_collector", "install",
                  "lma_collector", "smoke"])
    @log_snapshot_after_test
    def install_lma_collector(self):
        """Install the LMA Collector plugin

        Scenario:
            1. Upload the LMA Collector plugin to the master node
            2. Install the plugin
            3. Create a cluster
            4. Check that the plugin can be enabled

        Duration 20m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.create_cluster()

        self.activate_plugin()

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["deploy_lma_collector", "deploy", "lma_collector", "smoke"])
    @log_snapshot_after_test
    def deploy_lma_collector(self):
        """Deploy a cluster with the LMA Collector plugin

        Scenario:
            1. Upload plugin to the master node
            2. Install plugin
            3. Create cluster
            4. Add 1 node with controller role
            5. Add 1 node with compute role
            6. Deploy the cluster
            7. Check that plugin is working
            8. Run OSTF

        Duration 60m
        Snapshot deploy_lma_collector
        """

        self.check_run('deploy_lma_collector')

        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.create_cluster()

        self.activate_plugin()

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['compute']
            }
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_lma_collector", is_make=True)

    @test(depends_on=[deploy_lma_collector],
          groups=["uninstall_deployed_lma_collector", "uninstall",
                  "lma_collector", "smoke"])
    @log_snapshot_after_test
    def uninstall_deployed_lma_collector(self):
        """Uninstall the plugin with deployed environment

        Scenario:
            1.  Try to remove the plugins using the Fuel CLI
            2.  Check plugin can't be uninstalled on deployed cluster.
            3.  Remove the environment.
            4.  Remove the plugin.

        Duration 20m
        """
        self.env.revert_snapshot("deploy_lma_collector")

        self.check_uninstall_failure()

        self.fuel_web.delete_env_wait(self.helpers.cluster_id)

        self.uninstall_plugin()

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["uninstall_lma_collector", "uninstall", "lma_collector",
                  "smoke"])
    @log_snapshot_after_test
    def uninstall_lma_collector(self):
        """Uninstall the plugins

        Scenario:
            1.  Install plugin.
            2.  Remove the plugins.

        Duration 5m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.uninstall_plugin()

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

from stacklight_tests.lma_infrastructure_alerting import api


@test(groups=["plugins"])
class TestLMAInfraAlertingPlugin(api.InfraAlertingPluginApi):
    """Class for testing the LMA Infrastructure Alerting plugin."""

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["install_lma_infrastructure_alerting", "install",
                  "lma_infrastructure_alerting ", "smoke"])
    @log_snapshot_after_test
    def install_lma_infrastructure_alerting(self):
        """Install the LMA Infrastructure Alerting plugin

        Scenario:
            1. Upload the LMA Infrastructure Alerting plugin to the master node
            2. Install the plugin
            3. Create a cluster
            4. Check that the plugin can be enabled

        Duration 20m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugin()

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["deploy_lma_infrastructure_alerting", "deploy",
                  "lma_infrastructure_alerting", "smoke"])
    @log_snapshot_after_test
    def deploy_lma_infrastructure_alerting(self):
        """Deploy a cluster with the LMA Infrastructure Alerting plugin

        Scenario:
            1. Upload the LMA Infrastructure Alerting plugin to the master node
            2. Install the plugin
            3. Create the cluster
            4. Add 1 node with controller role
            5. Add 1 node with compute role
            6. Add 1 node with the infrastructure_alerting role
            7. Deploy the cluster
            8. Check that Nagios and Apache are running
            9. Run OSTF

        Duration 60m
        Snapshot deploy_lma_infrastructure_alerting
        """

        self.check_run('deploy_lma_infrastructure_alerting')

        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

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

        self.env.make_snapshot("deploy_lma_infrastructure_alerting",
                               is_make=True)

    @test(depends_on_groups=["prepare_slaves_9"],
          groups=["deploy_ha_lma_infrastructure_alerting", "deploy",
                  "deploy_ha", "lma_infrastructure_alerting", "smoke"])
    @log_snapshot_after_test
    def deploy_ha_lma_infrastructure_alerting(self):
        """Deploy a cluster with the LMA Infrastructure Alerting plugin in HA
        configuration

        Scenario:
            1. Upload the LMA Infrastructure Alerting plugin to the master node
            2. Install the plugin
            3. Create the cluster
            4. Add 3 nodes with controller role
            5. Add 1 node with compute and cinder roles
            6. Add 3 nodes with infrastructure_alerting role
            7. Deploy the cluster
            8. Check that Nagios and Apache are running
            9. Run OSTF

        Duration 60m
        Snapshot deploy_ha_lma_infrastructure_alerting
        """

        self.check_run('deploy_ha_lma_infrastructure_alerting')

        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugin()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugin()

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['controller'],
                'slave-03': ['controller'],
                'slave-04': ['compute', 'cinder'],
                'slave-05': self.settings.role_name,
                'slave-06': self.settings.role_name,
                'slave-07': self.settings.role_name
            }
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_ha_lma_infrastructure_alerting",
                               is_make=True)

    @test(depends_on=[deploy_lma_infrastructure_alerting],
          groups=["uninstall_deployed_lma_infrastructure_alerting",
                  "uninstall", "lma_infrastructure_alerting", "smoke"])
    @log_snapshot_after_test
    def uninstall_deployed_lma_infrastructure_alerting(self):
        """Uninstall the LMA Infrastructure Alering plugin with a deployed
        environment

        Scenario:
            1.  Try to remove the plugin using the Fuel CLI
            2.  Check plugin can't be uninstalled on deployed cluster.
            3.  Remove the environment.
            4.  Remove the plugin.

        Duration 20m
        """
        self.env.revert_snapshot("deploy_lma_infrastructure_alerting")

        self.check_uninstall_failure()

        self.fuel_web.delete_env_wait(self.helpers.cluster_id)

        self.uninstall_plugin()

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["uninstall_lma_infrastructure_alerting", "uninstall",
                  "lma_infrastructure_alerting", "smoke"])
    @log_snapshot_after_test
    def uninstall_lma_infrastructure_alerting(self):
        """Uninstall the LMA Infrastructure Alerting plugin

        Scenario:
            1.  Install the plugin.
            2.  Remove the plugin.

        Duration 5m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.uninstall_plugin()

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
import time
from proboscis import asserts
from proboscis import test

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test import logger
from fuelweb_test import settings
from fuelweb_test.tests import base_test_case

from stacklight_tests.lma_infrastructure_alerting import api


@test(groups=["plugins"])
class TestLMAInfraAlertingPlugin(api.InfraAlertingPluginApi):
    """Class for testing the LMA Infrastructure Alerting plugin."""

    @test(depends_on=[base_test_case.SetupEnvironment.prepare_slaves_3],
          groups=["install_lma_infra_alerting"])
    @log_snapshot_after_test
    def install_lma_infra_alerting_plugin(self):
        """Install LMA Infrastructure Alerting plugin and check it exists

        Scenario:
            1. Upload plugin to the master node
            2. Install plugin
            3. Create cluster
            4. Check that plugin exists

        Duration 20m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.create_cluster()

        self.activate_plugin()

    @test(depends_on=[base_test_case.SetupEnvironment.prepare_slaves_3],
          groups=["deploy_lma_infra_alerting"])
    @log_snapshot_after_test
    def deploy_lma_infra_alerting(self):
        """Deploy a cluster with the LMA Infrastructure Alerting plugin

        Scenario:
            1. Upload plugins to the master node
            2. Install plugins
            3. Create cluster
            4. Add 1 node with controller role
            5. Add 1 node with compute role
            6. Add 1 node with lma infrastructure alerting,
             influxdb grafana roles
            7. Deploy the cluster
            8. Check that plugin is working
            9. Run OSTF

        Duration 60m
        Snapshot deploy_lma_alerting_plugin
        """

        self.check_run('deploy_lma_alerting_plugin')

        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin(dependencies=True)

        self.create_cluster()

        self.activate_plugin(dependencies=True)

        role_name = self.settings.role_name[:].append('influxdb_grafana')
        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['compute'],
                'slave-03': role_name
            }
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

        logger.info('Making environment snapshot deploy_lma_alerting_plugin')
        self.env.make_snapshot("deploy_lma_alerting_plugin", is_make=True)

    @test(depends_on=[base_test_case.SetupEnvironment.prepare_slaves_9],
          groups=["deploy_lma_infra_alerting_ha"])
    @log_snapshot_after_test
    def deploy_lma_infra_alerting_ha(self):
        """Deploy a cluster with the LMA Infrastructure Alerting plugin

        Scenario:
            1. Upload plugins to the master node
            2. Install plugins
            3. Create cluster
            4. Add 3 nodes with controller role
            5. Add 1 node with compute and cinder roles
            6. Add 3 nodes with lma infrastructure alerting,
             influxdb grafana roles
            7. Deploy the cluster
            8. Check that plugin is working
            9. Run OSTF

        Duration 60m
        Snapshot deploy_lma_alerting_plugin_ha
        """

        self.check_run('deploy_lma_alerting_plugin_ha')

        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugin(dependencies=True)

        self.create_cluster()

        self.activate_plugin(dependencies=True)

        role_name = self.settings.role_name[:].append('influxdb_grafana')
        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['controller'],
                'slave-03': ['controller'],
                'slave-04': ['compute', 'cinder'],
                'slave-05': role_name,
                'slave-06': role_name,
                'slave-07': role_name
            }
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

        logger.info('Making environment snapshot '
                    'deploy_lma_alerting_plugin_ha')
        self.env.make_snapshot("deploy_lma_alerting_plugin_ha", is_make=True)

    @test(depends_on=[deploy_lma_infra_alerting_ha],
          groups=["uninstall_deployed_plugin"])
    @log_snapshot_after_test
    def uninstall_deployed_plugin(self):
        """Uninstall the plugins with deployed environment

        Scenario:
            1.  Try to remove the plugins using the Fuel CLI
            2.  Remove the environment.
            3.  Remove the plugins.

        Duration 20m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin")

        self.helpers.uninstall_plugin(self.settings.name,
                                      self.settings.version, 1,
                                      'Plugin deletion must not be permitted'
                                      ' while it\'s active in deployed in env')

        self.fuel_web.delete_env_wait(self.helpers.cluster_id)
        self.helpers.uninstall_plugin(self.settings.name,
                                      self.settings.version)

    @test(depends_on=[base_test_case.SetupEnvironment.prepare_slaves_3],
          groups=["uninstall_plugin"])
    @log_snapshot_after_test
    def uninstall_plugin(self):
        """Uninstall the plugins

        Scenario:
            1.  Install plugin.
            2.  Remove the plugins.

        Duration 5m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.helpers.uninstall_plugin(self.settings.name,
                                      self.settings.version)



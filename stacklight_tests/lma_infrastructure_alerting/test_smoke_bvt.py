# coding=utf-8
#    Copyright 2015 Mirantis, Inc.
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
from fuelweb_test import logger
from fuelweb_test import settings
from fuelweb_test.tests import base_test_case

from stacklight_tests.lma_infrastructure_alerting import api
from stacklight_tests.lma_infrastructure_alerting import test_functional

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

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['compute'],
                'slave-03': [self.settings.role_name, 'influxdb_grafana']
            }
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

        logger.info('Making environment snapshot deploy_lma_alerting_plugin')
        self.env.make_snapshot("deploy_lma_alerting_plugin", is_make=True)

    @test(depends_on=[test_functional.TestLMAInfraAlertingPluginFunc.deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["add_remove_controller"])
    @log_snapshot_after_test
    def add_remove_controller(self):
        """Add/remove controller nodes in existing environment

        Scenario:
            1.  Remove 1 node with the controller role.
            2.  Re-deploy the cluster.
            3.  Check the plugin services using the CLI
            4.  Check in the Nagios UI that the removed node is no longer monitored.
            5.  Run the health checks (OSTF).
            6.  Add 1 new node with the controller role.
            7.  Re-deploy the cluster.
            8.  Check the plugin services using the CLI.
            9.  Check in the Nagios UI that the new node is monitored.
            10. Run the health checks (OSTF).

        Duration 60m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        target_node = self.helpers.get_fuel_node_name('slave-02')
        self.helpers.remove_node_from_cluster({'slave-02': ['controller']})
        self.run_ostf(should_fail=1)
        self.check_plugin_online()
        self.check_node_in_nagios(target_node, False)

        self.helpers.add_node_to_cluster({'slave-02': ['controller']})
        self.run_ostf(should_fail=1)
        self.check_plugin_online()
        target_node = self.helpers.get_fuel_node_name('slave-02')
        self.check_node_in_nagios(target_node, True)

    @test(depends_on=[test_functional.TestLMAInfraAlertingPluginFunc.deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["add_remove_compute"])
    @log_snapshot_after_test
    def add_remove_compute(self):
        """Add/remove compute nodes in existing environment

        Scenario:
            1.  Remove 1 node with the compute role.
            2.  Re-deploy the cluster.
            3.  Check the plugin services using the CLI
            4.  Check in the Nagios UI that the removed node is no longer monitored.
            5.  Run the health checks (OSTF).
            6.  Add 1 new node with the compute role.
            7.  Re-deploy the cluster.
            8.  Check the plugin services using the CLI.
            9.  Check in the Nagios UI that the new node is monitored.
            10. Run the health checks (OSTF).

        Duration 60m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        target_node = self.helpers.get_fuel_node_name('slave-04')
        self.helpers.remove_node_from_cluster({'slave-04': ['compute', 'cinder']}, False, True)
        self.run_ostf(should_fail=1)
        self.check_plugin_online()
        self.check_node_in_nagios(target_node, False)

        self.helpers.add_node_to_cluster({'slave-04': ['compute', 'cinder']})
        self.run_ostf(should_fail=1)
        self.check_plugin_online()
        target_node = self.helpers.get_fuel_node_name('slave-04')
        self.check_node_in_nagios(target_node, True)

    @test(depends_on=[test_functional.TestLMAInfraAlertingPluginFunc.deploy_lma_infra_alerting_plugin_in_ha_mode],
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

        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel plugins --remove {0}=={1}"
                                      .format(self.settings.name, self.settings.version))
            asserts.assert_equal(1, exec_res['exit_code'], 'Plugin deletion must not be permitted while '
                                                           'it\'s active in deployed in env')

            self.fuel_web.delete_env_wait(self.helpers.cluster_id)
            exec_res = remote.execute("fuel plugins --remove {0}=={1}"
                                      .format(self.settings.name, self.settings.version))
# TODO: plugin deletion has a bug. CHANGED!
            asserts.assert_equal(1, exec_res['exit_code'],
                                 'Plugin deletion failed: {0}'.format(exec_res['stderr']))

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

        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel plugins --remove {0}=={1}"
                                      .format(self.settings.name, self.settings.version))
# TODO: plugin deletion has a bug. CHANGED!
            asserts.assert_equal(1, exec_res['exit_code'],
                                 'Plugin deletion failed: {0}'.format(exec_res['stderr']))

    @test(depends_on=[base_test_case.SetupEnvironment.prepare_slaves_3],
          groups=["createmirror_deploy_plugin"])
    @log_snapshot_after_test
    def createmirror_deploy_plugin(self):
        """Run fuel-createmirror and deploy environment

        Scenario:
            1.  Copy the plugins to the Fuel Master node and install the plugins.
            2.  Run the following command on the master node:
                    fuel-createmirror
            3.  Create an environment with enabled plugins in the Fuel Web UI and deploy it.
            4.  Run OSTF.

        Duration 60m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin(dependencies=True)

        logger.info("Executing 'fuel-createmirror' command.")
        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel-createmirror")
            asserts.assert_equal(0, exec_res['exit_code'],
                                 'fuel-createmirror failed: {0}'.format(exec_res['stderr']))

        self.create_cluster()

        self.activate_plugin(dependencies=True)

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['compute'],
                'slave-03': [self.settings.role_name, 'influxdb_grafana']
            }
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

    @test(depends_on=[deploy_lma_infra_alerting],
          groups=["plugin_core_repos_setup"])
    @log_snapshot_after_test
    def plugin_core_repos_setup(self):
        """Fuel-createmirror and setup of core repos

        Scenario:
            1.  Copy the plugins to the Fuel Master node and install the plugins.
            2.  Create an environment with enabled plugin in the Fuel Web UI and deploy it.
            3.  Run OSTF
            4.  Go in cli through controller / compute / storage /etc nodes and get pid of
                services which were launched by plugin and store them.
            5.  Launch the following command on the Fuel Master node:
                    fuel-createmirror -M
            6.  Launch the following command on the Fuel Master node:
                    fuel --env <ENV_ID> node --node-id <NODE_ID1> <NODE_ID2>
                        <NODE_ID_N> --tasks setup_repositories
            7.  Go to controller/plugin/storage node and check if plugin's services are
                alive and aren't changed their pid.
            8.  Check with fuel nodes command that all nodes are remain in ready status.
            9.  Rerun OSTF.

        Duration 60m
        """

        self.env.revert_snapshot("deploy_lma_alerting_plugin")

        origina_pids = self.get_alerting_tasks_pids()

        logger.info("Executing 'fuel-createmirror -M' command.")
        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel-createmirror -M")
# TODO: fuel-createmirror -M will fail during the execution. CHANGED!
            asserts.assert_equal(1, exec_res['exit_code'],
                                 'fuel-createmirror -M failed: {0}'.format(exec_res['stderr']))
            cmd = "fuel --env {0} node --node-id " \
                  "1 2 3 --tasks setup_repositories".format(self.helpers.cluster_id)
            exec_res = remote.execute(cmd)
            asserts.assert_equal(0, exec_res['exit_code'],
                                 'Command {0} failed: {1}'.format(cmd, exec_res['stderr']))

        new_pids = self.get_alerting_tasks_pids()

        error = False
        for node in origina_pids:
            for process in origina_pids[node]:
                if origina_pids[node][process] != new_pids[node][process]:
                    logger.error("Process {0} on node {1} has changed its pid!"
                                 " Was: {2} Now: {3}".format(process,node, origina_pids[node][process],
                                                             new_pids[node][process]))
                    error = True

        asserts.assert_false(error, 'Some processes have changed their pids!')

        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel nodes | awk {'print $3'} | grep error")
# TODO: Nodes are in deploying state. CHANGED!
            asserts.assert_equal(1, exec_res['exit_code'], 'Some nodes are in error state!')

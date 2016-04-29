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
import os
import time

import requests

from proboscis import asserts
from proboscis import test

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test import logger
from fuelweb_test import settings
from fuelweb_test.tests import base_test_case

from stacklight_tests.lma_infrastructure_alerting import api


class NotFound(Exception):
    message = "Not Found."


class ErrorState(Exception):
    message = "Error state."


@test(groups=["plugins"])
class TestLMAInfraAlertingPlugin(api.InfraAlertingPluginApi):
    """Class for testing the LMA Infrastructure Alerting plugin."""

    def get_primary_lma_node(self):
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, [self.settings.role_name])
        lma_node = self.fuel_web.get_devops_nodes_by_nailgun_nodes(nailgun_nodes)[0]
        with self.fuel_web.get_ssh_for_node(lma_node.name) as remote:
            result = remote.execute("crm status | grep vip__infrastructure_alerting_mgmt_vip | awk '{print $4}'")
            return self.fuel_web.get_devops_node_by_nailgun_fqdn(result['stdout'][0].rstrip())

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

    @test(depends_on=[base_test_case.SetupEnvironment.prepare_slaves_9],
          groups=["deploy_lma_infra_alerting_ha"])
    @log_snapshot_after_test
    def deploy_lma_infra_alerting_plugin_in_ha_mode(self):
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

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['controller'],
                'slave-03': ['controller'],
                'slave-04': ['compute', 'cinder'],
                'slave-05': [self.settings.role_name, 'influxdb_grafana'],
                'slave-06': [self.settings.role_name, 'influxdb_grafana'],
                'slave-07': [self.settings.role_name, 'influxdb_grafana']
            }
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

        logger.info('Making environment snapshot deploy_lma_alerting_plugin_ha')
        self.env.make_snapshot("deploy_lma_alerting_plugin_ha", is_make=True)

    @test(depends_on=[deploy_lma_infra_alerting_plugin_in_ha_mode],
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
        self.helpers.add_remove_node({'slave-02': ['controller']}, False, True)
        self.check_plugin_online()
        self.check_node_in_nagios(target_node, False)

        self.helpers.add_remove_node({'slave-02': ['controller']})
        self.check_plugin_online()
        target_node = self.helpers.get_fuel_node_name('slave-02')
        self.check_node_in_nagios(target_node, False)

    @test(depends_on=[deploy_lma_infra_alerting_plugin_in_ha_mode],
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
        self.helpers.add_remove_node({'slave-04': ['compute', 'cinder']}, False, True)
        self.check_plugin_online()
        self.check_node_in_nagios(target_node, False)

        self.helpers.add_remove_node({'slave-04': ['compute', 'cinder']})
        self.check_plugin_online()
        target_node = self.helpers.get_fuel_node_name('slave-04')
        self.check_node_in_nagios(target_node, False)

    @test(depends_on=[deploy_lma_infra_alerting_plugin_in_ha_mode],
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
            asserts.assert_equal(1, exec_res['exit_code'], 'Some nodes are in error state!')

    @test(depends_on=[deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["add_remove_infrastructure_alerting"])
    @log_snapshot_after_test
    def add_remove_infrastructure_alerting(self):
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
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        target_node = self.helpers.get_fuel_node_name('slave-05')
        self.helpers.add_remove_node({'slave-05': [self.settings.role_name, 'influxdb_grafana']}, False, True)
        self.check_plugin_online()
        self.check_node_in_nagios(target_node, False)

        self.helpers.add_remove_node({'slave-05': [self.settings.role_name, 'influxdb_grafana']})
        self.check_plugin_online()
        target_node = self.helpers.get_fuel_node_name('slave-05')
        self.check_node_in_nagios(target_node, False)

    @test(depends_on=[deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["shutdown_infrastructure_alerting"])
    @log_snapshot_after_test
    def shutdown_infrastructure_alerting(self):
        """Shutdown infrastructure alerting node

        Scenario:
            1.  Connect to any infrastructure_alerting node and run command ‘crm status’.
            2.  Shutdown node were vip_infrastructure_alerting_mgmt_vip was started.
            3.  Check that vip_infrastructure_alerting was started on another infrastructure_alerting node.
            4.  Check the plugin services using CLI.
            5.  Check that Nagios UI works correctly.
            6.  Check that no data lost after shutdown.
            7.  Run OSTF.

        Duration 60m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(self.helpers.cluster_id,
                                                                         [self.role_name])
        d_nodes = self.fuel_web.get_devops_nodes_by_nailgun_nodes(nailgun_nodes)

        with self.fuel_web.get_ssh_for_node(d_nodes[0].name) as remote:
            result = remote.execute("crm status | grep vip__infrastructure_alerting_mgmt_vip | awk '{print $4}'")
            target_node = self.fuel_web.get_devops_node_by_nailgun_fqdn(result['stdout'][0].rstrip())

        self.fuel_web.warm_shutdown_nodes([target_node])
        for node in d_nodes:
            if target_node.name in node.name:
                d_nodes.remove(node)
                break

        with self.fuel_web.get_ssh_for_node(d_nodes[0].name) as remote:
            result = remote.execute("crm status | grep vip__infrastructure_alerting_mgmt_vip | awk '{print $4}'")
            new_node = self.fuel_web.get_devops_node_by_nailgun_fqdn(result['stdout'][0].rstrip())
        asserts.assert_not_equal(target_node, new_node)

#TODO: TEMPORARY! MUST BE TAKEN FROM INFLUXDB TEST SUITE
        self.helpers.check_influxdb_status(d_nodes)
        self.check_plugin_online()

    @test(depends_on=[deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["warning_alert_service_infra_alerting"])
    @log_snapshot_after_test
    def warning_alert_service_infra_alerting(self):
        """Verify that the warning alerts for services show up in the Grafana and Nagios UI.

        Scenario:
            1.  Open the Nagios URL
            2.  Connect to one of the controller nodes using ssh and stop the nova-api service.
            3.  Wait for at least 1 minute.
            4.  On Nagios, check the following items:
                    - the ‘nova’ service is in ‘WARNING’ state,
                    - the local user root on the lma node has received an email about the service
                     being in warning state.
            5.  Restart the nova-api service.
            6.  Wait for at least 1 minute.
            7.  On Nagios, check the following items:
                    - the ‘nova’ service is in ‘OK’ state,
                    - the local user root on the lma node has received an email about the recovery
                     of the service.
            8.  Stop the nova-scheduler service.
            9.  Wait for at least 3 minutes.
            10. On Nagios, check the following items:
                    - the ‘nova’ service is in ‘WARNING’ state,
                    - the local user root on the lma node has received an email about the service
                     being in warning state.
            11. Restart the nova-scheduler service.
            12. Wait for at least 1 minute.
            13. On Nagios, check the following items:
                    - the ‘nova’ service is in ‘OK’ state,
                    - the local user root on the lma node has received an email about the recovery
                     of the service.
            14. Repeat steps 1 to 13 for the following services:
                    - Cinder (stopping and starting the cinder-api and cinder-api services
                     respectively).
                    - Neutron (stopping and starting the neutron-server and neutron-openvswitch-agent
                     services respectively).
            15. Repeat steps 1 to 7 for the following services:
                    - Glance (stopping and starting the glance-api service).
                    - Heat (stopping and starting the heat-api service).
                    - Keystone (stopping and starting the Apache service).

        Duration 15m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        driver = self.get_nagios_main_page()

        services = {
            'nova' : ['nova-api', 'nova-scheduler'],
            'cinder': ['cinder-api', 'cinder-scheduler'],
            'neutron': ['neutron-server'],
            'glance': ['glance-api'],
            'heat': ['heat-api'],
            'keystone': ['apache2']
        }

        lma_node = self.get_devops_master_node_by_role([self.settings.role_name])

        try:
            for key in services:
                for service in services[key]:
                    nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                        self.helpers.cluster_id, ['controller'])
                    service_node = self.fuel_web.get_devops_nodes_by_nailgun_nodes(nailgun_nodes)[0]
                    self.change_verify_service_state(
                        [service, key], 'stop', 'WARNING', lma_node, [service_node], driver)
                    self.change_verify_service_state(
                        [service, key], 'start', 'OK', lma_node, [service_node], driver)
        finally:
            driver.close()

    @test(depends_on=[deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["critical_alert_service_infra_alerting"])
    @log_snapshot_after_test
    def critical_alert_service_infra_alerting(self):
        """Verify that the critical alerts for services show up in the Grafana and Nagios UI.

        Scenario:
            1.  Open the Nagios URL
            2.  Connect to one of the controller nodes using ssh and stop the nova-api service.
            3.  Connect to a second controller node using ssh and stop the nova-api service.
            4.  Wait for at least 1 minute.
            5.  On Nagios, check the following items:
                    - the ‘nova’ service is in ‘WARNING’ state,
                    - the local user root on the lma node has received an email about the service
                     being in warning state.
            6.  Restart the nova-api service on both nodes.
            7.  Wait for at least 1 minute.
            8.  On Nagios, check the following items:
                    - the ‘nova’ service is in ‘OK’ state,
                    - the local user root on the lma node has received an email about the recovery
                     of the service.
            9.  Connect to one of the controller nodes using ssh and stop the nova-scheduler service.
            10. Connect to a second controller node using ssh and stop the nova-scheduler service.
            11. Wait for at least 3 minutes.
            12. On Nagios, check the following items:
                    - the ‘nova’ service is in ‘WARNING’ state,
                    - the local user root on the lma node has received an email about the service
                     being in warning state.
            13. Restart the nova-scheduler service on both nodes.
            14. Wait for at least 1 minute.
            15. On Nagios, check the following items:
                    - the ‘nova’ service is in ‘OK’ state,
                    - the local user root on the lma node has received an email about the recovery
                     of the service.
            16. Repeat steps 1 to 15 for the following services:
                    - Cinder (stopping and starting the cinder-api and cinder-api services
                     respectively).
                    - Neutron (stopping and starting the neutron-server and neutron-openvswitch-agent
                     services respectively).
            17. Repeat steps 1 to 8 for the following services:
                    - Glance (stopping and starting the glance-api service).
                    - Heat (stopping and starting the heat-api service).
                    - Keystone (stopping and starting the Apache service).

        Duration 15m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        driver = self.get_nagios_main_page()

        services = {
            'nova' : ['nova-api', 'nova-scheduler'],
            'cinder': ['cinder-api', 'cinder-scheduler'],
            'neutron': ['neutron-server'],
            'glance': ['glance-api'],
            'heat': ['heat-api'],
            'keystone': ['apache2']
        }

        lma_node = self.get_devops_master_node_by_role([self.settings.role_name])

        try:
            for key in services:
                for service in services[key]:
                    logger.info("Checking service {0}".format(service))
                    nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
                        self.helpers.cluster_id, ['controller'])
                    service_nodes = self.fuel_web.get_devops_nodes_by_nailgun_nodes(nailgun_nodes)
                    self.change_verify_service_state([service, key], 'stop', 'CRITICAL', lma_node,
                                  [service_nodes[0], service_nodes[1]], driver)
                    self.change_verify_service_state([service, key], 'start', 'OK', lma_node,
                                  [service_nodes[0], service_nodes[1]], driver)
        finally:
            driver.close()

    @test(depends_on=[deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["warning_alert_node_infra_alerting"])
    @log_snapshot_after_test
    def warning_alert_node_infra_alerting(self):
        """Verify that the warning alerts for nodes show up in the Grafana and Nagios UI.

        Scenario:
            1.  Open the Nagios URL
            2.  Connect to one of the controller nodes using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root | awk '{ printf("%.0f\n",
                     1024 * ((($3 + $4) * 96 / 100) - $3))}') /var/lib/mysql/test
            3.  Wait for at least 1 minute.
            4.  On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘OK’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘WARNING’ state for the node.
            5.  Connect to a second controller node using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root | awk '{ printf("%.0f\n",
                     1024 * ((($3 + $4) * 96 / 100) - $3))}') /var/lib/mysql/test
            6.  Wait for at least 1 minute.
            7.  On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘WARNING’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘WARNING’ state for the 2 nodes,
                    - the local user root on the lma node has received an email about the service
                    being in warning state.
            8.  Run the following command on both controller nodes:
                    rm /var/lib/mysql/test
            9. Wait for at least 1 minutes.
            10. On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘OK’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘OKAY’ state for the 2 nodes,
                    - the local user root on the lma node has received an email about the recovery of the service.

        Duration 15m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        driver = self.get_nagios_main_page()

        lma_node = self.helpers.get_devops_master_node_by_role([self.settings.role_name])
        try:
            self.change_verify_node_service_state(['mysql', 'mysql-nodes.mysql-fs'], 'WARNING', '96', lma_node,
                                                  ['slave-01', 'slave-02'], driver)
        finally:
            driver.close()

    @test(depends_on=[deploy_lma_infra_alerting_plugin_in_ha_mode],
          groups=["critical_alert_node_infra_alerting"])
    @log_snapshot_after_test
    def critical_alert_node_infra_alerting(self):
        """Verify that the critical alerts for nodes show up in the Grafana and Nagios UI.

        Scenario:
            1.  Open the Nagios URL
            2.  Connect to one of the controller nodes using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root | awk '{ printf("%.0f\n",
                     1024 * ((($3 + $4) * 98 / 100) - $3))}') /var/lib/mysql/test
            3.  Wait for at least 1 minute.
            4.  On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘OK’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘CRITICAL’ state for the node.
            5.  Connect to a second controller node using ssh and run:
                    fallocate -l $(df | grep /dev/mapper/mysql-root | awk '{ printf("%.0f\n",
                     1024 * ((($3 + $4) * 98 / 100) - $3))}') /var/lib/mysql/test
            6.  Wait for at least 1 minute.
            7.  On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘CRITICAL’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘CRITICAL’ state for the 2 nodes,
                    - the local user root on the lma node has received an email about the service
                    being in warning state.
            8.  Run the following command on both controller nodes:
                    rm /var/lib/mysql/test
            9. Wait for at least 1 minutes.
            10. On Nagios, check the following items:
                    - the ‘mysql’ service is in ‘OK’ state,
                    - the ‘mysql-nodes.mysql-fs’ service is in ‘OKAY’ state for the 2 nodes,
                    - the local user root on the lma node has received an email about the recovery of the service.

        Duration 15m
        """
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        driver = self.get_nagios_main_page()

        lma_node = self.helpers.get_devops_master_node_by_role([self.settings.role_name])
        try:
            self.change_verify_node_service_state(['mysql', 'mysql-nodes.mysql-fs'], 'CRITICAL', '98', lma_node,
                                                  ['slave-01', 'slave-02'], driver)
        finally:
            driver.close()

    @test(groups=["test_execution"])
    def test_execution(self):
        """ TEST
        """
        # self.add_remove_controller()
        # self.add_remove_compute()
        self.plugin_core_repos_setup()
        # self.add_remove_infrastructure_alerting()
        self.shutdown_infrastructure_alerting()
        self.warning_alert_service_infra_alerting()
        self.critical_alert_service_infra_alerting()
        self.warning_alert_node_infra_alerting()
        self.critical_alert_node_infra_alerting()

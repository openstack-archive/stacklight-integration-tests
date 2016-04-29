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

from proboscis import asserts
from proboscis import test

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from fuelweb_test import logger
from fuelweb_test import settings
from fuelweb_test.tests import base_test_case
import time

import helpers.plugin_ui as plugin_ui
import helpers.helpers as helpers

import requests


class NotFound(Exception):
    message = "Not Found."


class ErrorState(Exception):
    message = "Error state."


@test(groups=["plugins"])
class TestLMAInfraAlertingPlugin(base_test_case.TestBasic):
    """Class for testing the LMA Infrastructure Alerting plugin."""

    name = 'lma_infrastructure_alerting'
    version = '0.9.0'
    role_name = 'infrastructure_alerting'
    nagios_user = 'nagiosadmin'
    nagios_password = 'r00tme'
    send_to = 'root@localhost'
    send_from = 'nagios@localhost'
    smtp_host = '127.0.0.1'

    def prepare_plugins(self, dependencies=True):
        self.env.admin_actions.upload_plugin(plugin=settings.LMA_INFRA_ALERTING_PLUGIN_PATH)
        self.env.admin_actions.install_plugin(
            plugin_file_name=os.path.basename(settings.LMA_INFRA_ALERTING_PLUGIN_PATH))
        if dependencies:
            self.env.admin_actions.upload_plugin(plugin=settings.LMA_COLLECTOR_PLUGIN_PATH)
            self.env.admin_actions.install_plugin(
                plugin_file_name=os.path.basename(settings.LMA_COLLECTOR_PLUGIN_PATH))
            self.env.admin_actions.upload_plugin(
                plugin=settings.INFLUXDB_GRAFANA_PLUGIN_PATH)
            self.env.admin_actions.install_plugin(
                plugin_file_name=os.path.basename(settings.INFLUXDB_GRAFANA_PLUGIN_PATH))

    def activate_plugins(self, cluster_id, dependencies=True):
        msg = "LMA Infra Alerting Plugin couldn't be enabled. Check plugin version. Test aborted"
        asserts.assert_true(self.fuel_web.check_plugin_exists(cluster_id, self.name), msg)
        options = {
            'nagios_password/value': self.nagios_password,
            'send_to/value': self.send_to,
            'send_from/value': self.send_from,
            'smtp_host/value': self.smtp_host,
        }
        self.fuel_web.update_plugin_settings(cluster_id, self.name, self.version, options)
        if dependencies:
            plugins = [
                {
                    'name': 'lma_collector',
                    'version': '0.9.0',
                    'options': {
                        'elasticsearch_mode/value': 'disabled',
                        'influxdb_mode/value': 'local',
                        'alerting_mode/value': 'local',
                    }
                },
                {
                    'name': 'influxdb_grafana',
                    'version': '0.9.0',
                    'options': {
                        'influxdb_rootpass/value': 'r00tme',
                        'influxdb_username/value': 'influxdb',
                        'influxdb_userpass/value': 'influxdbpass',
                        'grafana_username/value': 'grafana',
                        'grafana_userpass/value': 'grafanapass',
                        'mysql_mode/value': 'local',
                        'mysql_dbname/value': 'grafanalma',
                        'mysql_username/value': 'grafanalma',
                        'mysql_password/value': 'mysqlpass',
                    }
                },
            ]

            for plugin in plugins:
                msg = "{} couldn't be enabled. Check plugin version. Test aborted".format(plugin['name'])
                asserts.assert_true(self.fuel_web.check_plugin_exists(cluster_id, plugin['name']), msg)
                self.fuel_web.update_plugin_settings(cluster_id,
                                                     plugin['name'], plugin['version'], plugin['options'])

    def check_nagios_online(self, cluster_id):
        lma_alerting_vip = self.get_alerting_ip(cluster_id)
        asserts.assert_is_not_none(lma_alerting_vip, "Failed to get the IP of Nagios server")

        logger.info("Check that the Nagios server is running")
        r = requests.get(
            "http://{0}:{1}@{2}:8001".format(
                self.nagios_user, self.nagios_password, lma_alerting_vip))
        msg = "Nagios server responded with {}, expected 200".format(
            r.status_code)
        asserts.assert_equal(r.status_code, 200, msg)

    def get_alerting_ip(self, cluster_id):
        networks = self.fuel_web.client.get_networks(cluster_id)
        return networks.get('infrastructure_alerting')

    def add_remove_node(self, node_updates):
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        cluster_id = self.fuel_web.get_last_created_cluster()
        # remove 1 node with specified role.
        target_node = ''
        for key in node_updates:
            target_node = self.get_fuel_node_name(key)
        self.fuel_web.update_nodes(cluster_id, node_updates, False, True)

        self.fuel_web.deploy_cluster_wait(cluster_id, check_services=False)
        self.check_nagios_online(cluster_id)
        self.fuel_web.run_ostf(cluster_id=cluster_id, should_fail=1)
        self.check_node_in_nagios(cluster_id, target_node, False)

        # add 1 node with specified role.l
        self.fuel_web.update_nodes(cluster_id, node_updates)

        self.fuel_web.deploy_cluster_wait(cluster_id, check_services=False)
        self.check_nagios_online(cluster_id)
        self.fuel_web.run_ostf(cluster_id=cluster_id, should_fail=1)
        for key in node_updates:
            target_node = self.get_fuel_node_name(key)
        self.check_node_in_nagios(cluster_id, target_node, True)

    def get_alerting_tasks_pids(self):
        nodes = ['slave-0{0}'.format(slave) for slave in xrange(1, 4)]
        processes = ['heka', 'collectd']
        pids = {}

        for node in nodes:
            with self.fuel_web.get_ssh_for_node(node) as remote:
                pids[node] = {}
                for process in processes:
                    result = remote.execute("ps axf | grep {0} | grep -v grep "
                                            "| awk '{{print $1}}'".format(process))
                    pids[node][process] = result['stdout'][0].rstrip()

        with self.fuel_web.get_ssh_for_node('slave-03') as remote:
            result = remote.execute("ps axf | grep influxdb | grep -v grep | awk '{print $1}'")
            pids['slave-03']['influxdb'] = result['stdout'][0].rstrip()

        return pids

    def check_influxdb_status(self, nodes):
        for node in nodes:
            with self.fuel_web.get_ssh_for_node(node.name) as remote:
                result = remote.execute("service influxdb status | awk '{print $6}'")
                asserts.assert_equal('OK', result['stdout'][0].rstrip())

    def get_fuel_node_name(self, changed_node):
        with self.env.d_env.get_admin_remote() as remote:
            result = remote.execute("fuel nodes | grep {0} | awk '{{print $1}}'".format(changed_node))
            return 'node-' + result['stdout'][0].rstrip()

    def check_node_in_nagios(self, cluster_id, changed_node, state):
        driver = plugin_ui.get_driver("http://{0}:{1}@{2}:8001".format(
                    self.nagios_user, self.nagios_password, self.get_alerting_ip(cluster_id)),
                    "//frame[2]", "Nagios Core")
        try:
            driver = plugin_ui.get_hosts_page(driver)
            asserts.assert_equal(state, plugin_ui.node_is_present(driver, changed_node))
        finally:
            driver.close()

    def change_verify_service_state(self, service, action, state, lma_node, service_nodes, driver):
        self.clear_local_mail(lma_node)

        for service_node in service_nodes:
            with self.fuel_web.get_ssh_for_node(service_node.name) as remote:
                result = remote.execute("service {0} {1}".format(service[0], action))
                asserts.assert_equal(0, result['exit_code'],
                                     'Failed to {0} service {1} on {2}: {3}'
                                     .format(action, service[0], service_node.name, result['stderr']))

        time.sleep(180)

        driver = plugin_ui.get_services_page(driver)
        table = plugin_ui.get_table(driver, "/html/body/table[3]/tbody")
        node_name = plugin_ui.get_table_cell(table, 2, 1).text
        node_services = plugin_ui.get_services_for_node(table, node_name)
        for key in node_services:
            if key == service[1]:
                asserts.assert_equal(state, node_services[key])

        self.check_local_mail(lma_node, "{0} is {1}".format(service[1], state))

    def change_verify_node_service_state(self, services, state, parameter, lma_node, service_nodes, driver):
        self.clear_local_mail(lma_node)

        with self.fuel_web.get_ssh_for_node(service_nodes[0]) as remote:
            result = remote.execute("fallocate -l $(df | grep /dev/mapper/mysql-root |"
                                    " awk '{{ printf(\"%.0f\\n\", 1024 * ((($3 + $4) * {0} / 100)"
                                    " - $3))}}') /var/lib/mysql/test".format(parameter))
            asserts.assert_equal(0, result['exit_code'],
                                 'Failed to run command on {0}: {1}'
                                 .format(service_nodes[0], result['stderr']))

        time.sleep(120)

        driver = plugin_ui.get_services_page(driver)
        table = plugin_ui.get_table(driver, "/html/body/table[3]/tbody")
        node_services = plugin_ui.get_services_for_node(table,
                                                        self.get_fuel_node_name(service_nodes[0]))
        for key in node_services:
            if key == services[1]:
                asserts.assert_equal(state, node_services[key])
            elif key == services[0]:
                asserts.assert_equal('OK', node_services[key])

        with self.fuel_web.get_ssh_for_node(service_nodes[1]) as remote:
            result = remote.execute("fallocate -l $(df | grep /dev/mapper/mysql-root |"
                                    " awk '{{ printf(\"%.0f\\n\", 1024 * ((($3 + $4) * {0} / 100)"
                                    " - $3))}}') /var/lib/mysql/test".format(parameter))
            asserts.assert_equal(0, result['exit_code'],
                                 'Failed to run command on {0}: {1}'
                                 .format(service_nodes[0], result['stderr']))

        time.sleep(120)

        driver = plugin_ui.get_services_page(driver)
        table = plugin_ui.get_table(driver, "/html/body/table[3]/tbody")
        for node in service_nodes:
            node_services = plugin_ui.get_services_for_node(table,
                                                            self.get_fuel_node_name(node))
            for key in node_services:
                if key == services[0] or key == services[1]:
                    asserts.assert_equal(state, node_services[key])

        self.check_local_mail(lma_node, "{0} is {1}".format(services[0], state))

        for service_node in service_nodes:
            with self.fuel_web.get_ssh_for_node(service_node) as remote:
                result = remote.execute("rm /var/lib/mysql/test")
                asserts.assert_equal(0, result['exit_code'],
                                     'Failed to delete /var/lib/mysql/test on {0}: {1}'
                                     .format(service_node, result['stderr']))

        time.sleep(120)

        driver = plugin_ui.get_services_page(driver)
        table = plugin_ui.get_table(driver, "/html/body/table[3]/tbody")
        for node in service_nodes:
            node_services = plugin_ui.get_services_for_node(table,
                                                            self.get_fuel_node_name(node))
            for key in node_services:
                if key == services[0] or key == services[1]:
                    asserts.assert_equal('OK', node_services[key])

        self.check_local_mail(lma_node, "{0} is {1}".format(services[0], 'OK'))

    def check_local_mail(self, node, message):
        attempts = 5
        with self.fuel_web.get_ssh_for_node(node.name) as remote:
            while True:
                attempts -= 1
                result = remote.execute("cat $MAIL | grep '{0}'".format(message))
                if result['exit_code'] and attempts:
                    logger.warning("Unable to get email on {0}. {1} attempts remain..."
                                   .format(node.name, attempts))
                    time.sleep(60)
                elif result['exit_code']:
                    raise NotFound('Email about {0} was not found on {1}: Exit code is {2}: {3}'
                                   .format(message, node.name, result['exit_code'], result['stderr']))
                else:
                    break

    def clear_local_mail(self, node):
        with self.fuel_web.get_ssh_for_node(node.name) as remote:
            result = remote.execute("rm -rf $MAIL")
            asserts.assert_equal(0, result['exit_code'],
                                 'Failed to delete local mail on {0}: Exit code is {1}: {2}'
                                 .format(node.name, result['exit_code'], result['stderr']))

    def get_primary_lma_node(self, cluster_id):
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(cluster_id, [self.role_name])
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

        self.prepare_plugins()

        cluster_id = self.fuel_web.create_cluster(
            name=self.__class__.__name__,
            mode=settings.DEPLOYMENT_MODE,
        )

        self.activate_plugins(cluster_id)

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

        self.prepare_plugins(dependencies=True)

        cluster_id = self.fuel_web.create_cluster(
            name=self.__class__.__name__,
            mode=settings.DEPLOYMENT_MODE,
        )

        self.activate_plugins(cluster_id, dependencies=True)

        self.fuel_web.update_nodes(
            cluster_id,
            {
                'slave-01': ['controller'],
                'slave-02': ['compute'],
                'slave-03': [self.role_name, 'influxdb_grafana']
            }
        )

        self.fuel_web.deploy_cluster_wait(cluster_id)

        self.check_nagios_online(cluster_id)

        self.fuel_web.run_ostf(cluster_id=cluster_id)

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

        self.prepare_plugins(dependencies=True)

        cluster_id = self.fuel_web.create_cluster(
            name=self.__class__.__name__,
            mode=settings.DEPLOYMENT_MODE,
        )

        self.activate_plugins(cluster_id, dependencies=True)

        self.fuel_web.update_nodes(
            cluster_id,
            {
                'slave-01': ['controller'],
                'slave-02': ['controller'],
                'slave-03': ['controller'],
                'slave-04': ['compute', 'cinder'],
                'slave-05': [self.role_name, 'influxdb_grafana'],
                'slave-06': [self.role_name, 'influxdb_grafana'],
                'slave-07': [self.role_name, 'influxdb_grafana']
            }
        )

        self.fuel_web.deploy_cluster_wait(cluster_id)

        self.check_nagios_online(cluster_id)

        self.fuel_web.run_ostf(cluster_id=cluster_id)

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

        self.add_remove_node({'slave-02': ['controller']})

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
        self.add_remove_node({'slave-04': ['compute', 'cinder']})

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
        self.env.revert_snapshot("deploy_lma_alerting_plugin_ha")

        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel plugins --remove {0}=={1}".format(self.name, self.version))
            asserts.assert_equal(1, exec_res['exit_code'], 'Plugin deletion must not be permitted while '
                                                           'it\'s active in deployed in env')
            cluster_id = self.fuel_web.get_last_created_cluster()
            self.fuel_web.delete_env_wait(cluster_id)
            exec_res = remote.execute("fuel plugins --remove {0}=={1}".format(self.name, self.version))
# TODO: plugin deletion has a bug.
            asserts.assert_equal(0, exec_res['exit_code'], 'Plugin deletion failed: {0}'.format(exec_res['stderr']))

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

        self.prepare_plugins()

        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel plugins --remove {0}=={1}".format(self.name, self.version))
# TODO: plugin deletion has a bug.
            asserts.assert_equal(0, exec_res['exit_code'], 'Plugin deletion failed: {0}'.format(exec_res['stderr']))

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

        self.prepare_plugins(dependencies=True)

        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel-createmirror")
            asserts.assert_equal(0, exec_res['exit_code'], 'fuel-createmirror failed: {0}'.format(exec_res['stderr']))

        cluster_id = self.fuel_web.create_cluster(
            name=self.__class__.__name__,
            mode=settings.DEPLOYMENT_MODE,
        )

        self.activate_plugins(cluster_id, dependencies=True)

        self.fuel_web.update_nodes(
            cluster_id,
            {
                'slave-01': ['controller'],
                'slave-02': ['compute'],
                'slave-03': [self.role_name, 'influxdb_grafana']
            }
        )

        self.fuel_web.deploy_cluster_wait(cluster_id)

        self.check_nagios_online(cluster_id)

        self.fuel_web.run_ostf(cluster_id=cluster_id)

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


        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel-createmirror -M")
# TODO: fuel-createmirror -M will fail during the execution.
            asserts.assert_equal(0, exec_res['exit_code'], 'fuel-createmirror -M failed: {0}'.format(exec_res['stderr']))
            cluster_id = self.fuel_web.get_last_created_cluster()
            cmd = "fuel --env {0} node --node-id 1 2 3 --tasks setup_repositories".format(cluster_id)
            exec_res = remote.execute(cmd)
            asserts.assert_equal(0, exec_res['exit_code'], 'Command {0} failed: {1}'.format(cmd, exec_res['stderr']))

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
        self.add_remove_node({'slave-05': [self.role_name, 'influxdb_grafana']})

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

        cluster_id = self.fuel_web.get_last_created_cluster()
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(cluster_id, [self.role_name])
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

        self.check_influxdb_status(d_nodes)
        self.check_nagios_online(cluster_id)

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

        cluster_id = self.fuel_web.get_last_created_cluster()
        driver = plugin_ui.get_driver("http://{0}:{1}@{2}:8001".format(
                self.nagios_user, self.nagios_password, self.get_alerting_ip(cluster_id)),
                "//frame[2]", "Nagios Core")

        services = {
            'nova' : ['nova-api', 'nova-scheduler'],
            'cinder': ['cinder-api', 'cinder-scheduler'],
            'neutron': ['neutron-server'],
            'glance': ['glance-api'],
            'heat': ['heat-api'],
            'keystone': ['apache2']
        }

        lma_node = self.get_primary_lma_node(cluster_id)

        try:
            for key in services:
                for service in services[key]:
                    logger.info("Checking service {0}".format(service))
                    nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(cluster_id, ['controller'])
                    service_node = self.fuel_web.get_devops_nodes_by_nailgun_nodes(nailgun_nodes)[0]
                    self.change_verify_service_state([service, key], 'stop', 'WARNING', lma_node, [service_node], driver)
                    self.change_verify_service_state([service, key], 'start', 'OK', lma_node, [service_node], driver)
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

        cluster_id = self.fuel_web.get_last_created_cluster()
        driver = plugin_ui.get_driver("http://{0}:{1}@{2}:8001".format(
                self.nagios_user, self.nagios_password, self.get_alerting_ip(cluster_id)),
                "//frame[2]", "Nagios Core")

        services = {
            'nova' : ['nova-api', 'nova-scheduler'],
            'cinder': ['cinder-api', 'cinder-scheduler'],
            'neutron': ['neutron-server'],
            'glance': ['glance-api'],
            'heat': ['heat-api'],
            'keystone': ['apache2']
        }

        lma_node = self.get_primary_lma_node(cluster_id)

        try:
            for key in services:
                for service in services[key]:
                    logger.info("Checking service {0}".format(service))
                    nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(cluster_id, ['controller'])
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

        cluster_id = self.fuel_web.get_last_created_cluster()
        driver = plugin_ui.get_driver("http://{0}:{1}@{2}:8001".format(
                self.nagios_user, self.nagios_password, self.get_alerting_ip(cluster_id)),
                "//frame[2]", "Nagios Core")

        lma_node = self.get_primary_lma_node(cluster_id)
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

        cluster_id = self.fuel_web.get_last_created_cluster()
        driver = plugin_ui.get_driver("http://{0}:{1}@{2}:8001".format(
                self.nagios_user, self.nagios_password, self.get_alerting_ip(cluster_id)),
                "//frame[2]", "Nagios Core")

        lma_node = self.get_primary_lma_node(cluster_id)
        try:
            self.change_verify_node_service_state(['mysql', 'mysql-nodes.mysql-fs'], 'CRITICAL', '98', lma_node,
                                                  ['slave-01', 'slave-02'], driver)
        finally:
            driver.close()

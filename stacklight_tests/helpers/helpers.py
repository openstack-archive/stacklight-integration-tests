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

import os
import time
import urllib2

from devops.helpers import helpers
from fuelweb_test import logger
from proboscis import asserts

from stacklight_tests import settings


class NotFound(Exception):
    message = "Not Found."


def create_cluster(
        env, name, cluster_settings=None, mode=settings.DEPLOYMENT_MODE):
    return env.fuel_web.create_cluster(
        name=name, settings=cluster_settings, mode=mode)


class PluginHelper(object):
    """Class for common help functions."""

    def __init__(self, env):
        self.env = env
        self.fuel_web = self.env.fuel_web
        self._cluster_id = None

    @property
    def cluster_id(self):
        if self._cluster_id is None:
            try:
                self._cluster_id = self.fuel_web.get_last_created_cluster()
            except urllib2.URLError:
                raise EnvironmentError("No cluster was created.")
        return self._cluster_id

    @cluster_id.setter
    def cluster_id(self, value):
        self._cluster_id = value

    def prepare_plugin(self, plugin_path):
        """Upload and install plugin by path."""
        self.env.admin_actions.upload_plugin(plugin=plugin_path)
        self.env.admin_actions.install_plugin(
            plugin_file_name=os.path.basename(plugin_path))

    def activate_plugin(self, name, version, options):
        """Activate and check exist plugin."""
        msg = "Plugin couldn't be enabled. Check plugin version. Test aborted"
        asserts.assert_true(
            self.fuel_web.check_plugin_exists(self.cluster_id, name),
            msg)
        self.fuel_web.update_plugin_settings(
            self.cluster_id, name, version, options)

    def get_plugin_vip(self, vip_name):
        """Get plugin IP."""
        networks = self.fuel_web.client.get_networks(self.cluster_id)
        vip = networks.get('vips').get(vip_name, {}).get('ipaddr', None)
        asserts.assert_is_not_none(
            vip, "Failed to get the IP of {} server".format(vip_name))

        logger.debug("Check that {} is ready".format(vip_name))
        return vip

    def get_all_ready_nodes(self):
        return [node for node in
                self.fuel_web.client.list_cluster_nodes(self.cluster_id)
                if node["status"] == "ready"]

    def deploy_cluster(self, nodes_roles):
        """Method to deploy cluster with provided node roles."""
        self.fuel_web.update_nodes(self.cluster_id, nodes_roles)
        self.fuel_web.deploy_cluster_wait(self.cluster_id)

    def run_ostf(self, *args, **kwargs):
        self.fuel_web.run_ostf(self.cluster_id, *args, **kwargs)

    def add_node_to_cluster(self, node, redeploy=True, check_services=False):
        """Method to add node to cluster
        :param node: node to add to cluster
        :param redeploy: redeploy or just update settings
        :param check_services: run OSTF after redeploy or not
        """
        self.fuel_web.update_nodes(
            self.cluster_id,
            node,
        )
        if redeploy:
            self.fuel_web.deploy_cluster_wait(self.cluster_id,
                                              check_services=check_services)

    def remove_node_from_cluster(self, node, redeploy=True,
                                 check_services=False):
        """Method to remove node to cluster
            :param node: node to add to cluster
            :param redeploy: redeploy or just update settings
            :param check_services: run OSTF after redeploy or not
            """
        self.fuel_web.update_nodes(
            self.cluster_id,
            node,
            pending_addition=False, pending_deletion=True,
        )
        if redeploy:
            self.fuel_web.deploy_cluster_wait(self.cluster_id,
                                              check_services=check_services)

    def get_master_node_by_role(self, role_name, excluded_nodes_fqdns=()):
        nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.cluster_id, role_name)
        nodes = [node for node in nodes
                 if node['fqdn'] not in set(excluded_nodes_fqdns)]
        with self.fuel_web.get_ssh_for_nailgun_node(nodes[0]) as remote:
            stdout = remote.check_call(
                'pcs status cluster | grep "Current DC:"')["stdout"][0]
        for node in nodes:
            if node['fqdn'] in stdout:
                return node

    def hard_shutdown_node(self, fqdn):
        devops_node = self.fuel_web.get_devops_node_by_nailgun_fqdn(
            fqdn)
        msg = 'Node {0} has not become offline after hard shutdown'.format(
            devops_node.name)
        logger.info('Destroy node %s', devops_node.name)
        devops_node.destroy()
        logger.info('Wait a %s node offline status', devops_node.name)
        helpers.wait(lambda: not self.fuel_web.get_nailgun_node_by_devops_node(
            devops_node)['online'], timeout=60 * 5, timeout_msg=msg)

    @staticmethod
    def block_network_by_interface(interface):
        if interface.network.is_blocked:
            raise Exception('Network {0} is blocked'.format(interface))
        else:
            interface.network.block()

    @staticmethod
    def unblock_network_by_interface(interface):
        if interface.network.is_blocked:
            interface.network.unblock()
        else:
            raise Exception(
                'Network {0} was not blocked'.format(interface))

    def emulate_whole_network_disaster(self, delay_before_recover=5 * 60,
                                       wait_become_online=True):

        nodes = [node for node in self.env.d_env.get_nodes()
                 if node.driver.node_active(node)]

        networks_interfaces = nodes[1].interfaces

        for interface in networks_interfaces:
            self.block_network_by_interface(interface)

        time.sleep(delay_before_recover)

        for interface in networks_interfaces:
            self.unblock_network_by_interface(interface)

        if wait_become_online:
            self.fuel_web.wait_nodes_get_online_state(nodes[1:])

    def get_fuel_node_name(self, changed_node):
        with self.env.d_env.get_admin_remote() as remote:
            result = remote.execute("fuel nodes | grep {0} | awk "
                                    "'{{print $1}}'".format(changed_node))
            return 'node-' + result['stdout'][0].rstrip()

    def clear_local_mail(self, node):
        with self.fuel_web.get_ssh_for_node(node.name) as remote:
            result = remote.execute("rm -f $MAIL")
            asserts.assert_equal(0, result['exit_code'],
                                 'Failed to delete local mail on {0}: '
                                 'Exit code is {1}: {2}'
                                 .format(node.name, result['exit_code'],
                                         result['stderr']))

    def change_service_state(self, service, action, service_nodes):
        for service_node in service_nodes:
            with self.fuel_web.get_ssh_for_node(service_node.name) as remote:
                result = remote.execute("service {0} {1}"
                                        .format(service[0], action))
                asserts.assert_equal(0, result['exit_code'],
                                     'Failed to {0} service {1} on {2}: {3}'
                                     .format(action, service[0],
                                             service_node.name,
                                             result['stderr']))

        time.sleep(180)

    def check_local_mail(self, node, message, timeout=5 * 60):
        def check_mail():
            with self.fuel_web.get_ssh_for_node(node.name) as remote:
                result = remote.execute("cat $MAIL | grep '{0}'"
                                        .format(message))
                if not result['exit_code']:
                    return True
                else:
                    return False
        msg = "Email with {0} was not found on {1}".format(message, node.name)
        helpers.wait(check_mail, timeout=timeout, timeout_msg=msg)

    def fill_mysql_space(self, node, parameter):
        with self.fuel_web.get_ssh_for_node(node) as remote:
            result = remote.execute("fallocate -l $(df | grep "
                                    "/dev/mapper/mysql-root |"
                                    " awk '{{ printf(\"%.0f\\n\", "
                                    "1024 * ((($3 + $4) * {0} / 100)"
                                    " - $3))}}') /var/lib/mysql/test"
                                    .format(parameter))
            asserts.assert_equal(0, result['exit_code'],
                                 'Failed to run command on {0}: {1}'
                                 .format(node, result['stderr']))
        time.sleep(120)

    def clean_mysql_space(self, service_nodes):
        for service_node in service_nodes:
            with self.fuel_web.get_ssh_for_node(service_node) as remote:
                result = remote.execute("rm /var/lib/mysql/test")
                asserts.assert_equal(0, result['exit_code'],
                                     'Failed to delete '
                                     '/var/lib/mysql/test on {0}: {1}'
                                     .format(service_node, result['stderr']))

        time.sleep(120)

    def uninstall_plugin(self, plugin_name, plugin_version, exit_code=0,
                         msg=None):
        msg = msg or "Plugin {0} deletion failed: exit code is {1}"
        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel plugins --remove {0}=={1}"
                                      .format(plugin_name,
                                              plugin_version))
            asserts.assert_equal(exit_code, exec_res['exit_code'],
                                 msg.format(plugin_name, exit_code))

    def fuel_createmirror(self, option="", exit_code=0):
        logger.info("Executing 'fuel-createmirror' command.")
        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute(
                "fuel-createmirror {0}".format(option))
            asserts.assert_equal(exit_code, exec_res['exit_code'],
                                 'fuel-createmirror failed: {0}'
                                 .format(exec_res['stderr']))

    def fuel_createmirror_mos(self):
        logger.info("Executing 'fuel-createmirror -M' command.")
        # TODO(vushakov) fuel-createmirror -M will fail during the
        #  execution. CHANGED!
        self.fuel_createmirror("-M", 1)
        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute(
                "fuel nodes | grep ready | awk '{{print $1}}'")
            nodes = [ind.rstrip() for ind in exec_res['stdout']]
            ' '.join(nodes)
            cmd = "fuel --env {0} node --node-id " \
                  "{1} --tasks setup_repositories"\
                .format(self.helpers.cluster_id, nodes)
            exec_res = remote.execute(cmd)
            asserts.assert_equal(0, exec_res['exit_code'],
                                 'Command {0} failed: {1}'
                                 .format(cmd, exec_res['stderr']))

    # NOTE: Might become handy in influxdb check.
    def check_influxdb_status(self, nodes):
        for node in nodes:
            with self.fuel_web.get_ssh_for_node(node.name) as remote:
                result = remote.execute("service influxdb status | "
                                        "awk '{print $6}'")
                asserts.assert_equal('OK', result['stdout'][0].rstrip())

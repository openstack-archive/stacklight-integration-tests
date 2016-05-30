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
import re
import time
import urllib2

from devops.helpers import helpers
from fuelweb_test.helpers import checkers
from fuelweb_test import logger
from proboscis import asserts


PLUGIN_PACKAGE_RE = re.compile(r'([^/]+)-(\d+\.\d+)-(\d+\.\d+\.\d+)')


def get_plugin_name(filename):
    """Extract the plugin name from the package filename.

    :param filename: the plugin's filename.
    :type filename: str
    :returns: the plugin's name or None if not found
    :rtype: str
    """
    m = PLUGIN_PACKAGE_RE.search(filename or '')
    if m:
        return m.group(1)
    else:
        return None


def get_plugin_version(filename):
    """Extract the plugin version from the package filename.

    :param filename: the plugin's filename.
    :type filename: str
    :returns: the plugin's version or None if not found
    :rtype: str
    """
    m = PLUGIN_PACKAGE_RE.search(filename or '')
    if m:
        return m.group(3)
    else:
        return None


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

    def activate_plugin(self, name, version, options=None):
        """Enable and configure a plugin for the cluster.

        :param name: name of the plugin.
        :type name: str
        :param version: version of the plugin.
        :type name: str
        :param options: configuration of the plugin (optional).
        :type options: dict
        :returns: None
        """
        if options is None:
            options = {}
        msg = "Plugin {name} ({version}) couldn't be enabled.".format(
            name=name,
            version=version)
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

    def create_cluster(self, name=None, settings=None):
        """Create a cluster.

        :param name: name of the cluster.
        :type name: str
        :param settings: optional dict containing the cluster's configuration.
        :type settings: dict
        :returns: the cluster's id
        :rtype: str
        """
        if not name:
            name = self.__class__.__name__
        return self.env.fuel_web.create_cluster(
            name=name,
            settings=settings,
            mode='ha_compact')

    def deploy_cluster(self, nodes_roles):
        """Method to deploy cluster with provided node roles."""
        self.fuel_web.update_nodes(self.cluster_id, nodes_roles)
        self.fuel_web.deploy_cluster_wait(self.cluster_id)

    def run_ostf(self, *args, **kwargs):
        """Run the OpenStack health checks."""
        self.fuel_web.run_ostf(self.cluster_id, *args, **kwargs)

    def run_single_ostf(self, test_sets, test_name, *args, **kwargs):
        """Run a subset of the OpenStack health checks."""
        self.fuel_web.run_single_ostf_test(self.cluster_id, test_sets,
                                           test_name, *args, **kwargs)

    def verify_service(self, ip, service_name, count):
        """Check that a process is running on a host.

        :param ip: IP address of the host.
        :type ip: str
        :param service_name: the process name to match.
        :type service_name: str
        :param count: the number of processes to match.
        :type count: int
        """
        with self.env.d_env.get_ssh_to_remote(ip) as remote:
            checkers.verify_service(remote, service_name, count)

    def add_node_to_cluster(self, node, redeploy=True, check_services=False):
        """Add nodes to the cluster.

        :param node: list of nodes with their roles.
        :type: node: dict
        :param redeploy: whether to redeploy the cluster (default: True).
        :type redeploy: boolean
        :param check_services: run OSTF after redeploy (default: False).
        :type check_services: boolean
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
        """Remove nodes from the cluster.

        :param node: list of nodes to remove from the cluster.
        :type node: dict
        :param redeploy: whether to redeploy the cluster (default: True).
        :type redeploy: boolean
        :param check_services: run OSTF after redeploy (default: False).
        :type check_services: boolean
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
        """Return the node running as the Designated Controller (DC).
        """
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

    @staticmethod
    def full_vip_name(vip_name):
        return "".join(["vip__", vip_name])

    def get_node_with_vip(self, role_name, vip, exclude_node=None):
        nailgun_nodes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.cluster_id, role_name)
        lma_nodes = self.fuel_web.get_devops_nodes_by_nailgun_nodes(
            nailgun_nodes)
        lma_node = None
        if exclude_node:
            for node in lma_nodes:
                if node.name != exclude_node.name:
                    lma_node = node
                    break
        else:
            lma_node = lma_nodes[0]
        return self.fuel_web.get_pacemaker_resource_location(
            lma_node.name, vip)[0]

    def wait_for_vip_migration(self, old_master, role_name, vip,
                               timeout=5 * 60):
        logger.info('Waiting for the migration of VIP {}'.format(vip))
        msg = "VIP {0} has not been migrated away from {1}".format(
            vip, old_master)
        helpers.wait(
            lambda: old_master != self.get_node_with_vip(
                role_name, vip, exclude_node=old_master),
            timeout=timeout, timeout_msg=msg)

    def power_off_node(self, node):
        """Power off a node.
        """
        msg = 'Node {0} has not become offline after hard shutdown'.format(
            node.name)
        logger.info('Power off node %s', node.name)
        node.destroy()
        logger.info('Wait a %s node offline status', node.name)
        helpers.wait(lambda: not self.fuel_web.get_nailgun_node_by_devops_node(
            node)['online'], timeout=60 * 5, timeout_msg=msg)

    def emulate_whole_network_disaster(self, delay_before_recover=5 * 60,
                                       wait_become_online=True):
        """Simulate a full network outage for all nodes.

        :param delay_before_recover: outage interval in seconds (default: 300).
        :type delay_before_recover: int
        :param wait_become_online: whether to wait for nodes to be back online.
        :type wait_become_online: bool
        """
        nodes = [node for node in self.env.d_env.get_nodes()
                 if node.driver.node_active(node)]

        networks_interfaces = nodes[1].interfaces

        for interface in networks_interfaces:
            interface.network.block()

        time.sleep(delay_before_recover)

        for interface in networks_interfaces:
            interface.network.unblock()

        if wait_become_online:
            self.fuel_web.wait_nodes_get_online_state(nodes[1:])

    def uninstall_plugin(self, plugin_name, plugin_version, exit_code=0,
                         msg=None):
        """Remove a plugin.

        :param plugin_name: plugin's name.
        :type plugin_name: str
        :param plugin_version: plugin's version.
        :type plugin_version: str
        :param exit_code: expected exit code.
        :type exit_code: int
        :param msg: message in case of error.
        :type msg: str
        """
        logger.info("Trying to uninstall {name}({version}) plugin".format(
            name=plugin_name,
            version=plugin_version))
        msg = msg or "Plugin {0} deletion failed: exit code is {1}"
        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute("fuel plugins --remove"
                                      " {0}=={1}".format(plugin_name,
                                                         plugin_version))
            asserts.assert_equal(
                exit_code, exec_res['exit_code'],
                msg.format(plugin_name, exec_res['exit_code']))

    def check_plugin_cannot_be_uninstalled(self, plugin_name, plugin_version):
        """Check that the plugin cannot be uninstalled.

        :param plugin_name: plugin's name.
        :type plugin_name: str
        :param plugin_version: plugin's version.
        :type plugin_version: str
        """
        self.uninstall_plugin(
            plugin_name=plugin_name, plugin_version=plugin_version,
            exit_code=1,
            msg='{name}({version}) plugin deletion must not be allowed '
                'when it is deployed'.format(name=plugin_name,
                                             version=plugin_version))

    def get_fuel_node_name(self, changed_node):
        for node in self.fuel_web.client.list_cluster_nodes(self.cluster_id):
            if node["name"] == changed_node:
                return node["hostname"]
        return None

    def fuel_createmirror(self, option="", exit_code=0):
        logger.info("Executing 'fuel-createmirror' command.")
        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute(
                "fuel-createmirror {0}".format(option))
            asserts.assert_equal(exit_code, exec_res['exit_code'],
                                 'fuel-createmirror failed:'
                                 ' {0}'.format(exec_res['stderr']))

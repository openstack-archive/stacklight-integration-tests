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
import urllib2
<<<<<<< HEAD
=======
import time
>>>>>>> 42c69ad... Add base testcase class structure.

from fuelweb_test import logger
from proboscis import asserts

from stacklight_tests import settings


<<<<<<< HEAD
=======
class NotFound(Exception):
    message = "Not Found."


>>>>>>> 42c69ad... Add base testcase class structure.
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
        kwargs.update({"cluster_id": self.cluster_id})
        self.fuel_web.run_ostf(*args, **kwargs)
<<<<<<< HEAD
=======

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

#TODO: NEW METHODS

    def get_fuel_node_name(self, changed_node):
        with self.env.d_env.get_admin_remote() as remote:
            result = remote.execute("fuel nodes | grep {0} | awk '{{print $1}}'".format(changed_node))
            return 'node-' + result['stdout'][0].rstrip()

    def add_remove_node(self, node_updates, addition=True, deletion=False):
        self.fuel_web.update_nodes(self.cluster_id, node_updates, addition, deletion)
        self.fuel_web.deploy_cluster_wait(self.cluster_id, check_services=False)
        self.fuel_web.run_ostf(cluster_id=self.cluster_id, should_fail=1)

    def clear_local_mail(self, node):
        with self.fuel_web.get_ssh_for_node(node.name) as remote:
            result = remote.execute("rm -f $MAIL")
            asserts.assert_equal(0, result['exit_code'],
                                 'Failed to delete local mail on {0}: Exit code is {1}: {2}'
                                 .format(node.name, result['exit_code'], result['stderr']))

    def change_service_state(self, service, action, service_nodes):
        for service_node in service_nodes:
            with self.fuel_web.get_ssh_for_node(service_node.name) as remote:
                result = remote.execute("service {0} {1}".format(service[0], action))
                asserts.assert_equal(0, result['exit_code'],
                                     'Failed to {0} service {1} on {2}: {3}'
                                     .format(action, service[0], service_node.name, result['stderr']))

        time.sleep(180)

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
                    raise NotFound('Email with {0} was not found on {1}: Exit code is {2}: {3}'
                                   .format(message, node.name, result['exit_code'], result['stderr']))
                else:
                    break

    def fill_mysql_space(self, node, parameter):
        with self.fuel_web.get_ssh_for_node(node) as remote:
            result = remote.execute("fallocate -l $(df | grep /dev/mapper/mysql-root |"
                                    " awk '{{ printf(\"%.0f\\n\", 1024 * ((($3 + $4) * {0} / 100)"
                                    " - $3))}}') /var/lib/mysql/test".format(parameter))
            asserts.assert_equal(0, result['exit_code'],
                                 'Failed to run command on {0}: {1}'
                                 .format(node, result['stderr']))
        time.sleep(120)

    def clean_mysql_space(self, service_nodes):
        for service_node in service_nodes:
            with self.fuel_web.get_ssh_for_node(service_node) as remote:
                result = remote.execute("rm /var/lib/mysql/test")
                asserts.assert_equal(0, result['exit_code'],
                                     'Failed to delete /var/lib/mysql/test on {0}: {1}'
                                     .format(service_node, result['stderr']))

        time.sleep(120)

#TODO: TEMPORARY!
    def check_influxdb_status(self, nodes):
        for node in nodes:
            with self.fuel_web.get_ssh_for_node(node.name) as remote:
                result = remote.execute("service influxdb status | awk '{print $6}'")
                asserts.assert_equal('OK', result['stdout'][0].rstrip())
>>>>>>> 42c69ad... Add base testcase class structure.

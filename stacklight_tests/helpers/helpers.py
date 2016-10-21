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

import contextlib
import os
import re
import signal
import tempfile
import time
import urllib2

from devops.helpers import helpers
from fuelweb_test.helpers import checkers
from fuelweb_test.helpers import os_actions
from fuelweb_test import logger
from fuelweb_test import settings as conf
from proboscis import asserts
from stacklight_tests.helpers import remote_ops
from stacklight_tests import settings


PLUGIN_PACKAGE_RE = re.compile(r'([^/]+)-(\d+\.\d+)-(\d+\.\d+\.\d+)')


class NotFound(Exception):
    pass


class TimeoutException(Exception):
    pass


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


def get_fixture(name):
    """Return the full path to a fixture."""
    path = os.path.join(os.environ.get("WORKSPACE", "./"), "fixtures", name)
    if not os.path.isfile(path):
        raise NotFound("File {} not found".format(path))
    return path


def mos7_get_ssh_for_nailgun_node(target, node):
    return target.environment.d_env.get_ssh_to_remote(node['ip'])


def mos89_upload_plugin(target, plugin, source=None):
    target.orig_upload_plugin(plugin=plugin)


def mos89_install_plugin(target, plugin_file_name, source=None):
    target.orig_install_plugin(plugin_file_name=plugin_file_name)


def mos7_upload_plugin(target, plugin, source=None):
    with source.get_admin_remote() as remote:
        checkers.upload_tarball(
            remote, plugin, "/var")


def mos7_install_plugin(target, plugin_file_name, source=None):
    with source.get_admin_remote() as remote:
        checkers.install_plugin_check_code(
            remote, plugin=plugin_file_name)


class PluginHelper(object):
    """Class for common help functions."""

    def __init__(self, env):
        self.env = env
        self.fuel_web = self.env.fuel_web
        # This method does not exist in MOS 7.0
        # Using Monkey-patching on class. The benefit is that the code
        # modifications required to get everything to work properly
        # on every supported version os MOS is located here and there is no
        # need to modify any other existing code in the test suite
        wtype = type(self.fuel_web)
        if 'get_ssh_for_nailgun_node' not in wtype.__dict__:
            wtype.get_ssh_for_nailgun_node = mos7_get_ssh_for_nailgun_node
        # Do NOT patch other MOS 7.0 methods on self.env.admin_actions
        # class because it is not yet instanciated at this point
        # (see further down in prepare_plugin)
        self._cluster_id = None
        self.nailgun_client = self.fuel_web.client
        self._os_conn = None

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

    @property
    def os_conn(self):
        if self._os_conn is None:
            self._os_conn = os_actions.OpenStackActions(
                self.fuel_web.get_public_vip(self.cluster_id))
        return self._os_conn

    def prepare_plugin(self, plugin_path):
        """Upload and install plugin by path."""
        # This method does not exist in MOS 7.0
        # Using Monkey-patching on class
        atype = type(self.env.admin_actions)
        if 'upload_plugin' not in atype.__dict__:
            atype.upload_plugin = mos7_upload_plugin
            atype.install_plugin = mos7_install_plugin
            # Fallback mechanism for SSH to remote
            source = self.env.d_env
        else:
            # If already Monkey-patched then only set source
            if atype.upload_plugin.__name__ not in (
                    mos7_upload_plugin.__name__,
                    mos89_upload_plugin.__name__):
                # Need to keep original methods
                # because of interface change below
                atype.orig_upload_plugin = atype.upload_plugin
                atype.orig_install_plugin = atype.install_plugin
                atype.upload_plugin = mos89_upload_plugin
                atype.install_plugin = mos89_install_plugin
                source = None
            else:
                source = self.env.d_env
        # Changing interface of methods for genericity across MOS versions
        self.env.admin_actions.upload_plugin(plugin=plugin_path, source=source)
        self.env.admin_actions.install_plugin(
            plugin_file_name=os.path.basename(plugin_path), source=source)

    def get_plugin_setting(self, plugin, parameter):
        """Return the given parameter's value for the plugin.

        :param plugin: name of the plugin.
        :type plugin: str
        :param parameter: name of the parameter.
        :type parameter: str
        :returns: parameter's value
        """
        asserts.assert_true(
            self.fuel_web.check_plugin_exists(self.cluster_id, plugin),
            "Plugin {0} isn't found.".format(plugin))

        attributes = self.nailgun_client.get_cluster_attributes(
            self.cluster_id)
        attributes = attributes['editable'][plugin]

        value = None
        for item in attributes['metadata']['versions']:
            if (parameter in item and
                item['metadata']['plugin_id'] ==
                    attributes['metadata']['chosen_id']):
                value = item[parameter]['value']
                break
        asserts.assert_is_not_none(
            value, "Could not find parameter {0} for plugin {1}".format(
                parameter, plugin))
        return value

    def activate_plugin(self, name, version, options=None, strict=False):
        """Enable and configure a plugin for the cluster.

        :param name: name of the plugin.
        :type name: str
        :param version: version of the plugin.
        :type name: str
        :param options: configuration of the plugin (optional).
        :type options: dict
        :param strict: whether or not to fail when setting an unknown option
        (default: False).
        :type strict: boolean
        :returns: None
        """
        if options is None:
            options = {}
        msg = "Plugin {0} isn't found.".format(name)
        asserts.assert_true(
            self.fuel_web.check_plugin_exists(self.cluster_id, name),
            msg)

        logger.info("Updating settings for plugin {0} ({1}): {2}".format(
            name, version, options))
        attributes = self.nailgun_client.get_cluster_attributes(
            self.cluster_id)
        attributes = attributes['editable'][name]

        plugin_data = None
        # This key does not exist in MOS 7.0
        if 'versions' in attributes['metadata']:
            for item in attributes['metadata']['versions']:
                if item['metadata']['plugin_version'] == version:
                    plugin_data = item
                    break
            asserts.assert_is_not_none(
                plugin_data,
                "Plugin {0} ({1}) is not found".format(
                    name, version))
        else:
            plugin_data = attributes

        attributes['metadata']['enabled'] = True
        for option, value in options.items():
            path = option.split("/")
            for p in path[:-1]:
                if p in plugin_data:
                    plugin_option = plugin_data[p]
                else:
                    msg = "Plugin option {} not found".format(option)
                    if strict:
                        raise NotFound(msg)
                    logger.warn(msg)
                    plugin_option = None
                    break

            if plugin_option is not None:
                plugin_option[path[-1]] = value

        self.nailgun_client.update_cluster_attributes(self.cluster_id, {
            "editable": {name: attributes}
        })

    def get_vip_address(self, vip_name):
        """Get the virtual IP address.

        :param vip_name: name of the VIP.
        :type vip_name: str
        :returns: the VIP address in dotted-decimal notation
        :rtype: str
        """
        networks = self.nailgun_client.get_networks(self.cluster_id)
        vip = networks.get('vips').get(vip_name, {}).get('ipaddr', None)
        asserts.assert_is_not_none(
            vip, "Failed to get the IP of {} server".format(vip_name))

        logger.debug("VIP '{0}': {1}".format(vip_name, vip))
        return vip

    def get_all_ready_nodes(self):
        return [node for node in
                self.nailgun_client.list_cluster_nodes(self.cluster_id)
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
        # For MOS 7.0 as default network is Nova
        # The global environment variables should have been set via openrc file
        if 'NEUTRON_ENABLE' in conf.__dict__ and conf.NEUTRON_ENABLE:
            if not settings:
                settings = {}
            settings["net_provider"] = "neutron"
            settings["net_segment_type"] = conf.NEUTRON_SEGMENT_TYPE
        self._cluster_id = self.env.fuel_web.create_cluster(
            name=name,
            settings=settings,
            mode='ha_compact')
        return self._cluster_id

    def deploy_cluster(self, nodes_roles, verify_network=False,
                       update_interfaces=True, check_services=True,
                       timeout=7800):
        """Assign roles to nodes and deploy the cluster.

        :param nodes_roles: nodes to roles mapping.
        :type nodes_roles: dict
        :param verify_network: whether or not network verification should be
        run before the deployment (default: False).
        :type verify_network: boolean
        :param update_interfaces: whether or not interfaces should be updated
        before the deployment (default: True).
        :type update_interfaces: boolean
        :param check_services: whether or not OSTF tests should run after the
        deployment (default: True).
        :type check_services: boolean
        :returns: None
        """
        self.fuel_web.update_nodes(self.cluster_id, nodes_roles,
                                   update_interfaces=update_interfaces)
        if verify_network:
            self.fuel_web.verify_network(self.cluster_id)
        self.fuel_web.deploy_cluster_wait(self.cluster_id,
                                          check_services=check_services,
                                          timeout=timeout)

    def run_ostf(self, *args, **kwargs):
        """Run the OpenStack health checks."""
        self.fuel_web.run_ostf(self.cluster_id, *args, **kwargs)

    def run_single_ostf(self, test_sets, test_name, *args, **kwargs):
        """Run a subset of the OpenStack health checks."""
        self.fuel_web.run_single_ostf_test(self.cluster_id, test_sets,
                                           test_name, *args, **kwargs)

    def add_nodes_to_cluster(self, nodes, redeploy=True, check_services=False):
        """Add nodes to the cluster.

        :param nodes: list of nodes with their roles.
        :type: nodes: dict
        :param redeploy: whether to redeploy the cluster (default: True).
        :type redeploy: boolean
        :param check_services: run OSTF after redeploy (default: False).
        :type check_services: boolean
        """
        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes,
        )
        if redeploy:
            self.fuel_web.deploy_cluster_wait(self.cluster_id,
                                              check_services=check_services)

    def remove_nodes_from_cluster(self, nodes, redeploy=True,
                                  check_services=False):
        """Remove nodes from the cluster.

        :param nodes: list of nodes to remove from the cluster.
        :type nodes: dict
        :param redeploy: whether to redeploy the cluster (default: True).
        :type redeploy: boolean
        :param check_services: run OSTF after redeploy (default: False).
        :type check_services: boolean
        """
        self.fuel_web.update_nodes(
            self.cluster_id,
            nodes,
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
    def get_vip_resource_name(vip_name):
        """Return the name of the VIP resource.
        """
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

        :param node: Devops node.
        :type node: devops node instance
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

    def get_hostname_by_node_name(self, changed_node):
        node = self.fuel_web.get_nailgun_node_by_base_name(changed_node)
        if node is None:
            raise NotFound("Nailgun node with '{}' in name not found".format(
                changed_node))
        return node['hostname']

    def fuel_createmirror(self, option="", exit_code=0):
        cmd = "fuel-createmirror {0}".format(option)
        logger.info("Executing '{}' command.".format(cmd))
        with self.env.d_env.get_admin_remote() as remote:
            exec_res = remote.execute(cmd)
            asserts.assert_equal(
                exit_code, exec_res['exit_code'],
                'fuel-createmirror failed: {0}'.format(exec_res['stderr']))

    def replace_ubuntu_mirror_with_mos(self):
        cmds = ["fuel-mirror create -P ubuntu -G mos",
                "fuel-mirror apply --replace -P ubuntu -G mos"]
        logger.info("Executing '{}' commands.".format('\n'.join(cmds)))
        with self.env.d_env.get_admin_remote() as remote:
            for cmd in cmds:
                remote.check_call(cmd)

    def fuel_create_repositories(self, nodes):
        """Start task to setup repositories on provided nodes.

        :param nodes: list of nodes to run task on them
        :type nodes: list
        """
        nodes_ids = [str(node['id']) for node in nodes]
        cmd = (
            "fuel --env {env_id} "
            "node --node-id {nodes_ids} "
            "--tasks setup_repositories".format(
                env_id=self.cluster_id,
                nodes_ids=' '.join(nodes_ids))
        )
        logger.info(
            "Executing {cmd} command.".format(cmd=cmd))
        with self.env.d_env.get_admin_remote() as remote:
            remote.check_call(cmd)

    def run_tasks(self, nodes, tasks=None, start=None, end=None,
                  timeout=10 * 60):
        """Run a set of tasks on nodes and wait for completion.

        The list of tasks is provided using the 'tasks' parameter and it can
        also be specified using the 'start' and/or 'end' parameters. In the
        latter case, the method will compute the exact set of tasks to be
        executed.

        :param nodes: list of nodes that should run the tasks
        :type nodes: list
        :param tasks: list of tasks to run.
        :param tasks: list
        :param start: the task from where to start the deployment.
        :param start: str
        :param end: the task where to end the deployment.
        :param end: str
        :param timeout: number of seconds to wait for the tasks completion
        (default: 600).
        :param timeout: int
        """
        task_ids = []
        if tasks is not None:
            task_ids += tasks
        if start is not None or end is not None:
            task_ids += [
                t["id"] for t in self.nailgun_client.get_end_deployment_tasks(
                    self.cluster_id, end=end or '', start=start or '')]
        node_ids = ",".join([str(node["id"]) for node in nodes])
        logger.info("Running tasks {0} for nodes {1}".format(
            ",".join(task_ids), node_ids))
        result = self.nailgun_client.put_deployment_tasks_for_cluster(
            self.cluster_id, data=task_ids, node_id=node_ids)
        self.fuel_web.assert_task_success(result, timeout=timeout)

    def apply_maintenance_update(self):
        """Method applies maintenance updates on whole cluster."""
        logger.info("Applying maintenance updates on master node")
        self.env.admin_install_updates()

        logger.info("Applying maintenance updates on slaves")
        slaves_mu_script_url = (
            "https://github.com/Mirantis/tools-sustaining/"
            "raw/master/scripts/mos_apply_mu.py")

        path_to_mu_script = "/tmp/mos_apply_mu.py"

        with self.env.d_env.get_admin_remote() as remote:
            remote.check_call("wget {uri} -O {path}".format(
                uri=slaves_mu_script_url,
                path=path_to_mu_script)
            )

            remote.check_call(
                "python {path} "
                "--env-id={identifier} "
                "--user={username} "
                "--pass={password} "
                "--tenant={tenant_name} --update".format(
                    path=path_to_mu_script,
                    identifier=self.cluster_id,
                    **settings.KEYSTONE_CREDS
                )
            )

        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.cluster_id, roles=['controller', ])

        computes = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.cluster_id, roles=['compute', ])

        logger.info("Restarting all OpenStack services")

        logger.info("Restarting services on controllers")
        ha_services = (
            "p_heat-engine",
            "p_neutron-plugin-openvswitch-agent",
            "p_neutron-dhcp-agent",
            "p_neutron-metadata-agent",
            "p_neutron-l3-agent")
        non_ha_services = (
            "heat-api-cloudwatch",
            "heat-api-cfn",
            "heat-api",
            "cinder-api",
            "cinder-scheduler",
            "nova-objectstore",
            "nova-cert",
            "nova-api",
            "nova-consoleauth",
            "nova-conductor",
            "nova-scheduler",
            "nova-novncproxy",
            "neutron-server",
        )
        for controller in controllers:
            with self.fuel_web.get_ssh_for_nailgun_node(
                    controller) as remote:
                for service in ha_services:
                    remote_ops.manage_pacemaker_service(remote, service)
                for service in non_ha_services:
                    remote_ops.manage_service(remote, service)

        logger.info("Restarting services on computes")
        compute_services = (
            "neutron-plugin-openvswitch-agent",
            "nova-compute",
        )
        for compute in computes:
            with self.fuel_web.get_ssh_for_nailgun_node(compute) as remote:
                for service in compute_services:
                    remote_ops.manage_service(remote, service)

    @staticmethod
    def wait_for_resource_status(resource_client, resource, expected_status,
                                 timeout=180, interval=30):
        start = time.time()
        finish = start + timeout
        while start < finish:
            curr_state = resource_client.get(resource).status
            if curr_state == expected_status:
                return
            else:
                logger.debug(
                    "Instance is not in {} status".format(expected_status))
                time.sleep(interval)
                start = time.time()
        raise TimeoutException("Timed out waiting to become {}".format(
            expected_status))

    def get_fuel_release(self):
        version = self.nailgun_client.get_api_version()
        return version.get('release')

    def check_pacemaker_resource(self, resource_name, role, is_ha=True):
        """Check that the pacemaker resource is started on nodes with given
        role.
        :param resource_name: the name of the pacemaker resource
        :type resource_name: str
        :param role: the role of node when pacemaker is running
        :type role: str
        :returns: None
        """
        n_ctrls = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.cluster_id, [role])
        d_ctrls = self.fuel_web.get_devops_nodes_by_nailgun_nodes(n_ctrls)
        pcm_nodes = ' '.join(self.fuel_web.get_pcm_nodes(
            d_ctrls[0].name, pure=True)['Online'])
        logger.info("pacemaker nodes are {0}".format(pcm_nodes))
        resource_nodes = self.fuel_web.get_pacemaker_resource_location(
            d_ctrls[0].name, "{}".format(resource_name))
        if is_ha:
            for resource_node in resource_nodes:
                logger.info("Check resource [{0}] on node {1}".format(
                    resource_name, resource_node.name))
                config = self.fuel_web.get_pacemaker_config(resource_node.name)
                asserts.assert_not_equal(
                    re.search(
                        "Clone Set: clone_{0} \[{0}\]\s+Started: \[ {1} \]".
                        format(resource_name, pcm_nodes), config), None,
                    'Resource [{0}] is not properly configured'.format(
                        resource_name))
        else:
            asserts.assert_true(len(resource_nodes), 1)
            config = self.fuel_web.get_pacemaker_config(resource_nodes[0].name)
            logger.info("Check resource [{0}] on node {1}".format(
                resource_name, resource_nodes[0].name))
            asserts.assert_not_equal(
                re.search("{0}\s+\(ocf::fuel:{1}\):\s+Started".format(
                    resource_name, resource_name.split("_")[1]), config), None,
                'Resource [{0}] is not properly configured'.format(
                    resource_name))

    def update_neutron_advanced_configuration(self, option, value):
        """Method updates current cluster neutron advanced configuration option
        with provided value.

        :param option: option to set
        :type option: str
        :param value: value to set
        :type value: any
        :return: None
        """
        attributes = self.nailgun_client.get_cluster_attributes(
            self.cluster_id)
        nac_subdict = attributes['editable']['neutron_advanced_configuration']
        nac_subdict[option]['value'] = value
        self.nailgun_client.update_cluster_attributes(
            self.cluster_id, attributes)

    def create_image(self):

        with tempfile.TemporaryFile() as fp:
            fp.write('Test')
            fp.seek(0)
            image = self.os_conn.create_image(name='Redis',
                                              container_format='bare',
                                              disk_format='qcow2',
                                              data=fp)
        return image

    @staticmethod
    def verify(secs, func, step='', msg='', action='', duration=1000,
               sleep_for=10, *args, **kwargs):
        """Arguments:
        :secs: timeout time;
        :func: function to be verified;
        :step: number of test step;
        :msg: message that will be displayed if an exception occurs;
        :action: action that is performed by the method.
        """
        logger.info("STEP:{0}, verify action: '{1}'".format(step, action))
        now = time.time()
        time_out = now + duration
        try:
            with timeout(secs, action):
                while now < time_out:
                    result = func(*args, **kwargs)
                    if result or result is None:
                        return result
                    logger.info(
                        "{} is failed. Will try again".
                        format(action)
                    )
                    time.sleep(sleep_for)
                    now = time.time()
        except Exception as exc:
            logger.exception(exc)
            if type(exc) is AssertionError:
                msg = str(exc)
            raise AssertionError(
                "Step {} failed: {} Please refer to OpenStack logs for more "
                "details.".format(step, msg)
            )
        else:
            return result

    @contextlib.contextmanager
    def make_logical_db_unavailable(self, db_name, controller):
        """Context manager that renames all tables in provided database
        to make it unavailable and renames it back on exit.

        :param db_name: logical database name
        :type db_name: str
        :param controller: controller with MySQL database
        :type controller: nailgun node
        :returns: None, works as context manager
        """
        cmd = (
            "mysql -AN -e "
            "\"select concat("
            "'rename table {db_name}.', table_name, ' "
            "to {db_name}.' , {method}(table_name) , ';') "
            "from information_schema.tables "
            "where table_schema = '{db_name}';"
            "\" | mysql")

        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            remote.check_call(cmd.format(db_name=db_name, method="upper"))

        yield

        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            remote.check_call(cmd.format(db_name=db_name, method="lower"))


def _raise_TimeOut(sig, stack):
    raise TimeoutException()


class timeout(object):
    """Timeout context that will stop code running within context
    if timeout is reached

    >>with timeout(2):
    ...     requests.get("http://msdn.com")
    """

    def __init__(self, timeout, action):
        self.timeout = timeout
        self.action = action

    def __enter__(self):
        signal.signal(signal.SIGALRM, _raise_TimeOut)
        signal.alarm(self.timeout)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)  # disable the alarm
        if exc_type is not TimeoutException:
            return False  # never swallow other exceptions
        else:
            logger.info("Timeout {timeout}s exceeded for {call}".format(
                call=self.action,
                timeout=self.timeout
            ))
            msg = ("Time limit exceeded while waiting for {call} to "
                   "finish.").format(call=self.action)
            raise AssertionError(msg)

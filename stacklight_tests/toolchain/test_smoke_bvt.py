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
from fuelweb_test import settings
from proboscis import test

from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestToolchain(api.ToolchainApi):
    """Class for smoke testing the LMA Toolchain plugins."""

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["install_toolchain", "install", "toolchain", "smoke"])
    @log_snapshot_after_test
    def install_toolchain(self):
        """Install the LMA Toolchain plugins and check it exists

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create a cluster
            4. Check that the plugins can be enabled

        Duration 20m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["deploy_toolchain", "deploy", "toolchain", "smoke"])
    @log_snapshot_after_test
    def deploy_toolchain(self):
        """Deploy a cluster with the LMA Toolchain plugins

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 1 node with controller role
            5. Add 1 node with compute and cinder roles
            6. Add 1 node with plugin roles
            7. Deploy the cluster
            8. Check that LMA Toolchain plugins are running
            9. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain
        """
        self.check_run("deploy_toolchain")
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

        self.helpers.deploy_cluster(self.settings.base_nodes)

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_toolchain", is_make=True)

    @test(depends_on_groups=['prepare_slaves_9'],
          groups=["deploy_ha_toolchain", "deploy", "deploy_ha", "toolchain",
                  "smoke"])
    @log_snapshot_after_test
    def deploy_ha_toolchain(self):
        """Deploy a cluster with the LMA Toolchain plugins in HA mode

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 3 nodes with controller role
            5. Add 3 nodes with compute and cinder roles
            6. Add 3 nodes with plugin roles
            7. Deploy the cluster
            8. Check that LMA Toolchain plugins are running
            9. Run OSTF

        Duration 120m
        Snapshot deploy_ha_toolchain
        """
        self.check_run("deploy_ha_toolchain")
        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

        self.helpers.deploy_cluster(self.settings.full_ha_nodes)

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_ha_toolchain", is_make=True)

    @test(depends_on=[deploy_toolchain],
          groups=["uninstall_deployed_toolchain", "uninstall", "toolchain",
                  "smoke"])
    @log_snapshot_after_test
    def uninstall_deployed_toolchain(self):
        """Uninstall the LMA Toolchain plugins with a deployed environment

        Scenario:
            1.  Try to remove the plugins using the Fuel CLI
            2.  Check plugins can't be uninstalled on deployed cluster.
            3.  Remove the environment.
            4.  Remove the plugins.

        Duration 20m
        """
        self.env.revert_snapshot("deploy_toolchain")

        self.check_uninstall_failure()

        self.fuel_web.delete_env_wait(self.helpers.cluster_id)

        self.uninstall_plugins()

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["uninstall_toolchain", "uninstall", "toolchain", "smoke"])
    @log_snapshot_after_test
    def uninstall_toolchain(self):
        """Uninstall the LMA Toolchain plugins

        Scenario:
            1.  Install the plugins.
            2.  Remove the plugins.

        Duration 5m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.uninstall_plugins()

    @test(depends_on_groups=["prepare_slaves_9"],
          groups=["deploy_toolchain_ha_ceph_backend", "deploy", "deploy_ha",
                  "toolchain", "smoke"])
    @log_snapshot_after_test
    def deploy_toolchain_ha_ceph_backend(self):
        """Deploy plugins in HA mode with CEPH backend

        Scenario:
            1.  Create new environment with plugins and CEPH backend.
            2.  Add 3 controllers, 3 compute+ceph, 3 toolchain nodes
                and deploy the environment.
            3.  Check that plugins work.
            4.  Run OSTF.

        Duration 120m
        """

        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugins()

        data = {
            'volumes_ceph': True,
            'images_ceph': True,
            'volumes_lvm': False,
            'tenant': 'toolchainceph',
            'user': 'toolchainceph',
            'password': 'toolchainceph',
            'net_provider': 'neutron',
            'net_segment_type': settings.NEUTRON_SEGMENT['vlan']
        }

        self.helpers.create_cluster(name=self.__class__.__name__,
                                    settings=data)

        self.activate_plugins()

        node_roles = {
            'slave-01': ['controller'],
            'slave-02': ['controller'],
            'slave-03': ['controller'],
            'slave-04': ['compute', 'ceph-osd'],
            'slave-05': ['compute', 'ceph-osd'],
            'slave-06': ['compute', 'ceph-osd'],
            'slave-07': self.settings.stacklight_roles,
            'slave-08': self.settings.stacklight_roles,
            'slave-09': self.settings.stacklight_roles
        }

        self.helpers.deploy_cluster(node_roles)

        self.check_plugins_online()

        self.helpers.run_ostf()

    @test(depends_on_groups=["prepare_slaves_9"],
          groups=["deploy_toolchain_ha_platform_components", "deploy",
                  "deploy_ha", "toolchain", "smoke"])
    @log_snapshot_after_test
    def deploy_toolchain_ha_platform_components(self):
        """Deploy plugins with platform components

        Scenario:
            1.  Create new environment with plugins and enable Ceilometer,
                Sahara, Murano and Ironic.
            2.  Add 3 controllers+mongo, 3 compute+cinder+ironic,
                3 toolchain nodes and deploy the environment.
            3.  Check that plugins work.
            4.  Run OSTF.

        Duration 120m
        """

        self.env.revert_snapshot("ready_with_9_slaves")

        self.prepare_plugins()

        data = {
            'net_provider': 'neutron',
            'net_segment_type': settings.NEUTRON_SEGMENT['vlan'],
            'ironic': True,
            'sahara': True,
            'murano': True,
            'ceilometer': True,
            'tenant': 'toolchaincomponents',
            'user': 'toolchaincomponents',
            'password': 'toolchaincomponents'
        }

        self.helpers.create_cluster(name=self.__class__.__name__,
                                    settings=data)

        self.activate_plugins()

        node_roles = {
            'slave-01': ['controller', 'mongo'],
            'slave-02': ['controller', 'mongo'],
            'slave-03': ['controller', 'mongo'],
            'slave-04': ['compute', 'cinder', 'ironic'],
            'slave-05': ['compute', 'cinder', 'ironic'],
            'slave-06': ['compute', 'cinder', 'ironic'],
            'slave-07': self.settings.stacklight_roles,
            'slave-08': self.settings.stacklight_roles,
            'slave-09': self.settings.stacklight_roles
        }

        self.helpers.deploy_cluster(node_roles)

        self.check_plugins_online()

        self.helpers.run_ostf()

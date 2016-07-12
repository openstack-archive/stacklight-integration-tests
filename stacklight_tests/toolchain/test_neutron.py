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
class TestToolchainNeutron(api.ToolchainApi):
    """Class for testing the LMA Toolchain plugins when using different Neutron
    configurations.
    """

    def _deploy_with_neutron_configuration(self, caller, config=None,
                                           advanced_options=(), is_ha=False):
        self.check_run(caller)
        base_snapshot_name = "ready_with_3_slaves"
        nodes = self.settings.base_nodes
        if is_ha:
            base_snapshot_name = "ready_with_5_slaves"
            nodes = self.settings.os_semi_ha_nodes
        self.env.revert_snapshot(base_snapshot_name)

        self.prepare_plugins()

        self.helpers.create_cluster(
            name=caller,
            settings=config
        )

        self.activate_plugins()

        for option in advanced_options:
            self.helpers.update_neutron_advanced_configuration(*option)

        self.helpers.deploy_cluster(nodes,
                                    verify_network=True)
        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot(caller, is_make=True)

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["deploy_toolchain_neutron_vxlan", "deploy",
                  "toolchain", "network_configuration"])
    @log_snapshot_after_test
    def deploy_toolchain_neutron_vxlan(self):
        """Deploy a cluster with the LMA Toolchain plugins with
        Neutron VxLAN segmentation.

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster using VxLAN segmentation
            4. Add 1 node with controller role
            5. Add 1 node with compute and cinder roles
            6. Add 1 node with plugin roles
            7. Deploy the cluster
            8. Check that LMA Toolchain plugins are running
            9. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_neutron_vxlan
        """
        self._deploy_with_neutron_configuration(
            "deploy_toolchain_neutron_vxlan",
            config={
                "net_provider": "neutron",
                "net_segment_type": settings.NEUTRON_SEGMENT["tun"]
            }
        )

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["deploy_toolchain_neutron_vlan_dvr", "deploy",
                  "toolchain", "network_configuration"])
    @log_snapshot_after_test
    def deploy_toolchain_neutron_vlan_dvr(self):
        """Deploy a cluster with the LMA Toolchain plugins with
        Neutron VLAN segmentation and DVR feature.

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster using VLAN segmentation
            4. Set DVR option
            5. Add 1 node with controller role
            6. Add 1 node with compute and cinder roles
            7. Add 1 node with plugin roles
            8. Deploy the cluster
            9. Check that LMA Toolchain plugins are running
            10. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_neutron_vlan_dvr
        """
        options = ('neutron_dvr', True),
        self._deploy_with_neutron_configuration(
            "deploy_toolchain_neutron_vlan_dvr", advanced_options=options)

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["deploy_toolchain_neutron_vlan_l3ha", "deploy",
                  "toolchain", "network_configuration"])
    @log_snapshot_after_test
    def deploy_toolchain_neutron_vlan_l3ha(self):
        """Deploy a cluster with the LMA Toolchain plugins with
        Neutron VLAN segmentation and L3HA feature.

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster using VLAN segmentation
            4. Set L3HA option
            5. Add 1 node with controller role
            6. Add 1 node with compute and cinder roles
            7. Add 1 node with plugin roles
            8. Deploy the cluster
            9. Check that LMA Toolchain plugins are running
            10. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_neutron_vlan_l3ha
        """
        options = ('neutron_l3_ha', True),
        self._deploy_with_neutron_configuration(
            "deploy_toolchain_neutron_vlan_l3ha",
            advanced_options=options, is_ha=True)

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["deploy_toolchain_neutron_vxlan_l2pop_dvr", "deploy",
                  "toolchain", "network_configuration"])
    @log_snapshot_after_test
    def deploy_toolchain_neutron_vxlan_l2pop_dvr(self):
        """Deploy a cluster with the LMA Toolchain plugins with
        Neutron VxLAN segmentation and DVR feature.

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster using VxLAN segmentation
            4. Set L2pop and DVR options
            5. Add 1 node with controller role
            6. Add 1 node with compute and cinder roles
            7. Add 1 node with plugin roles
            8. Deploy the cluster
            9. Check that LMA Toolchain plugins are running
            10. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_neutron_vxlan_l2pop_dvr
        """

        options = (('neutron_l2_pop', True),
                   ('neutron_dvr', True))

        self._deploy_with_neutron_configuration(
            "deploy_toolchain_neutron_vxlan_l2pop_dvr",
            config={
                "net_provider": "neutron",
                "net_segment_type": settings.NEUTRON_SEGMENT["tun"]
            },
            advanced_options=options
        )

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["deploy_toolchain_neutron_vxlan_l3ha", "deploy",
                  "toolchain", "network_configuration"])
    @log_snapshot_after_test
    def deploy_toolchain_neutron_vxlan_l3ha(self):
        """Deploy a cluster with the LMA Toolchain plugins with
        Neutron VxLAN segmentation and L3HA feature.

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster using VxLAN segmentation
            4. Set L3HA option
            5. Add 1 node with controller role
            6. Add 1 node with compute and cinder roles
            7. Add 1 node with plugin roles
            8. Deploy the cluster
            9. Check that LMA Toolchain plugins are running
            10. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_neutron_vxlan_l3ha
        """

        options = ('neutron_l3_ha', True),

        self._deploy_with_neutron_configuration(
            "deploy_toolchain_neutron_vxlan_l3ha",
            config={
                "net_provider": "neutron",
                "net_segment_type": settings.NEUTRON_SEGMENT["tun"]
            },
            advanced_options=options, is_ha=True
        )

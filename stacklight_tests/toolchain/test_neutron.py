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
        self.check_run("deploy_toolchain_neutron_vxlan")
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(
            name="deploy_toolchain_neutron_vxlan",
            settings={
                "net_provider": "neutron",
                "net_segment_type": settings.NEUTRON_SEGMENT["tun"]
            }
        )

        self.activate_plugins()

        self.helpers.deploy_cluster(self.settings.base_nodes,
                                    verify_network=True)
        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_toolchain_neutron_vxlan", is_make=True)

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
from proboscis import asserts
from proboscis import test

from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestToolchain(api.ToolchainApi):
    """Class for system testing the LMA Toolchain plugins."""

    @test(depends_on_groups=["deploy_toolchain"],
          groups=["toolchain_createmirror_setup_repos",
                  "system", "toolchain", "createmirror"])
    @log_snapshot_after_test
    def toolchain_createmirror_setup_repos(self):
        """Check work after fuel-createmirror and setup core repositories.

        Scenario:
            1. Revert the snapshot with 3 deployed nodes
            2. Get pid of services which were launched
               on controller/compute/storage/etc nodes by plugin and store them
            3. Run the following commands on the master node:
               `fuel-mirror create -P ubuntu -G mos`
               `fuel-mirror apply --replace -P ubuntu -G mos`
            4. Run the following command on the master node:
               `fuel --env ENV_ID node --node-id Node1 ... NodeN --tasks setup_repositories` # noqa
            5. Check that all nodes are remain in ready status
            6. Get pid of services which were launched
               on controller/compute/storage/etc nodes by plugin
               and check that they wasn't changed from last check
            7. Run OSTF

        Duration 60m
        """
        self.env.revert_snapshot("deploy_toolchain")

        ready_nodes_before = self.helpers.get_all_ready_nodes()

        ready_nodes_hostnames_before = {node["hostname"]
                                        for node in ready_nodes_before}

        pids_before = self.get_pids_of_services()

        # NOTE(rpromyshlennikov): fuel-createmirror cmd is depricated
        # since fuel-8.0 release
        self.helpers.replace_ubuntu_mirror_with_mos()
        self.helpers.fuel_create_repositories(ready_nodes_before)

        ready_nodes_hostnames_after = {node["hostname"] for node
                                       in self.helpers.get_all_ready_nodes()}
        asserts.assert_equal(
            ready_nodes_hostnames_before, ready_nodes_hostnames_after,
            "List of ready nodes is not equal, "
            "before createmirror:{}, "
            "after createmirror: {}.".format(ready_nodes_hostnames_before,
                                             ready_nodes_hostnames_after)
        )

        pids_after = self.get_pids_of_services()
        asserts.assert_equal(
            pids_after, pids_before,
            "PIDs of services not equal, "
            "before createmirror:{}, "
            "after createmirror: {}.".format(pids_before, pids_after))

        self.check_plugins_online()
        self.helpers.run_ostf()

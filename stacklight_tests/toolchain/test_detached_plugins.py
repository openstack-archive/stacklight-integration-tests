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

from stacklight_tests.helpers import get_plugin_version
from stacklight_tests.settings import DETACH_RABBITMQ_PLUGIN_PATH
from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestToolchainDetachPlugins(api.ToolchainApi):
    """Class for testing the LMA Toolchain plugins in combination with the
    detach-* plugins."""

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["deploy_toolchain_with_detached_rabbitmq", "deploy",
                  "toolchain", "detached_plugins"])
    @log_snapshot_after_test
    def deploy_toolchain_with_detached_rabbitmq(self):
        """Deploy a cluster with the LMA Toolchain plugins and the
        detach-rabbitmq plugin.

        Scenario:
            1. Upload the plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 1 node with the controller role
            4. Add 1 node with the rabbitmq role
            5. Add 1 node with the compute and cinder roles
            6. Add 1 node with the plugin roles
            7. Deploy the cluster
            8. Check that LMA Toolchain plugins are running
            9. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_with_detached_rabbitmq
        """
        self.check_run("deploy_toolchain_with_detached_rabbitmq")
        self.env.revert_snapshot("ready_with_5_slaves")

        asserts.assert_is_not_none(
            DETACH_RABBITMQ_PLUGIN_PATH,
            "DETACH_RABBITMQ_PLUGIN_PATH variable should be set"
        )
        self.helpers.prepare_plugin(DETACH_RABBITMQ_PLUGIN_PATH)
        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()
        self.helpers.activate_plugin(
            'detach-rabbitmq', get_plugin_version(DETACH_RABBITMQ_PLUGIN_PATH))

        nodes = self.settings.base_nodes.copy()
        nodes['slave-04'] = ['standalone-rabbitmq']
        self.helpers.deploy_cluster(nodes)

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_toolchain_with_detached_rabbitmq",
                               is_make=True)

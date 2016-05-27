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

from stacklight_tests.helpers.helpers import get_plugin_name
from stacklight_tests.helpers.helpers import get_plugin_version
from stacklight_tests.settings import DETACH_DATABASE_PLUGIN_PATH
from stacklight_tests.settings import DETACH_RABBITMQ_PLUGIN_PATH
from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestToolchainDetachPlugins(api.ToolchainApi):
    """Class for testing the LMA Toolchain plugins in combination with the
    detach-* plugins.
    """

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
            5. Add 1 node with the rabbitmq role
            6. Add 1 node with the compute and cinder roles
            7. Add 1 node with the plugin roles
            8. Deploy the cluster
            9. Check that LMA Toolchain plugins are running
            10. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_with_detached_rabbitmq
        """
        self.check_run("deploy_toolchain_with_detached_rabbitmq")

        asserts.assert_is_not_none(
            DETACH_RABBITMQ_PLUGIN_PATH,
            "DETACH_RABBITMQ_PLUGIN_PATH variable should be set"
        )

        self._deploy_toolchain_with_detached_plugin(
            "deploy_toolchain_with_detached_rabbitmq",
            DETACH_RABBITMQ_PLUGIN_PATH,
            "standalone-rabbitmq"
        )

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["deploy_toolchain_with_detached_database", "deploy",
                  "toolchain", "detached_plugins"])
    @log_snapshot_after_test
    def deploy_toolchain_with_detached_database(self):
        """Deploy a cluster with the LMA Toolchain plugins and the
        detach-database plugin.

        Scenario:
            1. Upload the plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Add 1 node with the controller role
            5. Add 1 node with the database role
            6. Add 1 node with the compute and cinder roles
            7. Add 1 node with the plugin roles
            8. Deploy the cluster
            9. Check that LMA Toolchain plugins are running
            10. Run OSTF

        Duration 60m
        Snapshot deploy_toolchain_with_detached_database
        """
        self.check_run("deploy_toolchain_with_detached_database")

        asserts.assert_is_not_none(
            DETACH_DATABASE_PLUGIN_PATH,
            "DETACH_DATABASE_PLUGIN_PATH variable should be set"
        )

        self._deploy_toolchain_with_detached_plugin(
            "deploy_toolchain_with_detached_database",
            DETACH_DATABASE_PLUGIN_PATH,
            "standalone-database"
        )

    def _deploy_toolchain_with_detached_plugin(self, caller, plugin_path,
                                               plugin_role, ha=False):
        self.check_run(caller)
        if ha:
            self.env.revert_snapshot("ready_with_9_slaves")
        else:
            self.env.revert_snapshot("ready_with_5_slaves")

        self.helpers.prepare_plugin(plugin_path)
        self.prepare_plugins()

        self.helpers.create_cluster(name=caller)

        self.activate_plugins()
        self.helpers.activate_plugin(
            get_plugin_name(plugin_path), get_plugin_version(plugin_path))

        if ha:
            nodes = self.settings.full_ha_nodes.copy()
            # TODO(all): implement a mechanism to assign roles without
            # hard-coding the names of the nodes
            nodes['slave-06'] = [plugin_role]
        else:
            nodes = self.settings.base_nodes.copy()
            nodes['slave-04'] = [plugin_role]

        self.helpers.deploy_cluster(nodes)

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot(caller, is_make=True)

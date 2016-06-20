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
from plugin_settings import base_nodes
from proboscis import test
from stacklight_tests.ceilometer_redis import api


@test(groups=["plugins"])
class TestCeilometerRedis(api.CeilometerRedisPluginApi):
    """Class for smoke testing the Ceilometer-Redis plugin."""

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["install_ceilometer_redis", "install",
                  "ceilometer_redis", "smoke"])
    @log_snapshot_after_test
    def install_ceilometer_redis(self):
        """Install Ceilometer-Redis plugin and check it exists

        Scenario:
            1. Upload the Ceilometer-Redis plugin to the master node
            2. Install the plugin
            3. Create a cluster
            4. Check that the plugin can be enabled

        Duration 90m
        """
        self.env.revert_snapshot("ready_with_5_slaves")

        self.prepare_plugin()

        self.helpers.create_cluster(name=self.__class__.__name__,
                                    settings={'ceilometer': True})

        self.activate_plugin()

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["deploy_ceilometer_redis", "deploy",
                  "ceilometer_redis", "smoke"])
    @log_snapshot_after_test
    def deploy_ceilometer_redis(self):
        """Deploy a cluster with the Ceilometer-Redis plugin

        Scenario:
            1. Upload the Ceilometer-Redis plugin to the master node
            2. Install the plugin
            3. Create the cluster
            4. Add 3 node with controller with Mongo
            5. Add 2 node with compute and cinder roles
            7. Deploy the cluster
            8. Check that Ceilometer-Redis are running
            9. Run OSTF

        Duration 60m
        Snapshot deploy_ceilometer_redis
        """
        self.check_run("deploy_ceilometer_redis")
        self.env.revert_snapshot("ready_with_5_slaves")

        self.prepare_plugin()

        self.helpers.create_cluster(name=self.__class__.__name__,
                                    settings={'ceilometer': True})

        self.activate_plugin()

        self.helpers.deploy_cluster(base_nodes)

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_ceilometer_redis", is_make=True)

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["uninstall_ceilometer_redis", "uninstall",
                  "ceilometer_redis", "smoke"])
    @log_snapshot_after_test
    def uninstall_ceilometer_redis(self):
        """Uninstall the Ceilometer-Redis plugin

        Scenario:
            1.  Install the plugin.
            2.  Remove the plugin.

        Duration 5m
        """
        self.env.revert_snapshot("ready_with_5_slaves")

        self.prepare_plugin()

        self.uninstall_plugin()

    @test(depends_on_groups=[deploy_ceilometer_redis],
          groups=["uninstall_deployed_ceilometer_redis", "uninstall",
                  "ceilometer_redis", "smoke"])
    @log_snapshot_after_test
    def uninstall_deployed_ceilometer_redis(self):
        """Uninstall the Ceilometer-Redis plugin with a deployed
        environment

        Scenario:
            1.  Try to remove the plugin using the Fuel CLI
            2.  Check plugin can't be uninstalled on deployed cluster.
            3.  Remove the environment.
            4.  Remove the plugin.

        Duration 20m
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")

        self.check_uninstall_failure()

        self.fuel_web.delete_env_wait(self.helpers.cluster_id)

        self.uninstall_plugin()

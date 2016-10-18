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
from proboscis import test

from stacklight_tests.zabbix import api


@test(groups=["plugins"])
class TestZabbix(api.ZabbixApi):
    """Class for smoke testing the zabbix plugin."""

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["install_zabbix", "install", "zabbix", "smoke"])
    @log_snapshot_after_test
    def install_zabbix(self):
        """Install Zabbix plugin and check it exists

        Scenario:
            1. Upload Zabbix plugin to the master node
            2. Install the plugin
            3. Create a cluster
            4. Check that the plugin can be enabled

        Duration 20m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugin()

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["deploy_zabbix_monitoring_ha", "smoke", "zabbix"])
    @log_snapshot_after_test
    def deploy_zabbix_monitoring_ha(self):
        """Deploy environment with zabbix plugin

        Scenario:
            1. Upload Zabbix plugin to the master node.
            2. Install the plugin.
            3. Create a cluster.
            4. Enable the plugin.
            5. Add 3 nodes with controller role.
            6. Add 1 node with compute role.
            7. Add 1 node with cinder role.
            8. Deploy cluster.
            9. Check plugin health.
            10. Run OSTF.

        Duration 60m
        """
        self.check_run('deploy_zabbix_monitoring_ha')

        self.env.revert_snapshot("ready_with_5_slaves")

        self.prepare_plugin()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugin()

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['controller'],
                'slave-03': ['controller'],
                'slave-04': ['compute'],
                'slave-05': ['cinder']
            }, timeout=10800
        )

        self.check_plugin_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("deploy_zabbix_monitoring_ha", is_make=True)

    @test(depends_on_groups=["deploy_zabbix_monitoring_ha"],
          groups=["uninstall_deployed_zabbix", "uninstall", "zabbix", "smoke"])
    @log_snapshot_after_test
    def uninstall_deployed_zabbix(self):
        """Uninstall Zabbix plugin with a deployed environment

        Scenario:
            1.  Try to remove the plugins using the Fuel CLI
            2.  Check plugins can't be uninstalled on deployed cluster.
            3.  Remove the environment.
            4.  Remove the plugins.

        Duration 20m
        """
        self.env.revert_snapshot("deploy_zabbix_monitoring_ha")

        self.check_uninstall_failure()

        self.fuel_web.delete_env_wait(self.helpers.cluster_id)

        self.uninstall_plugin()

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["uninstall_zabbix_monitoring", "uninstall", "zabbix",
                  "smoke"])
    @log_snapshot_after_test
    def uninstall_zabbix_monitoring(self):
        """Uninstall Zabbix plugin

        Scenario:
            1.  Install the plugin.
            2.  Remove the plugin.

        Duration 5m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.uninstall_plugin()

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
class TestDestructiveZabbix(api.ZabbixApi):
    """Class for destructive testing of Zabbix plugin."""

    @test(depends_on_groups=["deploy_zabbix_monitoring_ha"],
          groups=["test_host_failover", "zabbix", "destructive"])
    @log_snapshot_after_test
    def test_host_failover(self):
        """Verify that zabbix-server will be started on another
         node in case of network failover.

        Scenario:
            1. Find node with active zabbix-server via crm status
            2. Shutdown the node.
            3. Check that zabbix is active on other node via crm status.
            4. Check response from zabbix via HTTP request

        Duration 15m
        """

        self.env.revert_snapshot("deploy_zabbix_monitoring_ha")

        self.check_plugin_failover()

        self.check_plugin_online()

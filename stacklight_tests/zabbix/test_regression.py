# coding=utf-8
#    Copyright 2017 Mirantis, Inc.
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

from proboscis import test

from stacklight_tests.zabbix import api

from fuelweb_test.helpers.decorators import log_snapshot_after_test


@test(groups=["plugins"])
class TestZabbixPluginRegression(api.ZabbixApi):
    """Class for regression testing the Zabbix plugin."""

    @test(depends_on_groups=["prepare_slaves_5"],
          groups=["deploy_zabbix_custom_hostnames", "zabbix", "regression",
                  "bugs", "bug_1633701"])
    @log_snapshot_after_test
    def deploy_zabbix_custom_hostnames(self):
        """Change default nodes hostnames and deploy environment

        Scenario:
            1. Copy Zabbix plugin to the Fuel Master
               node and install the plugin.
            2. Create an environment with enabled plugin in the
               Fuel Web UI and change nodes default hostnames.
            3. Deploy environment.
            4. Check plugin health.

        Duration 60m
        """
        self.env.revert_snapshot("ready_with_5_slaves")

        self.prepare_plugin()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugin()

        nodes_hostnames = {
            'slave-01': 'controller-A',
            'slave-02': 'controller-B',
            'slave-03': 'controller-C',
            'slave-04': 'compute-A',
            'slave-05': 'cinder-A'
        }

        self.helpers.deploy_cluster(
            {
                'slave-01': ['controller'],
                'slave-02': ['controller'],
                'slave-03': ['controller'],
                'slave-04': ['compute'],
                'slave-05': ['cinder']
            }, timeout=10800,
            check_services=False,
            nodes_hostnames=nodes_hostnames
        )

        self.helpers.verify_custom_hostnames(nodes_hostnames)

        self.check_plugin_online()

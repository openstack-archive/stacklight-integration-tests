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

from stacklight_tests.lma_collector import api


@test(groups=["plugins"])
class TestLMACollectorPlugin(api.LMACollectorPluginApi):
    """Class for smoke testing the LMA Collector plugin."""

    @test(depends_on_groups=["prepare_slaves_3"],
          groups=["install_lma_collector", "install",
                  "lma_collector", "smoke"])
    @log_snapshot_after_test
    def install_lma_collector_plugin(self):
        """Install the LMA Collector plugin

        Scenario:
            1. Upload the LMA Collector plugin to the master node
            2. Install the plugin
            3. Create a cluster
            4. Check that the plugin can be enabled

        Duration 20m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugin()

        self.create_cluster()

        self.activate_plugin()

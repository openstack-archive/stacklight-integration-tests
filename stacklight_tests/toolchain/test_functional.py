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

from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestFunctionalToolchain(api.ToolchainApi):
    """Class for functional testing the LMA Toolchain plugins."""

    @test(depends_on_groups=["deploy_ha_toolchain"],
          groups=["check_nova_logs_in_elasticsearch", "toolchain",
                  "functional"])
    @log_snapshot_after_test
    def check_nova_logs_in_elasticsearch(self):
        """Check that Nova logs are present in Elasticsearch

        Scenario:
            1. Revert snapshot with 9 deployed nodes in HA configuration
            2. Query Nova logs are present in current Elasticsearch index
            3. Check that Nova logs are collected from all controller and
               compute nodes

        Duration 10m
        """
        self.env.revert_snapshot("deploy_ha_toolchain")

        self.check_plugins_online()

        self.check_nova_logs()

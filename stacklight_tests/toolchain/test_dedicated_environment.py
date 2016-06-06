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

from stacklight_tests.helpers.helpers import get_fixture
from stacklight_tests.toolchain import api


@test(groups=["plugins"])
class TestToolchainDedicatedEnvironment(api.ToolchainApi):
    """Class for testing that the LMA Toolchain plugins can be installed in an
    dedicated environment.
    """

    @test(depends_on_groups=['prepare_slaves_5'],
          groups=["deploy_standalone_backends", "deploy",
                  "toolchain", "dedicated_environment"])
    @log_snapshot_after_test
    def deploy_standalone_backends(self):
        """Deploy a cluster with the Elasticsearch and InfluxDB backends.

        Scenario:
            1. Create the cluster
            2. Add 3 nodes with the elasticsearch_kibana and influxdb_grafana
            roles
            3. Deploy the cluster
            4. Check that backends are running

        Duration 60m
        Snapshot deploy_standalone_backends
        """
        self.check_run("deploy_standalone_backends")

        self.env.revert_snapshot("ready_with_5_slaves")

        # Relax the restrictions on the controller role to deploy an
        # environment without OpenStack nodes.
        with self.helpers.env.d_env.get_admin_remote() as remote:
            remote.upload(
                get_fixture("scripts/update_controller_role.sh"), "/tmp")
            remote.check_call(
                "bash -x /tmp/update_controller_role.sh",
                verbose=True)

        # NOTE: in this test case, we don't deploy the LMA Infrastructure
        # Alerting plugin because there is no support for the remote mode on
        # the collector side
        stacklight_roles = ["elasticsearch_kibana", "influxdb_grafana"]
        self.disable_plugin_by_id(self.LMA_INFRASTRUCTURE_ALERTING)

        self.prepare_plugins()

        self.helpers.create_cluster(name='deploy_standalone_backends')

        self.activate_plugins()

        self.helpers.deploy_cluster({
            'slave-03': stacklight_roles,
            'slave-04': stacklight_roles,
            'slave-05': stacklight_roles
        })

        self.check_plugins_online()

        self.env.make_snapshot("deploy_standalone_backends",
                               is_make=True)

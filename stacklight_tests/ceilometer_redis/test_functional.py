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
from stacklight_tests.ceilometer_redis import api


@test(groups=["plugins"])
class TestFunctionalCeilometerRedisPlugin(api.CeilometerRedisPluginApi):
    """Class for functional testing of Ceilometer-Redis plugin."""

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_plugin_services", "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def check_plugin_services(self):
        """Verify that the plugin services are running"""

        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            cmd = remote.execute("pcs resource | grep Stopped")['stdout']
        msg = 'Some of the services stopped'
        asserts.assert_true(len(cmd) == 0, msg)

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["central_agents_restart", "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def central_agents_restart(self):
        """Verify that all measurements are collected
        after stopping one of central agents.
        """

        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            remote.execute('pcs resource ban p_ceilometer-agent-central '
                           '$(hostname) --wait=100')
            cmd = remote.execute(' ps aux | grep -v grep | grep'
                                 ' -c ceilometer-polling')['stdout'][0]
            msg = "Error"
            asserts.assert_true(int(cmd) == 0, msg)
            self.helpers.run_ostf()

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_polling_logs", "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def check_polling_logs(self):
        """Check 'Joined partitioning group agent-central
        in the logs of central agent
        """

        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            cmd = remote.execute("cat /var/log/ceilometer/"
                                 "ceilometer-polling.log | "
                                 "grep 'Joined partitioning "
                                 "group central-global' ")['stdout']
        msg = 'Agent central has some problem.Please,' \
              'look logs for more details'
        asserts.assert_true(len(cmd) > 0, msg)

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_alarm_evaluator_logs", "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def check_alarm_evaluator_logs(self):
        """Check 'Joined partitioning group alarm_evaluator'
        in the logs of alarm evaluator.
        """

        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            cmd = remote.execute("cat /var/log/aodh/aodh-evaluator.log "
                                 "| grep 'Joined partitioning group"
                                 " alarm_evaluator' ")['stdout']
        msg = 'Alarm evaluator has some problem.Please,' \
              'look logs for more details'
        asserts.assert_true(len(cmd) > 0, msg)

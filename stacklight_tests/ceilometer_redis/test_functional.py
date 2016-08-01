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
import time

from proboscis import asserts
from proboscis import test

from fuelweb_test.helpers.decorators import log_snapshot_after_test
from stacklight_tests.ceilometer_redis import api


@test(groups=["plugins"])
class TestFunctionalCeilometerRedisPlugin(api.CeilometerRedisPluginApi):
    """Class for functional testing of Ceilometer-Redis plugin."""

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["central_agents_restart", "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def central_agents_restart_ceilometer_redis(self):
        """Verify that all measurements are collected
        after stopping one of central agents.
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            remote.execute('pcs resource ban p_ceilometer-agent-central '
                           '$(hostname) --wait=100')
            result = remote.execute(' ps aux | grep -v grep | grep'
                                    ' -c ceilometer-polling')['stdout'][0]
        msg = "Agent central wasn't stopped"
        asserts.assert_true(int(result) == 0, msg)
        self.run_ostf()

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_polling_logs", "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def check_polling_logs_ceilometer_redis(self):
        """Check 'Joined partitioning group agent-central'
        in the aodh-evaluator logs.
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")
        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])
        for controller in controllers:
            with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
                result = remote.execute("cat /var/log/ceilometer/"
                                        "ceilometer-polling.log | "
                                        "grep 'Joined partitioning "
                                        "group central-global' ")['stdout']
            msg = ("'Joined partitioning group agent-central' "
                   "not found in ceilometer-polling.log")
            asserts.assert_true(len(result) > 0, msg)

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_alarm_evaluator_logs", "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def check_alarm_evaluator_logs_ceilometer_redis(self):
        """Check 'Joined partitioning group alarm_evaluator'
        in the ceilometer-polling logs.
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")
        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])
        for controller in controllers:
            with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
                result = remote.execute("cat /var/log/aodh/aodh-evaluator.log "
                                        "| grep 'Joined partitioning group"
                                        " alarm_evaluator' ")['stdout']
            msg = ("'Joined partitioning group alarm_evaluator' not found in "
                   "aodh-evaluator.log")
            asserts.assert_true(len(result) > 0, msg)

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_samples_ceilometer_redis", "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def check_samples_ceilometer_redis(self):
        """Check that for one polling interval only one 'image' sample exists.
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")
        self.check_sample_count(expected_count=1)

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_samples_with_one_agent_ceilometer_redis",
                  "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def check_samples_with_one_agent_ceilometer_redis(self):
        """Check samples after ban two of three ceilometer-agent-central.
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")
        controllers = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])
        for controller in controllers[:2]:
            with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
                remote.execute('pcs resource ban p_ceilometer-agent-central '
                               '$(hostname) --wait=100')
                result = remote.execute(' ps aux | grep -v grep | grep'
                                        ' -c ceilometer-polling')['stdout'][0]
            msg = "Agent central wasn't stopped"
            asserts.assert_true(int(result) == 0, msg)
            self.check_sample_count(expected_count=1)

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_central_disabled_coordination_ceilometer_redis",
                  "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def check_central_disabled_coordination_ceilometer_redis(self):
        """Check that after disable coordination we have 3
        image sample for the one polling period.
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")
        self.disable_coordination()
        self.check_sample_count(expected_count=3)

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_alarms_ceilometer_redis",
                  "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def check_alarms_ceilometer_redis(self):
        """Check that for one evaluation interval, alarm evaluators evaluated
        is joint set of alarms.
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")
        self.create_alarms()
        time.sleep(70)
        self.check_alarms_log()

    @test(depends_on_groups=["deploy_ceilometer_redis"],
          groups=["check_alarms_disabled_ceilometer_redis",
                  "ceilometer_redis",
                  "functional"])
    @log_snapshot_after_test
    def check_alarms_disabled_ceilometer_redis(self):
        """Check environment work after disable one of aodh-evaluator services.
        """
        self.env.revert_snapshot("deploy_ceilometer_redis")
        self.create_alarms()
        time.sleep(70)
        self.check_alarms_log()
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            remote.execute("pcs resource ban p_aodh-evaluator $(hostname) "
                           "--wait=100")
            result = remote.execute("ps aux | grep -v grep | "
                                    "grep -c aodh-evaluator")['stdout'][0]
        msg = "Aodh-evaluator wasn't stopped"
        asserts.assert_true(int(result) == 0, msg)
        self.check_alarms_log()

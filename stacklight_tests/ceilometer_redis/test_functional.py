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

import datetime
import tempfile
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
    def central_agents_restart(self):
        """Verify that all measurements are collected
        after stopping one of central agents.
        """

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
    def check_polling_logs(self):
        """Check 'Joined partitioning group agent-central'
        in the logs
        """

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
    def check_alarm_evaluator_logs(self):
        """Check 'Joined partitioning group alarm_evaluator'
        in the logs
        """

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

        with tempfile.TemporaryFile() as fp:
            fp.write('Test')
            fp.seek(0)
            image = self.helpers.os_conn.create_image(name='Redis',
                                                      container_format='bare',
                                                      disk_format='qcow2',
                                                      data=fp)
        time.sleep(2 * self.settings.polling_interval)
        f = datetime.datetime.now() - datetime.timedelta(seconds=600)
        query = [{'field': 'timestamp', 'op': 'ge', 'value': f.isoformat()},
                 {'field': 'resource_id', 'op': 'eq', 'value': image.id}]
        sample_count = self.ceilometer.statistics.list(
            q=query, meter_name='image')[0].count
        msg = ("Expected 1 image sample for one "
               "polling period , got : {0} .").format(sample_count)
        asserts.assert_true(sample_count == 1, msg)

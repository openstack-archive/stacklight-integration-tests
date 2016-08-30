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
from stacklight_tests.helpers import helpers
from stacklight_tests.kafka_plugin import api

from proboscis import asserts
from proboscis import test

import time


@test(groups=["plugins"])
class TestFuncKafkaPlugin(api.KafkaPluginApi):

    @test(depends_on_groups=["deploy_kafka"],
          groups=["fff", "kafka", "functional"])
    @log_snapshot_after_test
    def check_messages(self):
        kafka_node = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, roles=["kafka"])[0]
        with self.fuel_web.get_ssh_for_nailgun_node(kafka_node) as remote:
            remote.upload(helpers.get_fixture("test.py"), "/tmp")
            remote.check_call("python  /tmp/test.py")
            time.sleep(2)
            result = remote.execute('cat /tmp/log.txt | grep "error" ')
            ['stdout']
        msg = "Quantity of recieved messages does't correspond quantity " \
              "of sent"
        asserts.assert_true(len(result) == 0, msg)

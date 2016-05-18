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

from stacklight_tests.helpers import helpers
from stacklight_tests import settings


name = 'lma_collector'
role_name = []  # NOTE(rpromyshlennikov): there is no role name
# because lma collector is installed on all nodes in cluster
plugin_path = settings.LMA_COLLECTOR_PLUGIN_PATH
version = helpers.get_plugin_version(plugin_path)

# NOTE(vgusev): this options will be changed after merging of
# https://review.openstack.org/#/c/316812/
bvt_options = {
    'environment_label/value': 'deploy_lma_toolchain',
    'elasticsearch_mode/value': 'remote',
    'influxdb_mode/value': 'remote',
    'alerting_mode/value': 'local',
    'elasticsearch_address/value': '127.0.0.1',
    'influxdb_address/value': '127.0.0.1'
}

toolchain_options = {
    'environment_label/value': 'deploy_lma_toolchain',
    'elasticsearch_mode/value': 'local',
    'influxdb_mode/value': 'local',
    'alerting_mode/value': 'local'
}

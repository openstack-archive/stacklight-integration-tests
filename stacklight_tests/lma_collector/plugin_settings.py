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

from stacklight_tests import settings


name = 'lma_collector'
version = '0.9.0'
role_name = []  # NOTE(rpromyshlennikov): there is no role name
# because lma collector is installed on all nodes in cluster
plugin_path = settings.LMA_COLLECTOR_PLUGIN_PATH

options = {
    'environment_label/value': 'deploy_lma_toolchain',
    'elasticsearch_mode/value': 'remote',
    'influxdb_mode/value': 'remote',
    'alerting_mode/value': 'local',
    'elasticsearch_address/value': '1.2.3.4',
    'influxdb_address': '1.2.3.4'
}

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

name = 'ceilometer-redis'
plugin_path = settings.CEILOMETER_REDIS_PLUGIN_PATH
version = helpers.get_plugin_version(plugin_path)
default_options = {}
base_nodes = {
    'slave-01': ['controller', 'mongo'],
    'slave-02': ['controller', 'mongo'],
    'slave-03': ['controller', 'mongo'],
    'slave-04': ['compute', 'cinder'],
    'slave-05': ['compute', 'cinder']
}

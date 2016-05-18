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

from stacklight_tests.elasticsearch_kibana import (
    plugin_settings as elasticsearch_settings)
from stacklight_tests.influxdb_grafana import (
    plugin_settings as influxdb_settings)
from stacklight_tests.lma_collector import (
    plugin_settings as collector_settings)
from stacklight_tests.lma_infrastructure_alerting import (
    plugin_settings as infrastructure_alerting_settings)

name = 'toolchain'
version = '0.9.0'

role_name = (elasticsearch_settings.role_name + influxdb_settings.role_name +
             collector_settings.role_name +
             infrastructure_alerting_settings.role_name)

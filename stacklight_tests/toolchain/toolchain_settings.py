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

stacklight_roles = (elasticsearch_settings.role_name +
                    influxdb_settings.role_name +
                    collector_settings.role_name +
                    infrastructure_alerting_settings.role_name)

OKAY = 0
WARN = 1
UNKW = 2
CRIT = 3
DOWN = 4

base_nodes = {
    'slave-01': ['controller'],
    'slave-02': ['compute', 'cinder'],
    'slave-03': stacklight_roles
}

nova_nodes = {
    'slave-01': ['controller', 'cinder'],
    'slave-02': ['compute'],
    'slave-03': ['compute'],
    'slave-04': ['compute'],
    'slave-05': ['compute'],
    'slave-06': stacklight_roles
}

ha_controller_nodes = {
    'slave-01': ['controller'],
    'slave-02': ['controller'],
    'slave-03': ['controller'],
    'slave-04': ['compute', 'cinder'],
    'slave-05': stacklight_roles,
}

full_ha_nodes = {
    'slave-01': ['controller'],
    'slave-02': ['controller'],
    'slave-03': ['controller'],
    'slave-04': ['compute', 'cinder'],
    'slave-05': ['compute', 'cinder'],
    'slave-06': ['compute', 'cinder'],
    'slave-07': stacklight_roles,
    'slave-08': stacklight_roles,
    'slave-09': stacklight_roles
}

mysql_fs = "/dev/mapper/mysql-root"
mysql_fs_alarm_test_file = "/var/lib/mysql/bigfile"

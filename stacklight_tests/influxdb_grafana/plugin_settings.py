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


name = 'influxdb_grafana'
role_name = ['influxdb_grafana']
vip_name = 'influxdb'
plugin_path = settings.INFLUXDB_GRAFANA_PLUGIN_PATH
version = helpers.get_plugin_version(plugin_path)

influxdb_db_name = "lma"
influxdb_user = 'influxdb'
influxdb_pass = 'influxdbpass'
influxdb_rootuser = 'root'
influxdb_rootpass = 'r00tme'

grafana_user = 'grafana'
grafana_pass = 'grafanapass'

mysql_mode = 'local'
mysql_dbname = 'grafanalma'
mysql_user = 'grafanalma'
mysql_pass = 'mysqlpass'

default_options = {
    'influxdb_rootpass/value': influxdb_rootpass,
    'influxdb_username/value': influxdb_user,
    'influxdb_userpass/value': influxdb_pass,
    'grafana_username/value': grafana_user,
    'grafana_userpass/value': grafana_pass,
    'mysql_mode/value': mysql_mode,
    'mysql_dbname/value': mysql_dbname,
    'mysql_username/value': mysql_user,
    'mysql_password/value': mysql_pass,
}

toolchain_options = default_options

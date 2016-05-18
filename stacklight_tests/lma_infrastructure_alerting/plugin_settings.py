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

name = 'lma_infrastructure_alerting'
role_name = ['infrastructure_alerting']
vip_name = 'infrastructure_alerting_mgmt_vip'
plugin_path = settings.LMA_INFRA_ALERTING_PLUGIN_PATH
version = helpers.get_plugin_version(plugin_path)

nagios_user = 'nagiosadmin'
nagios_password = 'r00tme'
send_to = 'root@localhost'
send_from = 'nagios@localhost'
smtp_host = '127.0.0.1'

default_options = {
    'nagios_password/value': nagios_password,
    'send_to/value': send_to,
    'send_from/value': send_from,
    'smtp_host/value': smtp_host,
}

toolchain_options = default_options

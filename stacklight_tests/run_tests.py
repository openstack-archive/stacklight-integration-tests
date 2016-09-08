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

import os

from nose import plugins
from paramiko import transport


class CloseSSHConnectionsPlugin(plugins.Plugin):
    """Closes all paramiko's ssh connections after each test case

    Plugin fixes proboscis disability to run cleanup of any kind.
    'afterTest' calls _join_lingering_threads function from paramiko,
    which stops all threads (set the state to inactive and joins for 10s)
    """
    name = 'closesshconnections'

    def options(self, parser, env=os.environ):
        super(CloseSSHConnectionsPlugin, self).options(parser, env=env)

    def configure(self, options, conf):
        super(CloseSSHConnectionsPlugin, self).configure(options, conf)
        self.enabled = True

    def afterTest(self, *args, **kwargs):
        transport._join_lingering_threads()


def import_tests():
    from stacklight_tests.ceilometer_redis import test_functional  # noqa
    from stacklight_tests.ceilometer_redis import test_smoke_bvt  # noqa
    from stacklight_tests.ceilometer_redis import test_system  # noqa
    from stacklight_tests.elasticsearch_kibana import test_smoke_bvt  # noqa
    from stacklight_tests.elasticsearch_kibana import test_system  # noqa
    from stacklight_tests.influxdb_grafana import test_destructive  # noqa
    from stacklight_tests.influxdb_grafana import test_functional  # noqa
    from stacklight_tests.influxdb_grafana import test_smoke_bvt  # noqa
    from stacklight_tests.influxdb_grafana import test_system  # noqa
    from stacklight_tests.kafka import test_smoke_bvt  # noqa
    from stacklight_tests.lma_collector import test_smoke_bvt  # noqa
    from stacklight_tests.lma_infrastructure_alerting import (  # noqa
        test_destructive)
    from stacklight_tests.lma_infrastructure_alerting import (  # noqa
        test_smoke_bvt)
    from stacklight_tests.lma_infrastructure_alerting import (  # noqa
        test_system)
    from stacklight_tests.toolchain import test_alarms  # noqa
    from stacklight_tests.toolchain import test_dedicated_environment  # noqa
    from stacklight_tests.toolchain import test_destructive  # noqa
    from stacklight_tests.toolchain import test_detached_plugins  # noqa
    from stacklight_tests.toolchain import test_functional  # noqa
    from stacklight_tests.toolchain import test_https_plugins  # noqa
    from stacklight_tests.toolchain import test_ldap_plugins  # noqa
    from stacklight_tests.toolchain import test_network_templates  # noqa
    from stacklight_tests.toolchain import test_neutron  # noqa
    from stacklight_tests.toolchain import test_post_install  # noqa
    from stacklight_tests.toolchain import test_reduced_footprint  # noqa
    from stacklight_tests.toolchain import test_smoke_bvt  # noqa
    from stacklight_tests.toolchain import test_system  # noqa
    from stacklight_tests.zabbix import test_system  # noqa


def run_tests():
    from proboscis import TestProgram  # noqa
    import_tests()

    # Run Proboscis and exit.
    TestProgram(
        addplugins=[CloseSSHConnectionsPlugin()]
    ).run_and_exit()


if __name__ == '__main__':
    import_tests()
    run_tests()

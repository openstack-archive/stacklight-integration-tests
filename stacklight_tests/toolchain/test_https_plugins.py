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
from fuelweb_test import logger
from proboscis import test

from stacklight_tests.helpers import helpers
from stacklight_tests.toolchain import api


@test(groups=["https"])
class TestToolchainHTTPs(api.ToolchainApi):
    """Class for smoke testing the LMA Toolchain plugins."""

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["https", "deploy_toolchain_with_https", "toolchain",
                  "deploy"])
    @log_snapshot_after_test
    def deploy_toolchain_with_https(self):
        """Install the LMA Toolchain plugins and check it exists

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Upload script for ssl certificate creation
            5. Create ssl certificate for influxdb_grafana plugin
            6. Create ssl certificate for elasticsearch_kibana plugin
            7. Create ssl certificate for lma_infrastructure_alerting plugin
            8. Enable and configure TLS option in plugins
            9. Deploy the cluster
            10. Check that LMA Toolchain plugins are running
            11. Run OSTF

        Duration 120m
        """
        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

        plugins_ssl = {
            "kibana": self.ELASTICSEARCH_KIBANA,
            "grafana": self.INFLUXDB_GRAFANA,
            "nagios": self.LMA_INFRASTRUCTURE_ALERTING,
        }

        with self.env.d_env.get_admin_remote() as remote:
            remote.upload(
                helpers.get_fixture("https/create_certificate.sh"),
                "/tmp")
            for name, plugin in plugins_ssl.items():
                self._activate_ssl_plugin(name, plugin, remote)

        self.helpers.deploy_cluster(self.settings.base_nodes)

        self.check_plugins_online()

        self.helpers.run_ostf()

        self.env.make_snapshot("https_plugins", is_make=True)

    @staticmethod
    def _activate_ssl_plugin(name, plugin, remote):
        """Creates certificate and activate ssl option in plugin."""
        logger.info(
            "Create certificate and configure tls in plugin {}".format(
                plugin.get_plugin_settings().name))

        ssl_cert = {}
        ssl_cert["name"] = "{}.pem".format(name)

        remote.execute(
            "cd /tmp && bash -x create_certificate.sh {}.fuel.local".
            format(name), verbose=True
        )

        with remote.open("/tmp/{}.pem".format(name)) as f:
            ssl_cert["content"] = f.read()

        plugin.activate_plugin(options={
            "tls_enabled/value": True,
            "{}_ssl_cert/value".format(name): ssl_cert
        })

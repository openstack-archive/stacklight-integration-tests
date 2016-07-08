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


@test(groups=["ldap"])
class TestToolchainLDAP(api.ToolchainApi):
    """Class testing the LMA Toolchain plugins with LDAP for authentication."""

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["ldap", "deploy_toolchain_with_ldap", "toolchain", "deploy"])
    @log_snapshot_after_test
    def deploy_toolchain_with_ldap(self):
        """Install the LMA Toolchain plugins with LDAP integration for
        authentication

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Enable and configure LDAP for plugin authentication
            5. Deploy the cluster
            6. Upload install_slapd.sh script on plugin node
            7. Install and configure the LDAP plugin
            8. Check that LMA Toolchain plugins are running
            9. Check plugins are available with LDAP for authentication

        Duration 120m
        """
        fuel_web = self.helpers.fuel_web

        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

        plugins_ldap = {
            "kibana": self.ELASTICSEARCH_KIBANA,
            "grafana": self.INFLUXDB_GRAFANA,
            "nagios": self.LMA_INFRASTRUCTURE_ALERTING,
        }

        for name, plugin in plugins_ldap.items():
            if name == "grafana":
                self._activate_ldap_plugin(plugin, "(uid=%s)")
            else:
                self._activate_ldap_plugin(plugin, "(objectClass=*)")

        self.helpers.deploy_cluster(self.settings.base_nodes)

        plugin_node = fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, roles=["influxdb_grafana", ])[0]

        with fuel_web.get_ssh_for_nailgun_node(plugin_node) as remote:
            remote.upload(
                helpers.get_fixture("ldap/install_slapd.sh"),
                "/tmp"
            )
            remote.check_call(
                "bash -x /tmp/install_slapd.sh", verbose=True
            )

        self.check_plugins_online()

        for plugin in plugins_ldap.values():
            plugin.check_plugin_ldap()

        self.env.make_snapshot("deploy_toolchain_with_ldap", is_make=True)

    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["ldap", "deploy_toolchain_with_ldap_authz", "toolchain",
                  "deploy"])
    @log_snapshot_after_test
    def deploy_toolchain_with_ldap_authz(self):
        """Install the LMA Toolchain plugins with LDAP integration for
        authentication and authorization

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Enable and configure LDAP for plugin authentication and
               authorization
            5. Deploy the cluster
            6. Upload install_slapd.sh script on plugin node
            7. Install and configure the LDAP plugin
            8. Check that LMA Toolchain plugins are running
            9. Check plugins are available with LDAP for authentication and
               authorization

        Duration 120m
        """
        fuel_web = self.helpers.fuel_web

        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

        plugins_ldap = {
            "kibana": self.ELASTICSEARCH_KIBANA,
            "grafana": self.INFLUXDB_GRAFANA,
            "nagios": self.LMA_INFRASTRUCTURE_ALERTING,
        }

        for name, plugin in plugins_ldap.items():
            if name == "grafana":
                self._activate_ldap_plugin(plugin, "(uid=%s)", authz=True)
            else:
                self._activate_ldap_plugin(plugin, "(objectClass=*)",
                                           authz=True)

        self.helpers.deploy_cluster(self.settings.base_nodes)

        plugin_node = fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, roles=["influxdb_grafana", ])[0]

        with fuel_web.get_ssh_for_nailgun_node(plugin_node) as remote:
            remote.upload(
                helpers.get_fixture("ldap/install_slapd.sh"),
                "/tmp"
            )
            remote.check_call(
                "bash -x /tmp/install_slapd.sh", verbose=True
            )

        self.check_plugins_online()

        for plugin in plugins_ldap.values():
            plugin.check_plugin_ldap(authz=True)

        self.env.make_snapshot("deploy_toolchain_ldap_authz", is_make=True)


@test(groups=["ldaps"])
class TestToolchainLDAPS(api.ToolchainApi):
    """Class testing the LMA Toolchain plugins with LDAPS for authentication.
    """
    @test(depends_on_groups=['prepare_slaves_3'],
          groups=["ldaps", "deploy_toolchain_with_ldaps_authz", "toolchain",
                  "deploy"])
    @log_snapshot_after_test
    def deploy_toolchain_with_ldaps_authz(self):
        """Install the LMA Toolchain plugins with LDAPS integration for
        authentication and authorization

        Scenario:
            1. Upload the LMA Toolchain plugins to the master node
            2. Install the plugins
            3. Create the cluster
            4. Enable and configure LDAPS for plugin authentication and
               authorization
            5. Deploy the cluster
            6. Upload install_slapd.sh script on plugin node
            7. Install and configure the LDAPS plugin
            8. Check that LMA Toolchain plugins are running
            9. Check plugins are available with LDAPS for authentication and
               authorization

        Duration 120m
        """
        fuel_web = self.helpers.fuel_web

        self.env.revert_snapshot("ready_with_3_slaves")

        self.prepare_plugins()

        self.helpers.create_cluster(name=self.__class__.__name__)

        self.activate_plugins()

        plugins_ldap = {
            "kibana": self.ELASTICSEARCH_KIBANA,
            "grafana": self.INFLUXDB_GRAFANA,
            "nagios": self.LMA_INFRASTRUCTURE_ALERTING,
        }

        for name, plugin in plugins_ldap.items():
            if name == "grafana":
                self._activate_ldap_plugin(plugin, "(uid=%s)", authz=True,
                                           protocol="ldaps")
            else:
                self._activate_ldap_plugin(plugin, "(objectClass=*)",
                                           authz=True, protocol="ldaps")

        self.helpers.deploy_cluster(self.settings.base_nodes)

        plugin_node = fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, roles=["influxdb_grafana", ])[0]

        with fuel_web.get_ssh_for_nailgun_node(plugin_node) as remote:
            remote.upload(
                helpers.get_fixture("ldap/install_slapd.sh"),
                "/tmp"
            )
            remote.check_call(
                "bash -x /tmp/install_slapd.sh", verbose=True
            )

        self.check_plugins_online()

        for plugin in plugins_ldap.values():
            plugin.check_plugin_ldap(authz=True)

        self.env.make_snapshot("deploy_toolchain_ldap_authZ", is_make=True)


def _activate_ldap_plugin(plugin, ufilter, authz=False, protocol="ldap"):
    """Activate LDAP option in plugin."""
    name = plugin.get_plugin_settings().name
    logger.info(
        "Enable LDAP in plugin {}, authorization {}, protocol: {}".format(
            name, authz, protocol))

    options = {
        "ldap_enabled/value": True,
        "ldap_protocol/value": protocol,
        "ldap_servers/value": "localhost",
        "ldap_bind_dn/value": "cn=admin,dc=stacklight,dc=ci",
        "ldap_bind_password/value": "admin",
        "ldap_user_search_base_dns/value": "dc=stacklight,dc=ci",
        "ldap_user_search_filter/value": ufilter,
        "ldap_user_search_base_dns/value": "dc=stacklight,dc=ci",
    }

    if authz:
        options.update({
            "ldap_authorization_enabled/value": True,
        })
        if name in ["elasticsearch_kibana", "lma_infrastructure_alerting"]:
            options.update({
                "ldap_admin_group_dn/value":
                    "cn=plugin_admins,ou=groups,dc=stacklight,dc=ci"
            })
            if name == "elasticsearch_kibana":
                options.update({
                    "ldap_viewer_group_dn/value":
                        "cn=plugin_viewers,ou=groups,dc=stacklight,dc=ci"
                })
        else:
            options.update({
                "ldap_group_search_base_dns/value":
                    "ou=groups,dc=stacklight,dc=ci",
                "ldap_group_search_filter/value":
                    "(&(objectClass=posixGroup)(memberUid=%s)",
                "ldap_admin_group_dn/value": "plugin_admins",
                "ldap_viewer_group_dn/value": "plugin_viewers"
            })

    plugin.activate_plugin(options=options)

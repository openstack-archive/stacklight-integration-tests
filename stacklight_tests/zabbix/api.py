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
import bs4
import requests
import urllib
import urlparse

from devops.helpers import helpers as devops_helpers
from fuelweb_test import logger
from proboscis import asserts
from pyzabbix import ZabbixAPI

from stacklight_tests.helpers import checkers
from stacklight_tests.helpers import helpers
from stacklight_tests.helpers import remote_ops

from stacklight_tests import base_test
from stacklight_tests.zabbix import plugin_settings as zabbix_plugin_settings


class ZabbixWeb(object):
    def __init__(self, zabbix_url, username, password, protocol, verify=False):
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        self.session.mount('{}://'.format(protocol), adapter)
        self.base_url = zabbix_url
        self.username = username
        self.password = password
        self.verify = verify

    def zabbix_web_login(self, autologin=1, expected_code=200):
        login_params = urllib.urlencode({'request': '',
                                         'name': self.username,
                                         'password': self.password,
                                         'autologin': autologin,
                                         'enter': 'Sign in'})
        url = urlparse.urljoin(self.base_url,
                               '?{0}'.format(login_params))
        response = self.session.post(url, verify=self.verify)

        asserts.assert_equal(
            response.status_code, expected_code,
            "Login to Zabbix failed: {0}".format(response.content))

    def get_zabbix_web_screen(self, page='screens.php',
                              expected_code=200):
        url = urlparse.urljoin(self.base_url, page)
        response = self.session.get(url, verify=self.verify)

        asserts.assert_equal(response.status_code, expected_code,
                             "Getting Zabbix screens failed: {0}".format(
                                 response.content))

        return bs4.BeautifulSoup(response.content)


class ZabbixApi(base_test.PluginApi):
    def __init__(self):
        super(ZabbixApi, self).__init__()
        self.settings = zabbix_plugin_settings
        self.helpers = helpers.PluginHelper(self.env)
        self.checkers = checkers
        self.remote_ops = remote_ops

    def get_plugin_settings(self):
        return zabbix_plugin_settings

    def prepare_plugin(self, dependat_plugins=False):
        self.helpers.prepare_plugin(self.settings.plugin_path)
        if dependat_plugins:
            for plugin in self.settings.dependant_plugins:
                self.helpers.prepare_plugin(
                    self.settings.dependant_plugins[plugin]["plugin_path"])

    def activate_plugin(self, options=None):
        if options is None:
            options = self.settings.default_options
        self.helpers.activate_plugin(
            self.settings.name, self.settings.version, options)

    def activate_dependant_plugin(self, plugin, options=None):
        if options is None:
            options = self.settings.default_options
        self.helpers.activate_plugin(
            plugin["name"], plugin["version"], options)

    def get_zabbix_url(self, protocol='http'):
        return "{0}://{1}/zabbix/".format(protocol, self.get_zabbix_vip())

    def get_zabbix_vip(self):
        return self.helpers.fuel_web.get_public_vip(self.helpers.cluster_id)

    def get_zabbix_mgmt_vip(self):
        return self.helpers.fuel_web.client.get_networks(
            self.helpers.cluster_id)['vips']['zbx_vip_mgmt']['ipaddr']

    def check_plugin_online(self):
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]
        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            remote.check_call("dpkg --get-selections | grep zabbix")
            response = remote.execute("crm resource status "
                                      "p_zabbix-server")["stdout"][0]
        asserts.assert_true("p_zabbix-server is running" in response,
                            "p_zabbix-server resource wasn't found"
                            " in pacemaker:\n{0}".format(response))

        zabbix_web = self.get_zabbix_web()
        zabbix_web.zabbix_web_login()
        screens_html = zabbix_web.get_zabbix_web_screen()
        screens_links = screens_html.find_all('a')
        asserts.assert_true(any('charts.php?graphid=' in link.get('href')
                                for link in screens_links),
                            "Zabbix screen page does not contain "
                            "graphs:\n{0}".format(screens_links))

    def uninstall_plugin(self):
        return self.helpers.uninstall_plugin(self.settings.name,
                                             self.settings.version)

    def check_uninstall_failure(self):
        return self.helpers.check_plugin_cannot_be_uninstalled(
            self.settings.name, self.settings.version)

    def get_zabbix_web(self, username='', password='', protocol='http'):
        username = username or self.settings.zabbix_username
        password = password or self.settings.zabbix_password

        return ZabbixWeb(
            self.helpers.fuel_web.get_public_vip(self.helpers.cluster_id),
            username, password, protocol)

    def get_zabbix_api(self):
        zabbix_api = ZabbixAPI(
            url=self.get_zabbix_url('https'),
            user=self.settings.zabbix_username,
            password=self.settings.zabbix_password)
        zabbix_api.session.verify = False
        return zabbix_api

    def get_node_with_zabbix_vip_fqdn(self):
        controller = self.fuel_web.get_nailgun_cluster_nodes_by_roles(
            self.helpers.cluster_id, ['controller'])[0]

        with self.fuel_web.get_ssh_for_nailgun_node(controller) as remote:
            result = remote.check_call(
                "crm status | grep {} | awk '{{print $4}}'".format(
                    self.helpers.get_vip_resource_name(
                        self.settings.zabbix_vip)))
        return result['stdout'][0].rstrip()

    def get_triggers(self, params=None):
        params = params or {
            "output": ["triggerid", "description", "priority"],
            "filter": {"value": 1}, "sortfield": "priority"
        }
        return self.get_zabbix_api().do_request('trigger.get', params)

    def wait_for_trigger(self, triggers, params=None, timeout=3 * 60):
        def check_triggers():
            for trigger in triggers:
                found = False
                for line in self.get_triggers(params)['result']:
                    if line["description"] in trigger["description"]:
                        found = True
                        if line["priority"] != trigger["priority"]:
                            logger.error(
                                "Trigger '{0}' has wrong priority! Expecteed"
                                " '{1}' but found '{2}'".format(
                                    line["description"], trigger["priority"],
                                    line["priority"]))
                            return False
                if not found:
                    logger.error("Failed to find trigger: {0}".format(
                        trigger["description"]))
                    return False
            return True
        devops_helpers.wait(
            check_triggers, timeout=timeout,
            timeout_msg="Failed to get all expected triggers!")

    def send_extreme_snmptraps(self, remote, extreme_host_ip):
        snmp_traps = {
            'ps': "snmptrap -v 1 -c {snmp_community} {zabbix_vip} "
                  "'.1.3.6.1.4.1.1916' '{extreme_host_ip}' 6 {parameter} '10'"
                  " .1.3.6.1.4.1.1916 s \"null\" .1.3.6.1.4.1.1916 s \"null\""
                  " .1.3.6.1.4.1.1916 s \"2\"",
            'port': "snmptrap -v 1 -c {snmp_community} {zabbix_vip}"
                    " '.1.3.6.1.6.3.1.1' '{extreme_host_ip}' {parameter} 10"
                    " '10' .1.3.6.1.6.3.1.1 s \"eth1\"",
            'fan': "snmptrap -v 1 -c {snmp_community} {zabbix_vip}"
                   " '.1.3.6.1.4.1.1916' '{extreme_host_ip}' 6 {parameter}"
                   " '10' .1.3.6.1.4.1.1916 s \"null\" .1.3.6.1.4.1.1916 s"
                   " \"null\" .1.3.6.1.4.1.1916 s \"5\"",
        }
        remote.check_call(snmp_traps['ps'].format(
            snmp_community='public', zabbix_vip=self.get_zabbix_mgmt_vip(),
            extreme_host_ip=extreme_host_ip, parameter=10))
        remote.check_call(snmp_traps['ps'].format(
            snmp_community='public', zabbix_vip=self.get_zabbix_mgmt_vip(),
            extreme_host_ip=extreme_host_ip, parameter=11))
        remote.check_call(snmp_traps['port'].format(
            snmp_community='public', zabbix_vip=self.get_zabbix_mgmt_vip(),
            extreme_host_ip=extreme_host_ip, parameter=2))
        remote.check_call(snmp_traps['port'].format(
            snmp_community='public', zabbix_vip=self.get_zabbix_mgmt_vip(),
            extreme_host_ip=extreme_host_ip, parameter=3))
        remote.check_call(snmp_traps['fan'].format(
            snmp_community='public', zabbix_vip=self.get_zabbix_mgmt_vip(),
            extreme_host_ip=extreme_host_ip, parameter=7))
        remote.check_call(snmp_traps['fan'].format(
            snmp_community='public', zabbix_vip=self.get_zabbix_mgmt_vip(),
            extreme_host_ip=extreme_host_ip, parameter=8))

    def send_emc_snmptraps(self, remote, emc_host_ip):
        emc_trap = (
            "snmptrap -v 1 -c {snmp_community} {zabbix_vip}"
            " '.1.3.6.1.4.1.1981' '{emc_host_ip}' 6 {parameter1} '10'"
            " .1.3.6.1.4.1.1981 s \"null\" .1.3.6.1.4.1.1981 s \"null\""
            " .1.3.6.1.4.1.1981 s \"{parameter2}\""
        )
        remote.check_call(emc_trap.format(
            snmp_community='public', zabbix_vip=self.get_zabbix_mgmt_vip(),
            emc_host_ip=emc_host_ip, parameter1=6, parameter2="a37"))
        remote.check_call(emc_trap.format(
            snmp_community='public', zabbix_vip=self.get_zabbix_mgmt_vip(),
            emc_host_ip=emc_host_ip, parameter1=5, parameter2=966))
        remote.check_call(emc_trap.format(
            snmp_community='public', zabbix_vip=self.get_zabbix_mgmt_vip(),
            emc_host_ip=emc_host_ip, parameter1=4, parameter2=7220))
        remote.check_call(emc_trap.format(
            snmp_community='public', zabbix_vip=self.get_zabbix_mgmt_vip(),
            emc_host_ip=emc_host_ip, parameter1=3, parameter2=2004))

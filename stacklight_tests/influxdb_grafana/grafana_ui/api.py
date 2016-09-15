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
from fuelweb_test import logger
from proboscis import asserts

from stacklight_tests.helpers import ui_tester
from stacklight_tests.influxdb_grafana.grafana_ui import pages


login_key_xpath = '//form[1]//button[1]'


def _get_main_page(driver, auth_data):
    login_page = pages.LoginPage(driver)
    login_page.is_login_page()
    home_page = login_page.login(*auth_data)
    home_page.is_main_page()
    return home_page


def check_grafana_dashboards(url):

    with ui_tester.ui_driver(url, "Grafana", login_key_xpath) as driver:
        user = ("grafana", "grafanapass")
        home_page = _get_main_page(driver, user)
        dashboard_names = {
            "Apache", "Cinder", "Elasticsearch", "Glance", "HAProxy", "Heat",
            "Hypervisor", "InfluxDB", "Keystone", "LMA self-monitoring",
            "Memcached", "MySQL", "Neutron", "Nova", "RabbitMQ", "System"
        }
        dashboard_names = {
            panel_name.lower() for panel_name in dashboard_names}
        available_dashboards_names = {
            dashboard.text.lower()
            for dashboard in home_page.dashboard_menu.items}
        msg = ("There is not enough panels in available panels, "
               "panels that are not presented: {}")
        # NOTE(rpromyshlennikov): should there be 'elasticsearch'
        # and 'influxdb' dashboards?
        asserts.assert_true(
            dashboard_names.issubset(available_dashboards_names),
            msg.format(dashboard_names - available_dashboards_names))
        for name in available_dashboards_names:
            dashboard_page = home_page.open_dashboard(name)
            dashboard_page.get_back_to_home()


def _check_available_menu_items_for_user(user, url, authz):
    logger.info("Checking Grafana service at {} with LDAP authorization "
                "for {} user".format(url, user[0]))
    admin_panels = ["Dashboards", "Data Sources", "Plugins"]
    viewer_panel = admin_panels[1:2] if authz else admin_panels

    with ui_tester.ui_driver(url, "Grafana", login_key_xpath) as driver:
        home_page = _get_main_page(driver, user)
        menu_items = [name.text for name in home_page.main_menu.items]
        msg = "Not all required panels are available in main menu."
        asserts.assert_true(
            (admin_panels if ("uadmin" in user)
             else viewer_panel) == menu_items,
            msg
        )


def check_grafana_ldap(grafana_url, authz=False,
                       uadmin=("uadmin", "uadmin"),
                       uviewer=("uviewer", "uviewer")):
    _check_available_menu_items_for_user(uadmin, grafana_url, authz)
    _check_available_menu_items_for_user(uviewer, grafana_url, authz)

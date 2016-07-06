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

from proboscis import asserts

from stacklight_tests.helpers.ui_tester import ui_driver
from stacklight_tests.influxdb_grafana.grafana_ui import pages


def check_grafana_dashboards(grafana_url):

    login_key_xpath = '/html/body/div/div[2]/div/div/div[2]/form/div[2]/button'

    with ui_driver(grafana_url, login_key_xpath, "Grafana") as driver:
        login_page = pages.LoginPage(driver)
        login_page.is_login_page()
        home_page = login_page.login("grafana", "grafanapass")
        home_page.is_main_page()
        dashboard_names = {
            "Apache", "Cinder", "Elasticsearch", "Glance", "HAProxy", "Heat",
            "Hypervisor", "InfluxDB", "Keystone", "LMA self-monitoring",
            "Memcached", "MySQL", "Neutron", "Nova", "RabbitMQ", "System"
        }
        dashboard_names = {
            panel_name.lower() for panel_name in dashboard_names}
        available_dashboards_names = {
            dashboard.text.lower() for dashboard in home_page.dashboards}
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


def check_grafana_ldap(grafana_url, authZ=False):

    uadmin = ("uadmin", "uadmin")
    uviewer = ("uviewer", "uviewer")

    _check_dashdoard_for_user(uadmin, grafana_url, authZ)
    _check_dashdoard_for_user(uviewer, grafana_url, authZ)


def _check_dashdoard_for_user(user, url, authZ):
    login_key_xpath = '//form[1]//button[1]'
    admin_panels = ["Dashboards", "Data Sources", "Plugins"]
    viewer_panel = list(admin_panels[1]) if authZ else admin_panels

    with ui_driver(url, login_key_xpath, "Grafana") as driver:
        login_page = pages.LoginPage(driver)
        login_page.is_login_page()
        home_page = login_page.login(*user)
        home_page.is_main_page()
        menu_items = [name.text for name in home_page.main_menu_items]
        msg = "Not all required panels are available in main menu."
        asserts.assert_true(
            (admin_panels if ("uadmin" in user)
             else viewer_panel) == menu_items,
            msg
        )

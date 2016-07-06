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

from stacklight_tests.elasticsearch_kibana.kibana_ui import pages
from stacklight_tests.helpers.ui_tester import ui_driver


def check_kibana_ldap(kibana_url, authz=False, uadmin=("uadmin", "uadmin"),
                      uviewer=("uviewer", "uviewer")):

    _check_saving_option(kibana_url, authz, *uadmin)
    _check_saving_option(kibana_url, authz, *uviewer)


def _check_saving_option(url, authz, user, password):
    url = url.split(':')
    url = ('{}://{}:{}@{}{}').format(url[0], user, password, url[1][2:],
                                     ':81' if user == 'uviewer' else '80')
    expects = {'uadmin': 'Logs', 'uviewer': 'Fatal Error'}
    with ui_driver(url, "Kibana") as driver:
        home_page = pages.MainPage(driver)
        home_page.is_main_page()
        name = home_page.save_dashboard()
        asserts.assert_equal(expects[user] if authz else 'Logs', name)

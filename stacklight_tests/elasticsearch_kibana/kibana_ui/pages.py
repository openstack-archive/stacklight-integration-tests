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
from selenium.common import exceptions
from selenium.webdriver.common import by

from stacklight_tests.helpers.ui import base_pages


class MainPage(base_pages.PageObject):
    _save_button_locator = (
        by.By.XPATH, '//button[@aria-label="Save Dashboard"]')
    _submit_button_locator = (
        by.By.XPATH, '//button[@class="btn btn-primary"][@type="submit"]')
    _error_field_locator = (by.By.CLASS_NAME, 'panel-title')

    def __init__(self, driver):
        super(MainPage, self).__init__(driver)
        self._page_title = "Logs - Dashboard - Kibana"

    def is_main_page(self):
        # TODO(rpromyshlennikov): fix unresolved attribute ._main_menu_locator
        return (self.is_the_current_page() and
                self._is_element_visible(*self._main_menu_locator))

    def save_dashboard(self):
        self._get_element(*self._save_button_locator).click()
        self._get_element(*self._submit_button_locator).click()
        try:
            self.driver.switch_to.alert.accept()
        except exceptions.NoAlertPresentException:
            pass
        return self._get_element(*self._error_field_locator).text

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

import contextlib

from proboscis import asserts
import selenium.common.exceptions as Exceptions
from selenium.webdriver.remote import webelement
import selenium.webdriver.support.ui as Support


class BaseWebObject(object):
    def __init__(self, driver, timeout=5):
        self.driver = driver
        self.timeout = timeout

    def _turn_off_implicit_wait(self):
        self.driver.implicitly_wait(0)

    def _turn_on_implicit_wait(self):
        self.driver.implicitly_wait(self.timeout)

    @contextlib.contextmanager
    def waits_disabled(self):
        try:
            self._turn_off_implicit_wait()
            yield
        finally:
            self._turn_on_implicit_wait()

    def _is_element_present(self, *locator):
        with self.waits_disabled():
            try:
                self._get_element(*locator)
                return True
            except Exceptions.NoSuchElementException:
                return False

    def _is_element_visible(self, *locator):
        try:
            return self._get_element(*locator).is_displayed()
        except (Exceptions.NoSuchElementException,
                Exceptions.ElementNotVisibleException):
            return False

    def _is_element_displayed(self, element):
        if element is None:
            return False
        try:
            if isinstance(element, webelement.WebElement):
                return element.is_displayed()
            else:
                return element.src_elem.is_displayed()
        except (Exceptions.ElementNotVisibleException,
                Exceptions.StaleElementReferenceException):
            return False

    def _is_text_visible(self, element, text, strict=True):
        if not hasattr(element, 'text'):
            return False
        if strict:
            return element.text == text
        else:
            return text in element.text

    def _get_element(self, *locator):
        return self.driver.find_element(*locator)

    def _get_elements(self, *locator):
        return self.driver.find_elements(*locator)

    def _fill_field_element(self, data, field_element):
        field_element.clear()
        field_element.send_keys(data)
        return field_element

    def _select_dropdown(self, value, element):
        select = Support.Select(element)
        select.select_by_visible_text(value)

    def _select_dropdown_by_value(self, value, element):
        select = Support.Select(element)
        select.select_by_value(value)

    def _get_dropdown_options(self, element):
        select = Support.Select(element)
        return select.options


class PageObject(BaseWebObject):
    """Base class for page objects."""

    PARTIAL_LOGIN_URL = 'login'

    def __init__(self, driver):
        """Constructor."""
        super(PageObject, self).__init__(driver)
        self._page_title = None

    @property
    def page_title(self):
        return self.driver.title

    def is_the_current_page(self, do_assert=False):
        found_expected_title = self.page_title.startswith(self._page_title)
        if do_assert:
            asserts.assert_true(
                found_expected_title,
                "Expected to find %s in page title, instead found: %s"
                % (self._page_title, self.page_title))
        return found_expected_title

    def get_current_page_url(self):
        return self.driver.current_url

    def close_window(self):
        return self.driver.close()

    def is_nth_window_opened(self, n):
        return len(self.driver.window_handles) == n

    def switch_window(self, name=None, index=None):
        """Switches focus between the webdriver windows.
        Args:
        - name: The name of the window to switch to.
        - index: The index of the window handle to switch to.
        If the method is called without arguments it switches to the
         last window in the driver window_handles list.
        In case only one window exists nothing effectively happens.
        Usage:
        page.switch_window(name='_new')
        page.switch_window(index=2)
        page.switch_window()
        """

        if name is not None and index is not None:
            raise ValueError("switch_window receives the window's name or "
                             "the window's index, not both.")
        if name is not None:
            self.driver.switch_to.window(name)
        elif index is not None:
            self.driver.switch_to.window(
                self.driver.window_handles[index])
        else:
            self.driver.switch_to.window(self.driver.window_handles[-1])

    def go_to_previous_page(self):
        self.driver.back()

    def go_to_next_page(self):
        self.driver.forward()

    def refresh_page(self):
        self.driver.refresh()


class DropDownMenu(BaseWebObject):

    _default_src_locator = None

    _options_list_locator = None

    _items_locator = None

    def __init__(self, driver):
        super(DropDownMenu, self).__init__(driver)
        self.src_elem = self._get_element(*self._default_src_locator)

    def is_opened(self):
        return self._is_element_present(*self._options_list_locator)

    def open(self):
        if not self.is_opened():
            self.src_elem.click()

    @property
    def options(self):
        self.open()
        return self._get_element(*self._options_list_locator)

    @property
    def items(self):
        return self.options.find_elements(*self._items_locator)

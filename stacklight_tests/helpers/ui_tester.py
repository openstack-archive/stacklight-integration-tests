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

import contextlib
import socket

from selenium import webdriver
from selenium.webdriver.common import by
from selenium.webdriver.common import proxy
import xvfbwrapper

from stacklight_tests.helpers.ui import ui_settings


@contextlib.contextmanager
def ui_driver(url, title, wait_element='/html'):
    vdisplay = None
    # Start a virtual display server for running the tests headless.
    if ui_settings.headless_mode:
        vdisplay = xvfbwrapper.Xvfb(width=1920, height=1080)
        args = []

        # workaround for memory leak in Xvfb taken from:
        # http://blog.jeffterrace.com/2012/07/xvfb-memory-leak-workaround.html
        args.append("-noreset")

        # disables X access control
        args.append("-ac")

        if hasattr(vdisplay, 'extra_xvfb_args'):
            # xvfbwrapper 0.2.8 or newer
            vdisplay.extra_xvfb_args.extend(args)
        else:
            vdisplay.xvfb_cmd.extend(args)
        vdisplay.start()
    driver = get_driver(url, wait_element, title)
    try:
        yield driver
    finally:
        driver.quit()
        if vdisplay is not None:
            vdisplay.stop()


def get_driver(url, anchor, title, by_selector_type=by.By.XPATH):
    proxy_address = ui_settings.proxy_address
    # Increase the default Python socket timeout from nothing
    # to something that will cope with slow webdriver startup times.
    # This *just* affects the communication between this test process
    # and the webdriver.
    socket.setdefaulttimeout(60)
    # Start the Selenium webdriver and setup configuration.
    proxy_ex = None
    if proxy_address is not None:
        proxy_ex = proxy.Proxy(
            {
                'proxyType': proxy.ProxyType.MANUAL,
                'socksProxy': proxy_address,
            }
        )
    driver = webdriver.Firefox(proxy=proxy_ex)
    if ui_settings.maximize_window:
        driver.maximize_window()
    driver.implicitly_wait(ui_settings.implicit_wait)
    driver.set_page_load_timeout(ui_settings.page_timeout)
    driver.get(url)
    driver.find_element(by_selector_type, anchor)
    assert title in driver.title
    return driver


def get_table(driver, xpath, frame=None):
    if frame:
        driver.switch_to.default_content()
        driver.switch_to.frame(driver.find_element_by_name(frame))
    return driver.find_element_by_xpath(xpath)


def get_table_row(table, row_id):
    return table.find_element_by_xpath("tr[{0}]".format(row_id))


def get_table_size(table):
    return len(table.find_elements_by_xpath("tr[position() > 0]"))


def get_table_cell(table, row_id, column_id):
    row = get_table_row(table, row_id)
    return row.find_element_by_xpath("td[{0}]".format(column_id))

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

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def get_driver(ip, anchor, title):
    driver = webdriver.Firefox()
    driver.get(ip)
    WebDriverWait(driver, 120).until(
        EC.presence_of_element_located((By.XPATH, anchor)))
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


def node_is_present(driver, name):
    table = get_table(driver, "/html/body/div[2]/table/tbody")
    for ind in xrange(2, get_table_size(table) + 1):
        node_name = get_table_cell(table, ind, 1).text.rstrip()
        if name == node_name:
            return True

    return False

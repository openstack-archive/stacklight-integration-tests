#    Copyright 2015 Mirantis, Inc.
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys

from fuelweb_test import logger
from fuelweb_test import logwrap

delay = 120

@logwrap
def get_driver(nagios_ip, anchor, title):
    driver = webdriver.Firefox()
    driver.get(nagios_ip)
    WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.XPATH, anchor)))
    assert title in driver.title
    return driver

@logwrap
def get_page(driver, link_text, anchor):
    driver.switch_to.default_content()
    driver.switch_to.frame(driver.find_element_by_name("side"))
    link = driver.find_element_by_link_text(link_text)
    link.click()
    driver.switch_to.default_content()
    driver.switch_to.frame(driver.find_element_by_name("main"))
    WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.XPATH, anchor)))
    return driver

@logwrap
def get_hosts_page(driver):
    return get_page(driver, 'Hosts', "//table[@class='headertable']")

@logwrap
def get_services_page(driver):
    return get_page(driver, 'Services', "//table[@class='headertable']")

@logwrap
def get_problems_page(driver):
    return get_page(driver, 'Problems', "//div[@class='statusTitle']")

@logwrap
def get_table(driver, xpath, frame=None):
    if frame:
        driver.switch_to.default_content()
        driver.switch_to.frame(driver.find_element_by_name(frame))
    return driver.find_element_by_xpath(xpath)

@logwrap
def get_table_row(table, row_id):
    return table.find_element_by_xpath("tr[{0}]".format(row_id))

@logwrap
def get_table_size(table):
    return len(table.find_elements_by_xpath("tr[position() > 0]"))

@logwrap
def get_services_for_node(table, node_name):
    services = {}
    node_start, node_end = '', ''
    for ind in xrange(2, get_table_size(table)+1):
        if not get_table_row(table, ind).text:
            if node_start:
                node_end = ind
                break
            else:
                continue
        if get_table_cell(table, ind, 1).text == node_name:
            node_start = ind

    for ind in xrange(node_start, node_end):
        services[get_table_cell(table, ind, 2).text] = get_table_cell(table, ind, 3).text
    return services


@logwrap
def get_table_cell(table, row_id, column_id):
    row = get_table_row(table, row_id)
    return row.find_element_by_xpath("td[{0}]".format(column_id))

@logwrap
def node_is_present(driver, name):
    present = False
    table = get_table(driver, "/html/body/div[2]/table/tbody")
    for ind in xrange(2, get_table_size(table)+1):
        node_name = get_table_cell(table, ind, 1).text
        logger.debug("#####     '{0}'  '{1}'     #####".format(name, node_name))
        if name in node_name:
            present = True
            break

    return present

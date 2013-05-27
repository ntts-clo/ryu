# Copyright (C) 2013 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import re
from math import sqrt
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException


class DriverUtil(object):
    def __init__(self):
        self.fail = AssertionError

    @staticmethod
    def wait_for_true(timeout, fnc, *args, **kwargs):
        res = None
        for i in range(timeout):
            res = fnc(*args, **kwargs)
            if res:
                break
            time.sleep(1)
        assert res, 'Timeout(%d) %s %s %s' % (timeout, fnc, args, kwargs)

        return res

    def is_displayed(self, el):
        if el and el.is_displayed():
            return True
        return False

    def wait_for_displayed(self, el, timeout=30):
        return DriverUtil.wait_for_true(timeout, self.is_displayed, el)

    def is_hidden(self, el):
        return not self.is_displayed(el)

    def wait_for_hidden(self, el, timeout=30):
        return DriverUtil.wait_for_true(timeout, self.is_hidden, el)

    def has_text(self, el, text):
        if el and re.search(r'%s' % text, el.text):
            return True
        return False

    def wait_for_text(self, el, text, timeout=30):
        return DriverUtil.wait_for_true(timeout, self.has_text, el, text)

    def has_not_text(self, el, text):
        return not self.has_text(el, text)

    def wait_for_text_deleted(self, el, text, timeout=30):
        return DriverUtil.wait_for_true(timeout, self.has_not_text, el, text)

    def get_element_center(self, el):
        x = (int(el.location['x']) + el.size['width']) / 2
        y = (int(el.location['y']) + el.size['height']) / 2
        return {'x': x, 'y': y}

    def get_distance(self, el1, el2):
        c1 = self.get_element_center(el1)
        c2 = self.get_element_center(el2)
        dx = c1['x'] - c2['x']
        dy = c1['y'] - c2['y']
        return sqrt(pow(dx, 2) + pow(dy, 2))


class ElementBase(object):
    def __init__(self, driver):
        self._driver = driver
        self.fail = AssertionError
        self.name = self.__class__.__name__

    def _get_el(self, by, value):
        try:
            element = self._driver.find_element(by=by, value=value)
        except NoSuchElementException, e:
            return False
        return element

    def _get_els(self, by, value):
        try:
            elements = self._driver.find_elements(by=by, value=value)
        except NoSuchElementException, e:
            return False
        return elements


class Menu(ElementBase):
    @property
    def body(self):
        return self._get_el(By.ID, "menu")

    @property
    def titlebar(self):
        return self._get_el(By.CSS_SELECTOR,
                            "#menu > div.content-title")

    @property
    def dialog(self):
        return self._get_el(By.ID, "jquery-ui-dialog-opener")

    @property
    def redesign(self):
        return self._get_el(By.ID, "menu-redesign")

    @property
    def link_list(self):
        return self._get_el(By.ID, "menu-link-status")

    @property
    def flow_list(self):
        return self._get_el(By.ID, "menu-flow-entries")

    @property
    def resize(self):
        return self._get_el(By.XPATH, "//div[@id='menu']/div[6]")


class Dialog(ElementBase):
    @property
    def body(self):
        return self._get_el(By.ID, "jquery-ui-dialog")

    @property
    def host(self):
        return self._get_el(By.ID, "jquery-ui-dialog-form-host")

    @property
    def port(self):
        return self._get_el(By.ID, "jquery-ui-dialog-form-port")

    @property
    def cancel(self):
        return self._get_el(By.XPATH, "(//button[@type='button'])[2]")

    @property
    def launch(self):
        return self._get_el(By.XPATH, "//button[@type='button']")

    @property
    def close(self):
        return self._get_el(By.CSS_SELECTOR, "span.ui-icon.ui-icon-closethick")

    @property
    def resize(self):
        return self._get_el(By.XPATH, "//div[7]")


class Topology(ElementBase):
    def __init__(self, driver):
        super(Topology, self).__init__(driver)
        self._not_selected_switch_width = None

    @property
    def body(self):
        return self._get_el(By.ID, "topology")

    @property
    def titlebar(self):
        return self._get_el(By.CSS_SELECTOR, "#topology > div.content-title")

    @property
    def resize(self):
        return self._get_el(By.XPATH, "//div[@id='topology']/div[5]")

    @property
    def switches(self):
        return self._get_els(By.CSS_SELECTOR,
                             "#topology > div.content-body > div.switch")

    def get_switch(self, dpid):
        id_ = "node-switch-%d" % int(dpid)
        el = self._get_el(By.ID, id_)
        if not el:
            self.fail('element not found. dpid=%d' % int(dpid))
            return
        elif self._not_selected_switch_width is None:
            # set element default width for is_selected()
            self._not_selected_switch_width = el.size["width"]
        return el

    def is_selected(self, el):
        # chromedriver could not use "get_value_of_css('border-color')".
        # check to wider than default switch element.
        return el.size['width'] > self._not_selected_switch_width

    def get_dpid(self, el):
        return int(el.get_attribute("id")[len('node-switch-'):])

    def get_text_dpid(self, dpid):
        return 'dpid: 0x%x' % (dpid)


class LinkList(ElementBase):
    @property
    def body(self):
        return self._get_el(By.ID, "link-list")

    @property
    def close(self):
        return self._get_el(By.XPATH, "//div[@id='link-list']/div/div[2]")

    @property
    def titlebar(self):
        return self._get_el(By.CSS_SELECTOR, "#link-list > div.content-title")

    @property
    def resize(self):
        return self._get_el(By.XPATH, "//div[@id='link-list']/div[6]")

    @property
    def scrollbar_x(self):
        return self._get_el(By.CSS_SELECTOR,
                            "#link-list-body > div.ps-scrollbar-x")

    @property
    def scrollbar_y(self):
        return self._get_el(By.CSS_SELECTOR,
                            "#link-list-body > div.ps-scrollbar-y")

    @property
    def rows(self):
        links = []
        css = '#%s > td.%s'
        # loop rows
        for row in self._get_els(By.CSS_SELECTOR,
                                 "#link-list > div.content-body > " +
                                 "table > tbody > tr.content-table-item"):
            id_ = row.get_attribute('id')

            # set inner elements
            no = self._get_el(By.CSS_SELECTOR, css % (id_, 'port-no'))
            name = self._get_el(By.CSS_SELECTOR, css % (id_, 'port-name'))
            peer = self._get_el(By.CSS_SELECTOR, css % (id_, 'port-peer'))
            setattr(row, 'no', no)
            setattr(row, 'name', name)
            setattr(row, 'peer', peer)
            links.append(row)
        return links


class FlowList(ElementBase):
    @property
    def body(self):
        return self._get_el(By.ID, "flow-list")

    @property
    def close(self):
        return self._get_el(By.XPATH, "//div[@id='flow-list']/div/div[2]")

    @property
    def titlebar(self):
        return self._get_el(By.CSS_SELECTOR, "#flow-list > div.content-title")

    @property
    def resize(self):
        return self._get_el(By.XPATH, "//div[@id='flow-list']/div[6]")

    @property
    def scrollbar_x(self):
        return self._get_el(By.CSS_SELECTOR,
                            "#flow-list-body > div.ps-scrollbar-x")

    @property
    def scrollbar_y(self):
        return self._get_el(By.CSS_SELECTOR,
                            "#flow-list-body > div.ps-scrollbar-y")

    @property
    def rows(self):
        return self._get_els(By.CSS_SELECTOR,
                             "#flow-list > div.content-body > " +
                             "table > tbody > tr.content-table-item")

    def _get_row_text(self, row_no):
        css = '#%s > td > div > span.flow-item-value'
        texts = {'stats': None, 'rules': None, 'actions': None}
        try:
            # get inner elements
            id_ = self.rows[row_no].get_attribute('id')
            inner = self._get_els(By.CSS_SELECTOR, css % (id_))
            if not len(inner) == 3:
                raise StaleElementReferenceException
            texts['stats'] = inner[0].text
            texts['rules'] = inner[1].text
            texts['actions'] = inner[2].text
        except StaleElementReferenceException:
            # flow-list refreashed.
            return False
        return texts

    def get_row_text(self, row_no):
        return DriverUtil.wait_for_true(2, self._get_row_text, row_no)

    def wait_for_refreshed(self, timeout=10):
        old = None
        rows = self.rows
        if rows:
            old = rows[0].id

        now = None
        for i in range(timeout):
            rows = self.rows
            if rows:
                now = rows[0].id
            if (old and not now) or (now and old != now):
                return True
            time.sleep(1)
        if (old is None and now is None):
            # no data
            return False
        self.fail('flow-list does not refreshed.')

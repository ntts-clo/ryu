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

import re
import time
import unittest
import xmlrpclib
from nose.tools import ok_, eq_
from nose.plugins.skip import SkipTest
from selenium.webdriver.common.action_chains import ActionChains

import gui_elements


# GUI app address
GUI_HOST = '127.0.0.1'
GUI_PORT = '8000'
BASE_URL = 'http://%s:%s' % (GUI_HOST, GUI_PORT)

# REST app address
REST_HOST = 'localhost'
REST_PORT = '8080'

# ryu controller address
RYU_HOST = '127.0.0.1'
RYU_PORT = '6633'

# mininet controller address
MN_HOST = '127.0.0.1'
MN_PORT = '18000'
MN_CTL_URL = 'http://%s:%s' % (MN_HOST, MN_PORT)


def _rest_request(path, method="GET", body=None):
    address = '%s:%s' % (REST_HOST, REST_PORT)
    conn = httplib.HTTPConnection(address)
    conn.request(method, path, body)
    res = conn.getresponse()
    if res.status in (httplib.OK,
                      httplib.CREATED,
                      httplib.ACCEPTED,
                      httplib.NO_CONTENT):
        return res
    raise httplib.HTTPException(
        res, 'code %d reason %s' % (res.status, res.reason),
        res.getheaders(), res.read())


class TestGUI(unittest.TestCase):
    # called before the TestCase run.
    @classmethod
    def setUpClass(cls):
        cls._mn = None
        cls._set_driver()
        ok_(cls.driver, 'driver dose not setting.')

        # elements
        cls.util = gui_elements.DriverUtil()
        cls.menu = gui_elements.Menu(cls.driver)
        cls.dialog = gui_elements.Dialog(cls.driver)
        cls.topology = gui_elements.Topology(cls.driver)
        cls.link_list = gui_elements.LinkList(cls.driver)
        cls.flow_list = gui_elements.FlowList(cls.driver)

    # called after the TestCase run.
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    # called before an individual test_* run.
    def setUp(self):
        self.driver.get(BASE_URL + "/")
        self.util.wait_for_displayed(self.dialog.body)

    # called after an individual test_* run.
    def tearDown(self):
        if self._mn is not None:
            self._mn.stop()

    # called in to setUpClass().
    @classmethod
    def _set_driver(cls):
        # set the driver of the test browser.
        # self.driver = selenium.webdriver.Firefox()
        cls.driver = None

    def _get_mininet_controller(self):
        self._mn = xmlrpclib.ServerProxy(MN_CTL_URL, allow_none=True)
        self._mn.add_controller(RYU_HOST, int(RYU_PORT))
        return self._mn

    def mouse(self):
        return ActionChains(self.driver)

    def _rest_connect(self):
        if not self.dialog.body.is_displayed():
            # dialog open
            self.menu.dialog.click()
            self.util.wait_for_displayed(self.dialog.body)

        # input address
        self.dialog.host.clear()
        self.dialog.host.send_keys(REST_HOST)
        self.dialog.port.clear()
        self.dialog.port.send_keys(REST_PORT)

        # click "launch"
        self.dialog.launch.click()
        self.util.wait_for_text(self.topology.body, "Connected")

    def test_default(self):
        ## input-dialog
        # is_displayed, host=GUI_HOST, port=8080
        dialog = self.dialog
        ok_(dialog.body.is_displayed())
        eq_(GUI_HOST, dialog.host.get_attribute("value"))
        eq_('8080', dialog.port.get_attribute("value"))

        # click "cancel"
        dialog.cancel.click()

        ## topology
        # "Disconnected", no switches
        topology = self.topology
        ok_(re.search(r"Disconnected", topology.body.text))
        ok_(not topology.switches)

        ## link-list
        # is_displayed, no data
        link = self.link_list
        ok_(link.body.is_displayed())
        ok_(not link.rows)

        ## flow-list
        # is_displayed, no data
        flow = self.flow_list
        ok_(flow.body.is_displayed())
        ok_(not flow.rows)

    def _test_contents_close_open(self, target, opener):
        self.util.wait_for_displayed(target.body)

        # close
        target.close.click()
        ok_(not target.body.is_displayed(),
            '%s does not close content.' % target.name)

        # open
        opener.click()
        ok_(self.util.wait_for_displayed(target.body),
            '%s does not open content.' % target.name)

    def test_contents_close_open(self):
        menu = self.menu
        ## input-dialog
        self._test_contents_close_open(self.dialog, menu.dialog)
        self.dialog.close.click()

        ## link-list
        self._test_contents_close_open(self.link_list, menu.link_list)

        ## flow-list
        self._test_contents_close_open(self.flow_list, menu.flow_list)

    def _test_contents_draggable(self, target):
        move = 50
        xoffset = target.location['x'] + move
        yoffset = target.location['y'] + move

        # move
        mouse = self.mouse()
        mouse.click(target)
        mouse.drag_and_drop_by_offset(target, move, move)
        mouse.perform()

        err = '%s draggable error' % (target.name)
        eq_(target.location['x'], xoffset, err)
        eq_(target.location['y'], yoffset, err)

        # move back
        # content can not drag if overlaps with other contents.
        mouse = self.mouse()
        mouse.click(target)
        mouse.drag_and_drop_by_offset(target, -move, -move)
        mouse.perform()

    def test_contents_draggable(self):
        self.dialog.close.click()

        ## menu
        self._test_contents_draggable(self.menu.titlebar)

        ## topology
        self._test_contents_draggable(self.topology.titlebar)

        ## link-list
        self._test_contents_draggable(self.link_list.titlebar)

        ## flow-list
        self._test_contents_draggable(self.flow_list.titlebar)

    def _test_contents_resize(self, target):
        self.util.wait_for_displayed(target.body)

        size = target.body.size

        # resize
        resize = 20
        mouse = self.mouse()
        mouse.move_to_element(target.body)
        mouse.drag_and_drop_by_offset(target.resize, resize, resize)
        mouse.perform()

        # check
        err = '%s resize error' % (target.name)
        eq_(target.body.size['width'], size['width'] + resize, err)
        eq_(target.body.size['height'], size['height'] + resize, err)

        # resize back
        mouse = self.mouse()
        mouse.move_to_element(target.body)
        mouse.drag_and_drop_by_offset(target.resize, -resize, -resize)
        mouse.perform()

    def test_contents_resize(self):
        ## input-dialog
        self._test_contents_resize(self.dialog)
        self.dialog.cancel.click()

        ## menu
        self._test_contents_resize(self.menu)

        ## topology
        self._test_contents_resize(self.topology)

        ## link-list
        self._test_contents_resize(self.link_list)

        ## flow-list
        self._test_contents_resize(self.flow_list)

    def test_connected(self):
        # input host
        host = self.dialog.host
        host.clear()
        host.send_keys(REST_HOST)

        # input port
        port = self.dialog.port
        port.clear()
        port.send_keys(REST_PORT)

        # click "Launch"
        self.dialog.launch.click()
        ok_(self.util.wait_for_text(self.topology.body, "Connected"))

    def test_topology_discavery(self):
        util = self.util
        topo = self.topology
        mn = self._get_mininet_controller()

        self._rest_connect()

        ## add switch (dpid=1)
        mn.add_switch('s1')
        ok_(util.wait_for_text(topo.body, topo.get_text_dpid(1)))

        ## add some switches (dpid=2-8)
        mn.add_switch('s2')
        mn.add_switch('s3')
        mn.add_switch('s4')

        # check drawed
        ok_(util.wait_for_text(topo.body, topo.get_text_dpid(2)))
        ok_(util.wait_for_text(topo.body, topo.get_text_dpid(3)))
        ok_(util.wait_for_text(topo.body, topo.get_text_dpid(4)))
        time.sleep(1)  # wait for switch move animation

        # check positions (diamond shape)
        d_1_2 = util.get_distance(topo.get_switch(1), topo.get_switch(2))
        d_2_3 = util.get_distance(topo.get_switch(2), topo.get_switch(3))
        d_3_4 = util.get_distance(topo.get_switch(3), topo.get_switch(4))
        d_4_1 = util.get_distance(topo.get_switch(4), topo.get_switch(1))
        ok_(d_1_2 == d_2_3 == d_3_4 == d_4_1)

        ## selected
        for sw in topo.switches:
            sw.click()
            ok_(topo.is_selected(sw))

        ## draggable
        default_locations = {}
        move = 10
        for sw in topo.switches:
            dpid = topo.get_dpid(sw)
            default_locations[dpid] = sw.location
            xoffset = sw.location['x'] + move
            yoffset = sw.location['y'] + move

            # move
            mouse = self.mouse()
            mouse.drag_and_drop_by_offset(sw, move, move)
            mouse.perform()

            err = 'dpid=%d draggable error' % (dpid)
            eq_(sw.location['x'], xoffset, err)
            eq_(sw.location['y'], yoffset, err)

        ## refresh
        self.menu.redesign.click()
        time.sleep(1)  # wait for switch move animation
        for sw in topo.switches:
            dpid = topo.get_dpid(sw)
            default_location = default_locations[dpid]
            eq_(sw.location, default_location)

        ## del switch (dpid=4)
        mn.del_switch('s4')
        ok_(util.wait_for_text_deleted(topo.body, topo.get_text_dpid(4)))

        time.sleep(1)  # wait for switch move animation

        # check position (isosceles triangle)
        d_1_2 = util.get_distance(topo.get_switch(1), topo.get_switch(2))
        d_1_3 = util.get_distance(topo.get_switch(1), topo.get_switch(3))
        eq_(d_1_2, d_1_3)

        ## del all switches
        mn.stop()
        ok_(util.wait_for_text_deleted(topo.body, topo.get_text_dpid(1)))
        ok_(util.wait_for_text_deleted(topo.body, topo.get_text_dpid(2)))
        ok_(util.wait_for_text_deleted(topo.body, topo.get_text_dpid(3)))


if __name__ == "__main__":
    unittest.main()

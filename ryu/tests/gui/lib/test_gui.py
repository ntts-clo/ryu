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
import json
import httplib
from nose.tools import ok_, eq_
from selenium.webdriver.common.action_chains import ActionChains

import elements
from ryu.ofproto.ether import ETH_TYPE_IP
from ryu.ofproto.inet import IPPROTO_TCP
from ryu.ofproto import ofproto_v1_0


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


OFP_DEFAULT_PRIORITY = ofproto_v1_0.OFP_DEFAULT_PRIORITY


# flow-list sort key
def _flows_sort_key(a, b):
    # ascending table_id
    if a.get('table_id', 0) > b.get('table_id', 0):
        return 1
    elif a.get('table_id', 0) < b.get('table_id', 0):
        return -1
    # descending priority
    elif a.get('priority', OFP_DEFAULT_PRIORITY) < \
        b.get('priority', OFP_DEFAULT_PRIORITY):
        return 1
    elif a.get('priority', OFP_DEFAULT_PRIORITY) > \
        b.get('priority', OFP_DEFAULT_PRIORITY):
        return -1
    # ascending duration
    elif a.get('duration_sec', 0) < b.get('duration_sec', 0):
        return 1
    elif a.get('duration_sec', 0) > b.get('duration_sec', 0):
        return -1
    elif a.get('duration_nsec', 0) < b.get('duration_nsec', 0):
        return 1
    elif a.get('duration_nsec', 0) > b.get('duration_nsec', 0):
        return -1
    else:
        return 0


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


def _is_rest_link_deleted():
    try:
        links = json.load(_rest_request('/v1.0/topology/links'))
    except (IOError):
        # REST API is not avaliable.
        return True
    return not links


class TestGUI(unittest.TestCase):
    WINDOW_SIZE_WIDTH = 900
    WINDOW_SIZE_HEIGHT = 900

    # called before the TestCase run.
    @classmethod
    def setUpClass(cls):
        cls._mn = None
        cls._set_driver()
        ok_(cls.driver, 'driver dose not setting.')
        cls.driver.set_window_size(cls.WINDOW_SIZE_WIDTH,
                                   cls.WINDOW_SIZE_HEIGHT)

        # elements
        cls.util = elements.DriverUtil()
        cls.menu = elements.Menu(cls.driver)
        cls.dialog = elements.Dialog(cls.driver)
        cls.topology = elements.Topology(cls.driver)
        cls.link_list = elements.LinkList(cls.driver)
        cls.flow_list = elements.FlowList(cls.driver)

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
            self.util.wait_for_true(20, _is_rest_link_deleted)

    # called in to setUpClass().
    @classmethod
    def _set_driver(cls):
        # set the driver of the test browser.
        # self.driver = selenium.webdriver.Firefox()
        cls.driver = None

    def _get_mininet_controller(self):
        if self._mn is None:
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
        titlebar = target.titlebar
        xoffset = titlebar.location['x'] + move
        yoffset = titlebar.location['y'] + move

        # move
        mouse = self.mouse()
        mouse.click(titlebar)
        mouse.drag_and_drop_by_offset(titlebar, move, move)
        mouse.perform()

        err = '%s draggable error' % (target.name)
        eq_(titlebar.location['x'], xoffset, err)
        eq_(titlebar.location['y'], yoffset, err)

        # move back
        # content can not drag if overlaps with other contents.
        mouse = self.mouse()
        mouse.click(titlebar)
        mouse.drag_and_drop_by_offset(titlebar, -move, -move)
        mouse.perform()

    def test_contents_draggable(self):
        self.dialog.close.click()

        ## menu
        self._test_contents_draggable(self.menu)

        ## topology
        self._test_contents_draggable(self.topology)

        ## link-list
        self._test_contents_draggable(self.link_list)

        ## flow-list
        self._test_contents_draggable(self.flow_list)

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

    def test_topology_discovery(self):
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

    def _test_link_discovery(self, links):
        link_list = self.link_list
        util = self.util

        # check Row count
        if links:
            eq_(len(links), len(link_list.rows))
        else:
            ok_(not link_list.rows)

        # check text
        for link in link_list.rows:
            ok_(link.name.text in links)
            eq_(str(links[link.name.text]['port_no']), link.no.text)
            eq_(links[link.name.text]['peer'], link.peer.text)

        # TODO: check connections on Topology

    def test_link_discovery(self):
        util = self.util
        link_list = self.link_list
        links = {}
        mn = self._get_mininet_controller()

        self._rest_connect()

        # add some switches (dpid=1-4)
        mn.add_switch('s1')
        mn.add_switch('s2')
        mn.add_switch('s3')
        mn.add_switch('s4')
        # s1 selected
        util.wait_for_text(self.topology.body,
                           self.topology.get_text_dpid(1))
        self.topology.get_switch(dpid=1).click()

        ## add links (s1 to s2, s3 and s4)
        mn.add_link('s1', 's2')
        mn.add_link('s1', 's3')
        mn.add_link('s1', 's4')

        links = {}
        links['s1-eth1'] = {'port_no': 1, 'peer': 's2-eth1'}
        links['s1-eth2'] = {'port_no': 2, 'peer': 's3-eth1'}
        links['s1-eth3'] = {'port_no': 3, 'peer': 's4-eth1'}
        for link in links.values():
            util.wait_for_text(link_list.body, link['peer'])

        # check
        self._test_link_discovery(links)

        ## del link (s1 to s4)
        mn.del_link('s1', 's4')
        del links['s1-eth3']
        util.wait_for_text_deleted(link_list.body, 's4-eth1')

        # check
        self._test_link_discovery(links)

    def _test_flow_discovery(self, flows):
        flow_list = self.flow_list
        body = flow_list.body
        scrollbar = flow_list.scrollbar_y
        flows.sort(cmp=_flows_sort_key)

        # wait list refreshed
        flow_list.wait_for_refreshed()

        # check Row count
        if flows:
            eq_(len(flow_list.rows), len(flows))
        else:
            ok_(not flow_list.rows)

        for i, flow in enumerate(flows):
            row = flow_list.get_row_text(i)

            # Row is be out of content area?
            if not row['actions']:
                # hold scrollbar
                mouse = self.mouse()
                mouse.click_and_hold(scrollbar).perform()

                do_scroll = self.mouse().move_by_offset(0, 3)
                end = body.location['y'] + body.size['height']
                end -= scrollbar.size['height']
                while scrollbar.location['y'] < end:
                    # do scroll
                    do_scroll.perform()
                    row = flow_list.get_row_text(i)
                    if row['actions']:
                        # loock up
                        break
                # scroll to top of content
                mouse = self.mouse()
                mouse.move_by_offset(0, -body.size['height'])
                mouse.release(scrollbar).perform()

            # check text
            stats = row['stats']
            rules = row['rules']
            actions = row['actions']

            # TODO: other attributes
            priority = flow['priority']
            tp_src = flow['match']['tp_src']
            output = flow['actions'][0]['port']

            ok_(re.search(r'priority=%d' % (priority), stats),
                'i=%d, priority=%d, display=%s' % (i, priority, stats))
            ok_(re.search(r'tp_src=%d' % (tp_src), rules),
                'i=%d, tp_src=%d, display=%s' % (i, tp_src, rules))
            ok_(re.search(r'OUTPUT:%d' % (output), actions),
                'i=%d, OUTPUT=%d, display=%s' % (i, output, actions))

    def test_flow_discovery(self):
        mn = self._get_mininet_controller()
        path = '/stats/flowentry/%s'
        flows = []

        self._rest_connect()

        # add switche (dpid=1) and select
        mn.add_switch('s1')
        self.util.wait_for_text(self.topology.body,
                                self.topology.get_text_dpid(1))
        self.topology.get_switch(dpid=1).click()

        ## add flow
        # stats  : priority=100
        # rules  : tp_src=99
        # actions: OUTPUT: 1
        body = {}
        body['dpid'] = 1
        body['priority'] = 100
        body['match'] = {'dl_type': ETH_TYPE_IP,
                         'nw_proto': IPPROTO_TCP,
                         'tp_src': 99}
        body['actions'] = [{'type': "OUTPUT", "port": 1}]
        _rest_request(path % ('add'), 'POST', json.dumps(body))

        flows.append(body)
        self._test_flow_discovery(flows)

        ## add more flow
        # stats  : priority=100-104
        # rules  : tp_src=101-105 (=priority + 1)
        # actions: OUTPUT: 2
        for priority in [100, 101, 102, 103, 104]:
            tp_src = priority + 1
            body = {}
            body['dpid'] = 1
            body['priority'] = priority
            body['match'] = {'dl_type': ETH_TYPE_IP,
                             'nw_proto': IPPROTO_TCP,
                             'tp_src': tp_src}
            body['actions'] = [{'type': "OUTPUT", "port": 2}]
            _rest_request(path % ('add'), 'POST', json.dumps(body))
            flows.append(body)
        self._test_flow_discovery(flows)

        ## mod flow
        # rules  : tp_src=103, 104 (=priority + 1)
        # actions: OUTPUT: 2 -> 3
        for flow in flows:
            if flow['match']['tp_src'] in [103, 104]:
                flow['actions'][0]['port'] = 3
                _rest_request(path % ('modify'), 'POST', json.dumps(flow))
        self._test_flow_discovery(flows)

        ## del some flow
        # rules  : tp_src=103, 104 (=priority + 1)
        for i, flow in enumerate(flows):
            if flow['match']['tp_src'] in [103, 104]:
                body = flows.pop(i)
                _rest_request(path % ('delete'), 'POST', json.dumps(body))
        self._test_flow_discovery(flows)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/python
#
# Copyright (C) Citrix Systems Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; version 2.1 only.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# A plugin for enabling trim on LVM based SRs to free up storage space
# in Storage arrays.

import xml
import sys
import os
import time
import util
from lock import Lock
import lvhdutil
import vhdutil
import lvutil
import xs_errors
import xmlrpclib

TRIM_LV_TAG = "_trim_lv"
TRIM_CAP = "SR_TRIM"
LOCK_RETRY_ATTEMPTS = 3
LOCK_RETRY_INTERVAL = 1

def _vg_by_sr_uuid(sr_uuid):
    return lvhdutil.VG_PREFIX + sr_uuid

def _lvpath_by_vg_lv_name(vg_name, lv_name):
    return os.path.join(lvhdutil.VG_LOCATION, vg_name, lv_name)

def to_xml(d):

    dom = xml.dom.minidom.Document()
    trim_response = dom.createElement("trim_response")
    dom.appendChild(trim_response)

    for key, value in d.iteritems():
        key_value_element = dom.createElement("key_value_pair")
        trim_response.appendChild(key_value_element)

        key_element = dom.createElement("key")
        key_text_node = dom.createTextNode(key)
        key_element.appendChild(key_text_node)
        key_value_element.appendChild(key_element)

        value_element = dom.createElement("value")
        value_text_mode = dom.createTextNode(value)
        value_element.appendChild(value_text_mode)
        key_value_element.appendChild(value_element)


    return dom.toxml()

def do_trim(session, args):
    """Attempt to trim the given LVHDSR"""
    util.SMlog("do_trim: %s" % args)
    sr_uuid = args["sr_uuid"]

    if TRIM_CAP not in util.sr_get_capability(sr_uuid):
        util.SMlog("Trim command ignored on unsupported SR %s" % sr_uuid)
        err_msg = {'errmsg': 'UnsupportedSRForTrim',
                   'opterr': 'Trim on [%s] not supported' % sr_uuid}
        return to_xml(err_msg)

    # Lock SR, get vg empty space details
    lock = Lock(vhdutil.LOCK_TYPE_SR, sr_uuid)
    got_lock = False
    for i in range(LOCK_RETRY_ATTEMPTS):
        got_lock = lock.acquireNoblock()
        if got_lock:
            break
        time.sleep(LOCK_RETRY_INTERVAL)

    if got_lock:
        try:
            vg_name = _vg_by_sr_uuid(sr_uuid)
            lv_name = sr_uuid + TRIM_LV_TAG
            lv_path = _lvpath_by_vg_lv_name(vg_name, lv_name)

            # Clean trim LV in case the previous trim attemp failed
            if lvutil.exists(lv_path):
                lvutil.remove(lv_path)

            # Perform a lvcreate and lvremove to trigger trim on the array
            lvutil.create(lv_name, 0, vg_name, activate=True,
                          size_in_percentage="100%F")
            lvutil.remove(lv_path,  config_param="issue_discards=1")
            util.SMlog("Trim on SR: %s complete. " % sr_uuid)
            return str(True)
        finally:
            lock.release()
    else:
        util.SMlog("Could not complete Trim on %s, Lock unavailable !" \
                   % sr_uuid)
        err_msg = {'errmsg': 'SRUnavailable',
                   'opterr': 'Unable to get SR lock [%s]' % sr_uuid}
        return to_xml(err_msg)

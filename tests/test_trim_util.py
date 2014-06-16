import unittest
import trim_util
import testlib

import mock


class AlwaysBusyLock(object):
    def acquireNoblock(self):
        return False


class TestTrimUtil(unittest.TestCase, testlib.XmlMixIn):
    @mock.patch('util.sr_get_capability')
    @testlib.with_context
    def test_do_trim_error_code_trim_not_supported(self,
                                                   context,
                                                   sr_get_capability):
        sr_get_capability.return_value = []
        context.setup_error_codes()

        result = trim_util.do_trim(None, {'sr_uuid': 'some-uuid'})

        self.assertXML("""
        <?xml version="1.0" ?>
        <trim_response>
            <key_value_pair>
                <key>opterr</key>
                <value>Trim on [some-uuid] not supported</value>
            </key_value_pair>
            <key_value_pair>
                <key>errmsg</key>
                <value>UnsupportedSRForTrim</value>
            </key_value_pair>
        </trim_response>
        """, result)

    @mock.patch('time.sleep')
    @mock.patch('lock.Lock')
    @mock.patch('util.sr_get_capability')
    @testlib.with_context
    def test_do_trim_unable_to_obtain_lock_on_sr(self,
                                                 context,
                                                 sr_get_capability,
                                                 MockLock,
                                                 sleep):
        MockLock.return_value = AlwaysBusyLock()
        sr_get_capability.return_value = [trim_util.TRIM_CAP]
        context.setup_error_codes()

        result = trim_util.do_trim(None, {'sr_uuid': 'some-uuid'})

        self.assertXML("""
        <?xml version="1.0" ?>
        <trim_response>
            <key_value_pair>
                <key>opterr</key>
                <value>Unable to get SR lock [some-uuid]</value>
            </key_value_pair>
            <key_value_pair>
                <key>errmsg</key>
                <value>SRUnavailable</value>
            </key_value_pair>
        </trim_response>
        """, result)

    @mock.patch('time.sleep')
    @mock.patch('lock.Lock')
    @mock.patch('util.sr_get_capability')
    @testlib.with_context
    def test_do_trim_sleeps_a_sec_and_retries_three_times(self,
                                                          context,
                                                          sr_get_capability,
                                                          MockLock,
                                                          sleep):
        MockLock.return_value = AlwaysBusyLock()
        sr_get_capability.return_value = [trim_util.TRIM_CAP]
        context.setup_error_codes()

        trim_util.do_trim(None, {'sr_uuid': 'some-uuid'})

        self.assertEquals([
                mock.call(1),
                mock.call(1),
                mock.call(1)
            ],
            sleep.mock_calls
        )


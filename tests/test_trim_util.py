import unittest
import trim_util
import testlib

import mock


class TestTrimUtil(unittest.TestCase, testlib.XmlMixIn):
    @mock.patch('util.sr_get_capability')
    @testlib.with_context
    def test_do_trim_error_code_trim_not_supported(self,
                                                   context,
                                                   sr_get_capability):
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

# -*- coding: utf-8 -*-
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/scancode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
import os

from commoncode.testcase import FileBasedTesting
from licensedcode import cache
from licensedcode import index
from licensedcode import models
from licensedcode.spans import Span

from scantext.match_text import Token
from scantext.match_text import get_full_matched_text
from scantext.match_text import reportable_tokens
from scantext.match_text import tokenize_matched_text

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class TestCollectLicenseMatchTexts(FileBasedTesting):
    test_data_dir = TEST_DATA_DIR

    def test_get_full_matched_text_base(self):
        rule_text = """
            Copyright [[some copyright]]
            THIS IS FROM [[THE CODEHAUS]] AND CONTRIBUTORS
            IN NO EVENT SHALL [[THE CODEHAUS]] OR ITS CONTRIBUTORS BE LIABLE
            EVEN IF ADVISED OF THE [[POSSIBILITY OF SUCH]] DAMAGE
        """

        rule = models.Rule(stored_text=rule_text, license_expression="test")
        idx = index.LicenseIndex([rule])

        querys = """
            foobar 45 . Copyright 2003 (C) James. All Rights Reserved.
            THIS IS FROM THE CODEHAUS AND CONTRIBUTORS
            IN NO EVENT SHALL THE best CODEHAUS OR ITS CONTRIBUTORS BE LIABLE
            EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. chabada DAMAGE 12 ABC dasdasda .
        """
        result = idx.match(query_string=querys)
        assert len(result) == 1
        match = result[0]

        # Note that there is a trailing space in that string
        expected = """Copyright [2003] ([C]) [James]. [All] [Rights] [Reserved].
            THIS IS FROM THE CODEHAUS AND CONTRIBUTORS
            IN NO EVENT SHALL THE [best] CODEHAUS OR ITS CONTRIBUTORS BE LIABLE
            EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. """
        matched_text = "".join(
            get_full_matched_text(match, query_string=querys, idx=idx, _usecache=False)
        )
        assert matched_text == expected

        expected_nh = """Copyright 2003 (C) James. All Rights Reserved.
            THIS IS FROM THE CODEHAUS AND CONTRIBUTORS
            IN NO EVENT SHALL THE best CODEHAUS OR ITS CONTRIBUTORS BE LIABLE
            EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. """
        matched_text_nh = "".join(
            get_full_matched_text(
                match, query_string=querys, idx=idx, _usecache=False, highlight=False
            )
        )
        assert matched_text_nh == expected_nh

        expected_origin_text = """Copyright 2003 (C) James. All Rights Reserved.
            THIS IS FROM THE CODEHAUS AND CONTRIBUTORS
            IN NO EVENT SHALL THE best CODEHAUS OR ITS CONTRIBUTORS BE LIABLE
            EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. """
        origin_matched_text = "".join(
            get_full_matched_text(
                match,
                query_string=querys,
                idx=idx,
                highlight_not_matched="{}",
            )
        )
        assert origin_matched_text == expected_origin_text

    def test_get_full_matched_text(self):
        rule_text = """
            Copyright [[some copyright]]
            THIS IS FROM [[THE CODEHAUS]] AND CONTRIBUTORS
            IN NO EVENT SHALL [[THE CODEHAUS]] OR ITS CONTRIBUTORS BE LIABLE
            EVEN IF ADVISED OF THE [[POSSIBILITY OF SUCH]] DAMAGE
        """

        rule = models.Rule(stored_text=rule_text, license_expression="test")
        idx = index.LicenseIndex([rule])

        querys = """
            foobar 45 Copyright 2003 (C) James. All Rights Reserved.
            THIS IS FROM THE CODEHAUS AND CONTRIBUTORS
            IN NO EVENT SHALL THE best CODEHAUS OR ITS CONTRIBUTORS BE LIABLE
            EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. chabada DAMAGE 12 ABC
        """
        result = idx.match(query_string=querys)
        assert len(result) == 1
        match = result[0]

        # Note that there is a trailing space in that string
        expected = """Copyright [2003] ([C]) [James]. [All] [Rights] [Reserved].
            THIS IS FROM THE CODEHAUS AND CONTRIBUTORS
            IN NO EVENT SHALL THE [best] CODEHAUS OR ITS CONTRIBUTORS BE LIABLE
            EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. """

        matched_text = "".join(
            get_full_matched_text(match, query_string=querys, idx=idx, _usecache=False)
        )
        assert matched_text == expected

        # the text is finally rstripped
        matched_text = match.matched_text(_usecache=False)
        assert matched_text == expected.rstrip()

        # test again using some HTML with tags
        # Note that there is a trailing space in that string
        expected = """Copyright <br>2003</br> (<br>C</br>) <br>James</br>. <br>All</br> <br>Rights</br> <br>Reserved</br>.
            THIS IS FROM THE CODEHAUS AND CONTRIBUTORS
            IN NO EVENT SHALL THE <br>best</br> CODEHAUS OR ITS CONTRIBUTORS BE LIABLE
            EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. """
        matched_text = "".join(
            get_full_matched_text(
                match,
                query_string=querys,
                idx=idx,
                highlight_not_matched="<br>{}</br>",
                _usecache=False,
            )
        )
        assert matched_text == expected

        # test again using whole_lines
        expected = """            foobar 45 Copyright 2003 (C) James. All Rights Reserved.
            THIS IS FROM THE CODEHAUS AND CONTRIBUTORS
            IN NO EVENT SHALL THE best CODEHAUS OR ITS CONTRIBUTORS BE LIABLE
            EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. chabada DAMAGE 12 ABC\n"""
        matched_text = "".join(
            get_full_matched_text(
                match,
                query_string=querys,
                idx=idx,
                highlight_not_matched="{}",
                whole_lines=True,
            )
        )
        assert matched_text == expected

    def test_get_full_matched_text_does_not_munge_underscore(self):
        rule_text = "MODULE_LICENSE_GPL"

        rule = models.Rule(stored_text=rule_text, license_expression="test")
        idx = index.LicenseIndex([rule])

        querys = "MODULE_LICENSE_GPL"
        result = idx.match(query_string=querys)
        assert len(result) == 1
        match = result[0]

        expected = "MODULE_LICENSE_GPL"
        matched_text = "".join(
            get_full_matched_text(match, query_string=querys, idx=idx, _usecache=False)
        )
        assert matched_text == expected

    def test_get_full_matched_text_does_not_munge_plus(self):
        rule_text = "MODULE_LICENSE_GPL+ +"

        rule = models.Rule(stored_text=rule_text, license_expression="test")
        idx = index.LicenseIndex([rule])

        querys = "MODULE_LICENSE_GPL+ +"
        result = idx.match(query_string=querys)
        assert len(result) == 1
        match = result[0]

        expected = "MODULE_LICENSE_GPL+ +\n"
        matched_text = "".join(
            get_full_matched_text(match, query_string=querys, idx=idx, _usecache=False)
        )
        assert matched_text == expected

    def test_tokenize_matched_text_does_cache_last_call_from_query_string_and_location(
        self,
    ):
        dictionary = {"module": 0, "license": 1, "gpl+": 2}
        location = None
        query_string = "the MODULE_LICENSE_GPL+ foobar"
        result1 = tokenize_matched_text(location, query_string, dictionary)
        result2 = tokenize_matched_text(location, query_string, dictionary)
        assert result2 is result1

        location = self.get_test_loc("matched_text/tokenize_matched_text_query.txt")
        query_string = None
        result3 = tokenize_matched_text(location, query_string, dictionary)
        assert result3 is not result2
        assert result3 == result2

        result4 = tokenize_matched_text(location, query_string, dictionary)
        assert result4 is result3

    def test_tokenize_matched_text_does_return_correct_tokens(self):
        querys = """
            foobar 45 Copyright 2003 (C) James. All Rights Reserved.  THIS
            IS FROM THE CODEHAUS AND CONTRIBUTORS
        """
        dictionary = dict(
            this=0, event=1, possibility=2, reserved=3, liable=5, copyright=6
        )
        result = tokenize_matched_text(
            location=None, query_string=querys, dictionary=dictionary
        )
        expected = [
            Token(
                value="\n",
                line_num=1,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="            ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="foobar",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="45",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Copyright",
                line_num=2,
                pos=0,
                is_text=True,
                is_matched=False,
                is_known=True,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="2003",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" (",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="C",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=") ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="James",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=". ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="All",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Rights",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Reserved",
                line_num=2,
                pos=1,
                is_text=True,
                is_matched=False,
                is_known=True,
            ),
            Token(
                value=".  ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="THIS",
                line_num=2,
                pos=2,
                is_text=True,
                is_matched=False,
                is_known=True,
            ),
            Token(
                value="\n",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="            ",
                line_num=3,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="IS",
                line_num=3,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=3,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="FROM",
                line_num=3,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=3,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="THE",
                line_num=3,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=3,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="CODEHAUS",
                line_num=3,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=3,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="AND",
                line_num=3,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=3,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="CONTRIBUTORS",
                line_num=3,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="\n",
                line_num=3,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="        \n",
                line_num=4,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
        ]

        assert result == expected

    def test_tokenize_matched_text_does_not_crash_on_turkish_unicode(self):
        querys = "İrəli"
        result = tokenize_matched_text(
            location=None, query_string=querys, dictionary={}
        )

        expected = [
            Token(
                value="i",
                line_num=1,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="rəli",
                line_num=1,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="\n",
                line_num=1,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
        ]
        assert result == expected

    def test_tokenize_matched_text_behaves_like_query_tokenizer_on_turkish_unicode(
        self,
    ):
        from licensedcode.tokenize import query_tokenizer

        querys = "İrəli"
        matched_text_result = tokenize_matched_text(
            location=None, query_string=querys, dictionary={}
        )
        matched_text_result = [t.value for t in matched_text_result]
        query_tokenizer_result = list(query_tokenizer(querys))

        if matched_text_result[-1] == "\n":
            matched_text_result = matched_text_result[:-1]

        assert matched_text_result == query_tokenizer_result

    def test_reportable_tokens_filter_tokens_does_not_strip_last_token_value(self):
        tokens = [
            Token(
                value="\n",
                line_num=1,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="            ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="foobar",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="45",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Copyright",
                line_num=2,
                pos=0,
                is_text=True,
                is_matched=False,
                is_known=True,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="2003",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" (",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="C",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=") ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="James",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=". ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="All",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Rights",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Reserved",
                line_num=2,
                pos=1,
                is_text=True,
                is_matched=False,
                is_known=True,
            ),
            Token(
                value=".  ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="THIS",
                line_num=2,
                pos=2,
                is_text=True,
                is_matched=False,
                is_known=True,
            ),
            Token(
                value="\n",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="            ",
                line_num=3,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
        ]

        match_qspan = Span(0, 1)
        result = list(
            reportable_tokens(
                tokens, match_qspan, start_line=1, end_line=2, whole_lines=False
            )
        )
        expected = [
            Token(
                value="Copyright",
                line_num=2,
                pos=0,
                is_text=True,
                is_matched=True,
                is_known=True,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="2003",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" (",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="C",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=") ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="James",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=". ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="All",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Rights",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Reserved",
                line_num=2,
                pos=1,
                is_text=True,
                is_matched=True,
                is_known=True,
            ),
            Token(
                value=".  ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
        ]

        assert result == expected

        # test again with whole lines
        match_qspan = Span(0, 1)
        result = list(
            reportable_tokens(
                tokens, match_qspan, start_line=1, end_line=2, whole_lines=True
            )
        )
        expected = [
            Token(
                value="\n",
                line_num=1,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="            ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="foobar",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="45",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Copyright",
                line_num=2,
                pos=0,
                is_text=True,
                is_matched=True,
                is_known=True,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="2003",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" (",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="C",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=") ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="James",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=". ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="All",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Rights",
                line_num=2,
                pos=-1,
                is_text=True,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value=" ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="Reserved",
                line_num=2,
                pos=1,
                is_text=True,
                is_matched=True,
                is_known=True,
            ),
            Token(
                value=".  ",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
            Token(
                value="THIS",
                line_num=2,
                pos=2,
                is_text=True,
                is_matched=False,
                is_known=True,
            ),
            Token(
                value="\n",
                line_num=2,
                pos=-1,
                is_text=False,
                is_matched=False,
                is_known=False,
            ),
        ]

        assert result == expected

    def test_matched_text_is_collected_correctly_end2end(self):
        rules_data_dir = self.get_test_loc("matched_text/index/rules")
        query_location = self.get_test_loc("matched_text/query.txt")
        rules = models.load_rules(rules_data_dir)
        idx = index.LicenseIndex(rules)

        results = [
            match.matched_text(_usecache=False)
            for match in idx.match(location=query_location)
        ]
        expected = [
            "This source code is licensed under both the Apache 2.0 license "
            "(found in the\n#  LICENSE",
            "This source code is licensed under [both] [the] [Apache] [2].[0] license "
            "(found in the\n#  LICENSE file in the root directory of this source tree)",
            "GPLv2 (",
        ]
        assert results == expected

    def check_matched_texts(self, test_loc, expected_texts, whole_lines=True):
        idx = cache.get_index()
        test_loc = self.get_test_loc(test_loc)
        matches = idx.match(location=test_loc)
        matched_texts = [
            m.matched_text(whole_lines=whole_lines, highlight=False, _usecache=False)
            for m in matches
        ]
        assert matched_texts == expected_texts

    def test_matched_text_is_collected_correctly_end2end_for_spdx_match_whole_lines(
        self,
    ):
        self.check_matched_texts(
            test_loc="matched_text/spdx/query.txt",
            expected_texts=["@REM # SPDX-License-Identifier: BSD-2-Clause-Patent"],
            whole_lines=True,
        )

    def test_matched_text_is_collected_correctly_end2end_for_spdx_match_plain(self):
        self.check_matched_texts(
            test_loc="matched_text/spdx/query.txt",
            expected_texts=["SPDX-License-Identifier: BSD-2-Clause-Patent"],
            whole_lines=False,
        )

    def test_matched_text_is_not_truncated_with_unicode_diacritic_input_from_query(
        self,
    ):
        idx = cache.get_index()
        querys_with_diacritic_unicode = "İ license MIT"
        result = idx.match(query_string=querys_with_diacritic_unicode)
        assert len(result) == 1
        match = result[0]
        expected = "license MIT"
        matched_text = match.matched_text(
            _usecache=False,
        )
        assert matched_text == expected

    def test_matched_text_is_not_truncated_with_unicode_diacritic_input_from_file(self):
        idx = cache.get_index()
        file_with_diacritic_unicode_location = self.get_test_loc(
            "matched_text/unicode_text/main3.js"
        )
        result = idx.match(location=file_with_diacritic_unicode_location)
        assert len(result) == 1
        match = result[0]
        expected = "license MIT"
        matched_text = match.matched_text(_usecache=False)
        assert matched_text == expected

    def test_matched_text_is_not_truncated_with_unicode_diacritic_input_from_query_whole_lines(
        self,
    ):
        idx = cache.get_index()
        querys_with_diacritic_unicode = "İ license MIT"
        result = idx.match(query_string=querys_with_diacritic_unicode)
        assert len(result) == 1
        match = result[0]
        expected = "[İ] license MIT"
        matched_text = match.matched_text(_usecache=False, whole_lines=True)
        assert matched_text == expected

    def test_matched_text_is_not_truncated_with_unicode_diacritic_input_with_diacritic_in_rules(
        self,
    ):
        rule_dir = self.get_test_loc("matched_text/turkish_unicode/rules")
        idx = index.LicenseIndex(models.load_rules(rule_dir))
        query_loc = self.get_test_loc("matched_text/turkish_unicode/query")
        matches = idx.match(location=query_loc)
        matched_texts = [
            m.matched_text(whole_lines=False, highlight=False, _usecache=False)
            for m in matches
        ]

        expected = [
            "Licensed under the Apache License, Version 2.0\r\nnext_label=irəli",
            "İ license MIT",
            "İ license MIT",
            "Licensed under the Apache License, Version 2.0\r\nnext_label=irəli",
            "lİcense mit",
        ]

        assert matched_texts == expected

    def test_matched_text_is_not_truncated_with_unicode_diacritic_input_and_full_index(
        self,
    ):
        expected = [
            "Licensed under the Apache License, Version 2.0",
            "license MIT",
            "license MIT",
            "Licensed under the Apache License, Version 2.0",
        ]

        self.check_matched_texts(
            test_loc="matched_text/turkish_unicode/query",
            expected_texts=expected,
            whole_lines=False,
        )

    def test_matched_text_does_not_ignores_whole_lines_in_binary_with_small_index(self):
        rule_dir = self.get_test_loc("matched_text/binary_text/rules")
        idx = index.LicenseIndex(models.load_rules(rule_dir))
        query_loc = self.get_test_loc("matched_text/binary_text/gosu")
        matches = idx.match(location=query_loc)
        matched_texts = [
            m.matched_text(whole_lines=True, highlight=False, _usecache=False)
            for m in matches
        ]

        expected = [
            "{{ .Self }} license: GPL-3 (full text at https://github.com/tianon/gosu)"
        ]

        assert matched_texts == expected

    def test_matched_text_does_not_ignores_whole_lines_in_binary_against_full_index(
        self,
    ):
        expected = [
            "{{ .Self }} license: GPL-3 (full text at https://github.com/tianon/gosu)"
        ]
        self.check_matched_texts(
            test_loc="matched_text/binary_text/gosu",
            expected_texts=expected,
            whole_lines=True,
        )

    def test_matched_text_is_collected_correctly_in_binary_ffmpeg_windows_whole_lines(
        self,
    ):
        expected_texts = [
            "--enable-gpl --enable-version3 --enable-dxva2 --enable-libmfx --enable-nvenc "
            "--enable-avisynth --enable-bzlib --enable-fontconfig --enable-frei0r "
            "--enable-gnutls --enable-iconv --enable-libass --enable-libbluray "
            "--enable-libbs2b --enable-libcaca --enable-libfreetype --enable-libgme "
            "--enable-libgsm --enable-libilbc --enable-libmodplug --enable-libmp3lame "
            "--enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 "
            "--enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libsnappy "
            "--enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame "
            "--enable-libvidstab --enable-libvo-amrwbenc --enable-libvorbis "
            "--enable-libvpx --enable-libwavpack --enable-libwebp --enable-libx264 "
            "--enable-libx265 --enable-libxavs --enable-libxvid --enable-libzimg "
            "--enable-lzma --enable-decklink --enable-zlib",
            "%sconfiguration: --enable-gpl --enable-version3 --enable-dxva2 "
            "--enable-libmfx --enable-nvenc --enable-avisynth --enable-bzlib "
            "--enable-fontconfig --enable-frei0r --enable-gnutls --enable-iconv "
            "--enable-libass --enable-libbluray --enable-libbs2b --enable-libcaca "
            "--enable-libfreetype --enable-libgme --enable-libgsm --enable-libilbc "
            "--enable-libmodplug --enable-libmp3lame --enable-libopencore-amrnb "
            "--enable-libopencore-amrwb --enable-libopenh264 --enable-libopenjpeg "
            "--enable-libopus --enable-librtmp --enable-libsnappy --enable-libsoxr "
            "--enable-libspeex --enable-libtheora --enable-libtwolame --enable-libvidstab "
            "--enable-libvo-amrwbenc --enable-libvorbis --enable-libvpx "
            "--enable-libwavpack --enable-libwebp --enable-libx264 --enable-libx265 "
            "--enable-libxavs --enable-libxvid --enable-libzimg --enable-lzma "
            "--enable-decklink --enable-zlib",
            "%s is free software; you can redistribute it and/or modify\n"
            "it under the terms of the GNU General Public License as published by\n"
            "the Free Software Foundation; either version 3 of the License, or\n"
            "(at your option) any later version.\n"
            "%s is distributed in the hope that it will be useful,\n"
            "but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
            "GNU General Public License for more details.\n"
            "You should have received a copy of the GNU General Public License\n"
            "along with %s.  If not, see <http://www.gnu.org/licenses/>.\n"
            "File formats:\n"
            "D. = Demuxing supported\n"
            ".E = Muxing supported\n"
            "%s%s %-15s %s\n"
            "Devices:\n"
            "Codecs:\n"
            "D..... = Decoding supported\n"
            ".E.... = Encoding supported\n"
            "..V... = Video codec\n"
            "No option name near '%s'\n"
            "Unable to parse '%s': %s\n"
            "Setting '%s' to value '%s'\n"
            "Option '%s' not found\n"
            "--enable-gpl --enable-version3 --enable-dxva2 --enable-libmfx --enable-nvenc "
            "--enable-avisynth --enable-bzlib --enable-fontconfig --enable-frei0r "
            "--enable-gnutls --enable-iconv --enable-libass --enable-libbluray "
            "--enable-libbs2b --enable-libcaca --enable-libfreetype --enable-libgme "
            "--enable-libgsm --enable-libilbc --enable-libmodplug --enable-libmp3lame "
            "--enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 "
            "--enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libsnappy "
            "--enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame "
            "--enable-libvidstab --enable-libvo-amrwbenc --enable-libvorbis "
            "--enable-libvpx --enable-libwavpack --enable-libwebp --enable-libx264 "
            "--enable-libx265 --enable-libxavs --enable-libxvid --enable-libzimg "
            "--enable-lzma --enable-decklink --enable-zlib",
            "--enable-gpl --enable-version3 --enable-dxva2 --enable-libmfx --enable-nvenc "
            "--enable-avisynth --enable-bzlib --enable-fontconfig --enable-frei0r "
            "--enable-gnutls --enable-iconv --enable-libass --enable-libbluray "
            "--enable-libbs2b --enable-libcaca --enable-libfreetype --enable-libgme "
            "--enable-libgsm --enable-libilbc --enable-libmodplug --enable-libmp3lame "
            "--enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 "
            "--enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libsnappy "
            "--enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame "
            "--enable-libvidstab --enable-libvo-amrwbenc --enable-libvorbis "
            "--enable-libvpx --enable-libwavpack --enable-libwebp --enable-libx264 "
            "--enable-libx265 --enable-libxavs --enable-libxvid --enable-libzimg "
            "--enable-lzma --enable-decklink --enable-zlib",
            "libavfilter license: GPL version 3 or later",
            "--enable-gpl --enable-version3 --enable-dxva2 --enable-libmfx --enable-nvenc "
            "--enable-avisynth --enable-bzlib --enable-fontconfig --enable-frei0r "
            "--enable-gnutls --enable-iconv --enable-libass --enable-libbluray "
            "--enable-libbs2b --enable-libcaca --enable-libfreetype --enable-libgme "
            "--enable-libgsm --enable-libilbc --enable-libmodplug --enable-libmp3lame "
            "--enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 "
            "--enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libsnappy "
            "--enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame "
            "--enable-libvidstab --enable-libvo-amrwbenc --enable-libvorbis "
            "--enable-libvpx --enable-libwavpack --enable-libwebp --enable-libx264 "
            "--enable-libx265 --enable-libxavs --enable-libxvid --enable-libzimg "
            "--enable-lzma --enable-decklink --enable-zlib",
            "libavformat license: GPL version 3 or later",
            "--enable-gpl --enable-version3 --enable-dxva2 --enable-libmfx --enable-nvenc "
            "--enable-avisynth --enable-bzlib --enable-fontconfig --enable-frei0r "
            "--enable-gnutls --enable-iconv --enable-libass --enable-libbluray "
            "--enable-libbs2b --enable-libcaca --enable-libfreetype --enable-libgme "
            "--enable-libgsm --enable-libilbc --enable-libmodplug --enable-libmp3lame "
            "--enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 "
            "--enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libsnappy "
            "--enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame "
            "--enable-libvidstab --enable-libvo-amrwbenc --enable-libvorbis "
            "--enable-libvpx --enable-libwavpack --enable-libwebp --enable-libx264 "
            "--enable-libx265 --enable-libxavs --enable-libxvid --enable-libzimg "
            "--enable-lzma --enable-decklink --enable-zlib",
            "libavcodec license: GPL version 3 or later",
            "--enable-gpl --enable-version3 --enable-dxva2 --enable-libmfx --enable-nvenc "
            "--enable-avisynth --enable-bzlib --enable-fontconfig --enable-frei0r "
            "--enable-gnutls --enable-iconv --enable-libass --enable-libbluray "
            "--enable-libbs2b --enable-libcaca --enable-libfreetype --enable-libgme "
            "--enable-libgsm --enable-libilbc --enable-libmodplug --enable-libmp3lame "
            "--enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 "
            "--enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libsnappy "
            "--enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame "
            "--enable-libvidstab --enable-libvo-amrwbenc --enable-libvorbis "
            "--enable-libvpx --enable-libwavpack --enable-libwebp --enable-libx264 "
            "--enable-libx265 --enable-libxavs --enable-libxvid --enable-libzimg "
            "--enable-lzma --enable-decklink --enable-zlib",
            "libpostproc license: GPL version 3 or later",
            "--enable-gpl --enable-version3 --enable-dxva2 --enable-libmfx --enable-nvenc "
            "--enable-avisynth --enable-bzlib --enable-fontconfig --enable-frei0r "
            "--enable-gnutls --enable-iconv --enable-libass --enable-libbluray "
            "--enable-libbs2b --enable-libcaca --enable-libfreetype --enable-libgme "
            "--enable-libgsm --enable-libilbc --enable-libmodplug --enable-libmp3lame "
            "--enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 "
            "--enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libsnappy "
            "--enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame "
            "--enable-libvidstab --enable-libvo-amrwbenc --enable-libvorbis "
            "--enable-libvpx --enable-libwavpack --enable-libwebp --enable-libx264 "
            "--enable-libx265 --enable-libxavs --enable-libxvid --enable-libzimg "
            "--enable-lzma --enable-decklink --enable-zlib",
            "libswresample license: GPL version 3 or later",
            "--enable-gpl --enable-version3 --enable-dxva2 --enable-libmfx --enable-nvenc "
            "--enable-avisynth --enable-bzlib --enable-fontconfig --enable-frei0r "
            "--enable-gnutls --enable-iconv --enable-libass --enable-libbluray "
            "--enable-libbs2b --enable-libcaca --enable-libfreetype --enable-libgme "
            "--enable-libgsm --enable-libilbc --enable-libmodplug --enable-libmp3lame "
            "--enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 "
            "--enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libsnappy "
            "--enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame "
            "--enable-libvidstab --enable-libvo-amrwbenc --enable-libvorbis "
            "--enable-libvpx --enable-libwavpack --enable-libwebp --enable-libx264 "
            "--enable-libx265 --enable-libxavs --enable-libxvid --enable-libzimg "
            "--enable-lzma --enable-decklink --enable-zlib",
            "libswscale license: GPL version 3 or later",
            "--enable-gpl --enable-version3 --enable-dxva2 --enable-libmfx --enable-nvenc "
            "--enable-avisynth --enable-bzlib --enable-fontconfig --enable-frei0r "
            "--enable-gnutls --enable-iconv --enable-libass --enable-libbluray "
            "--enable-libbs2b --enable-libcaca --enable-libfreetype --enable-libgme "
            "--enable-libgsm --enable-libilbc --enable-libmodplug --enable-libmp3lame "
            "--enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopenh264 "
            "--enable-libopenjpeg --enable-libopus --enable-librtmp --enable-libsnappy "
            "--enable-libsoxr --enable-libspeex --enable-libtheora --enable-libtwolame "
            "--enable-libvidstab --enable-libvo-amrwbenc --enable-libvorbis "
            "--enable-libvpx --enable-libwavpack --enable-libwebp --enable-libx264 "
            "--enable-libx265 --enable-libxavs --enable-libxvid --enable-libzimg "
            "--enable-lzma --enable-decklink --enable-zlib",
            "libavutil license: GPL version 3 or later",
            "This software is derived from the GNU GPL XviD codec (1.3.0).",
        ]

        self.check_matched_texts(
            test_loc="matched_text/ffmpeg/ffmpeg.exe",
            expected_texts=expected_texts,
            whole_lines=True,
        )

    def test_matched_text_is_collected_correctly_in_binary_ffmpeg_windows_not_whole_lines(
        self,
    ):
        expected_texts = [
            "enable-gpl --enable-version3 --",
            "enable-gpl --enable-version3 --",
            "is free software; you can redistribute it and/or modify\n"
            "it under the terms of the GNU General Public License as published by\n"
            "the Free Software Foundation; either version 3 of the License, or\n"
            "(at your option) any later version.\n"
            "%s is distributed in the hope that it will be useful,\n"
            "but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
            "GNU General Public License for more details.\n"
            "You should have received a copy of the GNU General Public License\n"
            "along with %s.  If not, see <http://www.gnu.org/licenses/>.\n"
            "File formats:\n"
            "D. = Demuxing supported\n"
            ".E = Muxing supported\n"
            "%s%s %-15s %s\n"
            "Devices:\n"
            "Codecs:\n"
            "D..... = Decoding supported\n"
            ".E.... = Encoding supported\n"
            "..V... = Video codec\n"
            "No option name near '%s'\n"
            "Unable to parse '%s': %s\n"
            "Setting '%s' to value '%s'\n"
            "Option '%s' not found\n"
            "--enable-gpl --",
            "enable-gpl --enable-version3 --",
            "license: GPL version 3 or later",
            "enable-gpl --enable-version3 --",
            "license: GPL version 3 or later",
            "enable-gpl --enable-version3 --",
            "license: GPL version 3 or later",
            "enable-gpl --enable-version3 --",
            "license: GPL version 3 or later",
            "enable-gpl --enable-version3 --",
            "license: GPL version 3 or later",
            "enable-gpl --enable-version3 --",
            "license: GPL version 3 or later",
            "enable-gpl --enable-version3 --",
            "license: GPL version 3 or later",
            "This software is derived from the GNU GPL XviD codec (",
        ]

        self.check_matched_texts(
            test_loc="matched_text/ffmpeg/ffmpeg.exe",
            expected_texts=expected_texts,
            whole_lines=False,
        )

    def test_matched_text_is_collected_correctly_in_binary_ffmpeg_elf_whole_lines(self):
        expected_texts = [
            "--prefix=/usr --extra-version=0ubuntu0.1 --build-suffix=-ffmpeg "
            "--toolchain=hardened --libdir=/usr/lib/x86_64-linux-gnu "
            "--incdir=/usr/include/x86_64-linux-gnu --cc=cc --cxx=g++ --enable-gpl "
            "--enable-shared --disable-stripping --disable-decoder=libopenjpeg "
            "--disable-decoder=libschroedinger --enable-avresample --enable-avisynth "
            "--enable-gnutls --enable-ladspa --enable-libass --enable-libbluray "
            "--enable-libbs2b --enable-libcaca --enable-libcdio --enable-libflite "
            "--enable-libfontconfig --enable-libfreetype --enable-libfribidi "
            "--enable-libgme --enable-libgsm --enable-libmodplug --enable-libmp3lame "
            "--enable-libopenjpeg --enable-libopus --enable-libpulse --enable-librtmp "
            "--enable-libschroedinger --enable-libshine --enable-libsnappy "
            "--enable-libsoxr --enable-libspeex --enable-libssh --enable-libtheora "
            "--enable-libtwolame --enable-libvorbis --enable-libvpx --enable-libwavpack "
            "--enable-libwebp --enable-libx265 --enable-libxvid --enable-libzvbi "
            "--enable-openal --enable-opengl --enable-x11grab --enable-libdc1394 "
            "--enable-libiec61883 --enable-libzmq --enable-frei0r --enable-libx264 "
            "--enable-libopencv",
            "%sconfiguration: --prefix=/usr --extra-version=0ubuntu0.1 "
            "--build-suffix=-ffmpeg --toolchain=hardened "
            "--libdir=/usr/lib/x86_64-linux-gnu --incdir=/usr/include/x86_64-linux-gnu "
            "--cc=cc --cxx=g++ --enable-gpl --enable-shared --disable-stripping "
            "--disable-decoder=libopenjpeg --disable-decoder=libschroedinger "
            "--enable-avresample --enable-avisynth --enable-gnutls --enable-ladspa "
            "--enable-libass --enable-libbluray --enable-libbs2b --enable-libcaca "
            "--enable-libcdio --enable-libflite --enable-libfontconfig "
            "--enable-libfreetype --enable-libfribidi --enable-libgme --enable-libgsm "
            "--enable-libmodplug --enable-libmp3lame --enable-libopenjpeg "
            "--enable-libopus --enable-libpulse --enable-librtmp --enable-libschroedinger "
            "--enable-libshine --enable-libsnappy --enable-libsoxr --enable-libspeex "
            "--enable-libssh --enable-libtheora --enable-libtwolame --enable-libvorbis "
            "--enable-libvpx --enable-libwavpack --enable-libwebp --enable-libx265 "
            "--enable-libxvid --enable-libzvbi --enable-openal --enable-opengl "
            "--enable-x11grab --enable-libdc1394 --enable-libiec61883 --enable-libzmq "
            "--enable-frei0r --enable-libx264 --enable-libopencv",
            "%s is free software; you can redistribute it and/or modify\n"
            "it under the terms of the GNU General Public License as published by\n"
            "the Free Software Foundation; either version 2 of the License, or\n"
            "(at your option) any later version.\n"
            "%s is distributed in the hope that it will be useful,\n"
            "but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
            "GNU General Public License for more details.\n"
            "You should have received a copy of the GNU General Public License\n"
            "along with %s; if not, write to the Free Software\n"
            "Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA",
        ]

        self.check_matched_texts(
            test_loc="matched_text/ffmpeg/ffmpeg",
            expected_texts=expected_texts,
            whole_lines=True,
        )

    def test_matched_text_is_collected_correctly_in_binary_ffmpeg_static_whole_lines(
        self,
    ):
        expected_texts = ["libswresample license: LGPL version 2.1 or later"]
        self.check_matched_texts(
            test_loc="matched_text/ffmpeg/libavsample.lib",
            expected_texts=expected_texts,
            whole_lines=True,
        )

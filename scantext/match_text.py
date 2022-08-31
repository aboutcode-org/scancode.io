#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/scancode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import attr
from licensedcode import query
from licensedcode.spans import Span
from licensedcode.stopwords import STOPWORDS
from licensedcode.tokenize import index_tokenizer
from licensedcode.tokenize import matched_query_text_tokenizer

TRACE = False
TRACE_MATCHED_TEXT = False
TRACE_MATCHED_TEXT_DETAILS = False


def logger_debug(*args):
    pass


if TRACE or TRACE_MATCHED_TEXT or TRACE_MATCHED_TEXT_DETAILS:

    use_print = True
    if use_print:
        prn = print
    else:
        import logging
        import sys

        logger = logging.getLogger(__name__)
        # logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
        logging.basicConfig(stream=sys.stdout)
        logger.setLevel(logging.DEBUG)
        prn = logger.debug

    def logger_debug(*args):
        return prn(" ".join(isinstance(a, str) and a or repr(a) for a in args))

    def _debug_print_matched_query_text(match, extras=5):
        """
        Print a matched query text including `extras` tokens before and after
        the match. Used for debugging license matches.
        """
        # Create a fake new match with extra tokens before and after
        new_match = match.combine(match)
        new_qstart = max([0, match.qstart - extras])
        new_qend = min([match.qend + extras, len(match.query.tokens)])
        new_qspan = Span(new_qstart, new_qend)
        new_match.qspan = new_qspan

        logger_debug(new_match)
        logger_debug(" MATCHED QUERY TEXT with extras")
        qt = new_match.matched_text(whole_lines=False)
        logger_debug(qt)


@attr.s(slots=True)
class Token:
    """
    Used to represent a token in collected query-side matched texts and SPDX
    identifiers.

    ``matches`` is a lits of LicenseMatch to accomodate for overlapping matches.
    For example, say we have these two matched text portions:
    QueryText: this is licensed under GPL or MIT
    Match1:    this is licensed under GPL
    Match2:            licensed under GPL or MIT

    Each Token would be to assigned one or more LicenseMatch:
        this:         Match1            : yellow
        is:           Match1            : yellow
        licensed:     Match1, Match2    : orange (mixing yellow and pink colors)
        under:        Match1, Match2    : orange (mixing yellow and pink colors)
        GPL:          Match1, Match2    : orange (mixing yellow and pink colors)
        or:           Match2            : pink
        MIT:          Match2            : pink
    """

    # original text value for this token.
    value = attr.ib()

    # line number, one-based
    line_num = attr.ib()

    # absolute position for known tokens, zero-based. -1 for unknown tokens
    pos = attr.ib(default=-1)

    # True if text/alpha False if this is punctuation or spaces
    is_text = attr.ib(default=False)

    # True if part of a match
    is_matched = attr.ib(default=False)

    # True if this is a known token
    is_known = attr.ib(default=False)

    # List of LicenseMatch ids that match this token
    match_ids = attr.ib(attr.Factory(list))


def tokenize_matched_text(
    location,
    query_string,
    dictionary,
    start_line=1,
    trace=TRACE_MATCHED_TEXT_DETAILS,
):
    """
    Yield Token objects with pos and line number collected from the file at
    `location` or the `query_string` string. `dictionary` is the index mapping
    of tokens to token ids.
    """
    pos = 0
    qls = query.query_lines(
        location=location,
        query_string=query_string,
        strip=False,
        start_line=start_line,
    )
    for line_num, line in qls:
        if trace:
            logger_debug(
                "  tokenize_matched_text:", "line_num:", line_num, "line:", line
            )

        for is_text, token_str in matched_query_text_tokenizer(line):
            if trace:
                logger_debug("     is_text:", is_text, "token_str:", repr(token_str))

            # Determine if a token is is_known in the license index or not. This
            # is essential as we need to realign the query-time tokenization
            # with the full text to report proper matches.
            if is_text and token_str and token_str.strip():

                # we retokenize using the query tokenizer:
                # 1. to lookup for is_known tokens in the index dictionary

                # 2. to ensure the number of tokens is the same in both
                # tokenizers (though, of course, the case will differ as the
                # regular query tokenizer ignores case and punctuations).
                qtokenized = list(index_tokenizer(token_str))
                if not qtokenized:

                    yield Token(
                        value=token_str,
                        line_num=line_num,
                        is_text=is_text,
                        is_known=False,
                        pos=-1,
                    )

                elif len(qtokenized) == 1:
                    is_known = qtokenized[0] in dictionary
                    if is_known:
                        p = pos
                        pos += 1
                    else:
                        p = -1

                    yield Token(
                        value=token_str,
                        line_num=line_num,
                        is_text=is_text,
                        is_known=is_known,
                        pos=p,
                    )
                else:
                    # we have two or more tokens from the original query mapped
                    # to a single matched text tokenizer token.
                    for qtoken in qtokenized:
                        is_known = qtoken in dictionary
                        if is_known:
                            p = pos
                            pos += 1
                        else:
                            p = -1

                        yield Token(
                            value=qtoken,
                            line_num=line_num,
                            is_text=is_text,
                            is_known=is_known,
                            pos=p,
                        )
            else:

                yield Token(
                    value=token_str,
                    line_num=line_num,
                    is_text=False,
                    is_known=False,
                    pos=-1,
                )

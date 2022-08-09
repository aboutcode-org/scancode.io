#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/scancode-toolkit for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

from enum import IntEnum
from itertools import groupby

import attr
from attr import validators
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


@attr.s(slots=True, frozen=True)
class Token(object):
    """
    Used to represent a token in collected query-side matched texts and SPDX
    identifiers.
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


def tokenize_matched_text(
    location,
    query_string,
    dictionary,
    start_line=1,
    _cache={},
):
    """
    Return a list of Token objects with pos and line number collected from the
    file at `location` or the `query_string` string. `dictionary` is the index
    mapping a token string to a token id.

    NOTE: the _cache={} arg IS A GLOBAL mutable by design.
    """
    key = location, query_string, start_line
    cached = _cache.get(key)
    if cached:
        return cached
    # we only cache the last call
    _cache.clear()
    _cache[key] = result = list(
        _tokenize_matched_text(
            location=location,
            query_string=query_string,
            dictionary=dictionary,
            start_line=start_line,
        )
    )
    return result


def _tokenize_matched_text(
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
                "  _tokenize_matched_text:", "line_num:", line_num, "line:", line
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

                # NOTE: we have a rare Unicode bug/issue because of some Unicode
                # codepoint such as some Turkish characters that decompose to
                # char + punct when casefolded. This should be fixed in Unicode
                # release 14 and up and likely implemented in Python 3.10 and up
                # See https://github.com/nexB/scancode-toolkit/issues/1872
                # See also: https://bugs.python.org/issue34723#msg359514
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


def reportable_tokens(
    tokens,
    match_qspan,
    start_line,
    end_line,
    whole_lines=False,
    trace=TRACE_MATCHED_TEXT_DETAILS,
):
    """
    Yield Tokens from a ``tokens`` iterable of Token objects (built from a query-
    side scanned file or string) that are inside a ``match_qspan`` matched Span
    starting at `start_line` and ending at ``end_line``. If whole_lines is True,
    also yield unmatched Tokens that are before and after the match and on the
    first and last line of a match (unless the lines are very long text lines or
    the match is from binary content.)

    As a side effect, known matched tokens are tagged as "is_matched=True" if
    they are matched.

    If ``whole_lines`` is True, any token within matched lines range is
    included. Otherwise, a token is included if its position is within the
    matched ``match_qspan`` or it is a punctuation token immediately after the
    matched ``match_qspan`` even though not matched.
    """
    start = match_qspan.start
    end = match_qspan.end

    started = False
    finished = False

    end_pos = 0
    last_pos = 0
    for real_pos, tok in enumerate(tokens):
        if trace:
            logger_debug("reportable_tokens: processing", real_pos, tok)

        # ignore tokens outside the matched lines range
        if tok.line_num < start_line:
            if trace:
                logger_debug(
                    "  tok.line_num < start_line:", tok.line_num, "<", start_line
                )

            continue

        if tok.line_num > end_line:
            if trace:
                logger_debug("  tok.line_num > end_line", tok.line_num, ">", end_line)

            break

        if trace:
            logger_debug("reportable_tokens:", real_pos, tok)

        is_included = False

        # tagged known matched tokens (useful for highlighting)
        if tok.pos != -1 and tok.is_known and tok.pos in match_qspan:
            tok = attr.evolve(tok, is_matched=True)
            is_included = True
            if trace:
                logger_debug("  tok.is_matched = True", "match_qspan:", match_qspan)
        else:
            if trace:
                logger_debug(
                    "  unmatched token: tok.is_matched = False",
                    "match_qspan:",
                    match_qspan,
                    "tok.pos in match_qspan:",
                    tok.pos in match_qspan,
                )

        if whole_lines:
            # we only work on matched lines so no need to test further
            # if start_line <= tok.line_num <= end_line.
            if trace:
                logger_debug("  whole_lines")

            is_included = True

        else:
            # Are we in the match_qspan range or a punctuation right before or after
            # that range?

            # start
            if not started and tok.pos == start:
                started = True
                if trace:
                    logger_debug("  start")

                is_included = True

            # middle
            if started and not finished:
                if trace:
                    logger_debug("    middle")

                is_included = True

            if tok.pos == end:
                if trace:
                    logger_debug("  at end")

                finished = True
                started = False
                end_pos = real_pos

            # one punctuation token after a match
            if finished and not started and end_pos and last_pos == end_pos:
                end_pos = 0
                if not tok.is_text:
                    # strip the trailing spaces of the last token
                    if tok.value.strip():
                        if trace:
                            logger_debug("  end yield")

                        is_included = True

        last_pos = real_pos
        if is_included:
            yield tok


def get_full_matched_text(
    match,
    location=None,
    query_string=None,
    idx=None,
    whole_lines=False,
    highlight=True,
    highlight_matched="{}",
    highlight_not_matched="[{}]",
    only_matched=False,
    stopwords=STOPWORDS,
    _usecache=True,
    trace=TRACE_MATCHED_TEXT,
):
    """
    Yield strings corresponding to the full matched query text given a ``match``
    LicenseMatch detected with an `idx` LicenseIndex in a query file at
    ``location`` or a ``query_string``.

    See get_full_qspan_matched_text() for other arguments documentation
    """
    if trace:
        logger_debug("get_full_matched_text:  match:", match)

    return get_full_qspan_matched_text(
        match_qspan=match.qspan,
        match_query_start_line=match.query.start_line,
        match_start_line=match.start_line,
        match_end_line=match.end_line,
        location=location,
        query_string=query_string,
        idx=idx,
        whole_lines=whole_lines,
        highlight=highlight,
        highlight_matched=highlight_matched,
        highlight_not_matched=highlight_not_matched,
        only_matched=only_matched,
        stopwords=stopwords,
        _usecache=_usecache,
        trace=trace,
    )


def get_full_qspan_matched_text(
    match_qspan,
    match_query_start_line,
    match_start_line,
    match_end_line,
    location=None,
    query_string=None,
    idx=None,
    whole_lines=False,
    highlight=True,
    highlight_matched="{}",
    highlight_not_matched="[{}]",
    only_matched=False,
    stopwords=STOPWORDS,
    _usecache=True,
    trace=TRACE_MATCHED_TEXT,
):
    """
    Yield strings corresponding to words of the matched query text given a
    ``match_qspan`` LicenseMatch qspan Span detected with an `idx` LicenseIndex
    in a query file at ``location`` or a ``query_string``.

    - ``match_query_start_line`` is the match query.start_line
    - ``match_start_line`` is the match start_line
    - ``match_end_line`` is the match= end_line

    The returned strings contains the full text including punctuations and
    spaces that are not participating in the match proper including punctuations.

    If ``whole_lines`` is True, the unmatched part at the start of the first
    matched line and the unmatched part at the end of the last matched lines are
    also included in the returned text (unless the line is very long).

    If ``highlight`` is True, each token is formatted for "highlighting" and
    emphasis with the ``highlight_matched`` format string for matched tokens or to
    the ``highlight_not_matched`` for tokens not matched. The default is to
    enclose an unmatched token sequence in [] square brackets. Punctuation is
    not highlighted.

    if ``only_matched`` is True, only matched tokens are returned and
    ``whole_lines`` and ``highlight`` are ignored. Unmatched words are replaced
    by a "dot".

    If ``_usecache`` is True, the tokenized text is cached for efficiency.
    """
    if trace:
        logger_debug("get_full_qspan_matched_text:  match_qspan:", match_qspan)
        logger_debug("get_full_qspan_matched_text:  location:", location)
        logger_debug("get_full_qspan_matched_text:  query_string :", query_string)

    assert location or query_string
    assert idx

    if only_matched:
        # use highlighting to skip the reporting of unmatched entirely
        whole_lines = False
        highlight = True
        highlight_matched = "{}"
        highlight_not_matched = "."
        highlight = True

    # Create and process a stream of Tokens
    if not _usecache:
        # for testing only, reset cache on each call
        tokens = tokenize_matched_text(
            location=location,
            query_string=query_string,
            dictionary=idx.dictionary,
            start_line=match_query_start_line,
            _cache={},
        )
    else:
        tokens = tokenize_matched_text(
            location=location,
            query_string=query_string,
            dictionary=idx.dictionary,
            start_line=match_query_start_line,
        )

    if trace:
        tokens = list(tokens)
        print()
        logger_debug("get_full_qspan_matched_text:  tokens:")
        for t in tokens:
            print("    ", t)
        print()

    tokens = reportable_tokens(
        tokens=tokens,
        match_qspan=match_qspan,
        start_line=match_start_line,
        end_line=match_end_line,
        whole_lines=whole_lines,
    )

    if trace:
        tokens = list(tokens)
        logger_debug("get_full_qspan_matched_text:  reportable_tokens:")
        for t in tokens:
            print(t)
        print()

    # Finally yield strings with eventual highlightings
    for token in tokens:
        val = token.value
        if not highlight:
            yield val
        else:
            if token.is_text and val.lower() not in stopwords:
                if token.is_matched:
                    yield highlight_matched.format(val)
                else:
                    yield highlight_not_matched.format(val)
            else:
                # we do not highlight punctuation and stopwords.
                yield val

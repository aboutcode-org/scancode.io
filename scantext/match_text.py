# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/nexB/scancode.io for support and download.

import attr
from licensedcode import models
from licensedcode import query
from licensedcode.spans import Span
from licensedcode.stopwords import STOPWORDS
from licensedcode.tokenize import index_tokenizer
from licensedcode.tokenize import matched_query_text_tokenizer

SCANCODE_BASE_URL = (
    "https://github.com/nexB/scancode-toolkit/tree/develop/src/licensedcode/data"
)
SPDX_LICENSE_URL = "https://spdx.org/licenses/{}"
SCANCODE_LICENSEDB_URL = "https://scancode-licensedb.aboutcode.org/{}"


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

    # Rules collected from license_matches using above match_ids
    match_rules = attr.ib(default=None)


def get_match_details(mid, match, license_url_template, spdx_license_url):
    """
    Return a mapping of license data built from a LicenseMatch ``match``.
    """
    from licensedcode import cache

    licenses = cache.get_licenses_db()

    # TODO: decide whether the text should be highlighted or not.
    matched_text = match.matched_text(whole_lines=False, highlight=False)

    SCANCODE_LICENSE_TEXT_URL = SCANCODE_BASE_URL + "/{}.LICENSE"
    SCANCODE_LICENSE_DATA_URL = SCANCODE_BASE_URL + "/{}.yml"

    result = {}

    result["mid"] = mid
    # Detection Level Information
    result["score"] = int(match.score())
    result["start_line"] = match.start_line
    result["end_line"] = match.end_line
    result["matched_length"] = match.len()
    result["match_coverage"] = match.coverage()
    result["matcher"] = match.matcher

    # LicenseDB Level Information (Rule that was matched)
    result["license_expression"] = match.rule.license_expression
    result["rule_text_url"] = get_rule_text_url(match.rule)
    result["rule_identifier"] = match.rule.identifier
    result["referenced_filenames"] = match.rule.referenced_filenames
    result["is_license_text"] = match.rule.is_license_text
    result["is_license_notice"] = match.rule.is_license_notice
    result["is_license_reference"] = match.rule.is_license_reference
    result["is_license_tag"] = match.rule.is_license_tag
    result["is_license_intro"] = match.rule.is_license_intro
    result["rule_length"] = match.rule.length
    result["rule_relevance"] = match.rule.relevance
    result["matched_text"] = matched_text

    # License Level Information (Individual licenses that this rule refers to)
    result["licenses"] = detected_licenses = []
    for license_key in match.rule.license_keys():
        detected_license = {}
        detected_licenses.append(detected_license)

        lic = licenses.get(license_key)

        detected_license["key"] = lic.key
        detected_license["name"] = lic.name
        detected_license["short_name"] = lic.short_name
        detected_license["category"] = lic.category
        detected_license["is_exception"] = lic.is_exception
        detected_license["is_unknown"] = lic.is_unknown
        detected_license["owner"] = lic.owner
        detected_license["homepage_url"] = lic.homepage_url
        detected_license["text_url"] = lic.text_urls[0] if lic.text_urls else ""
        detected_license["reference_url"] = license_url_template.format(lic.key)
        detected_license["scancode_text_url"] = SCANCODE_LICENSE_TEXT_URL.format(
            lic.key
        )
        detected_license["scancode_data_url"] = SCANCODE_LICENSE_DATA_URL.format(
            lic.key
        )

        spdx_key = lic.spdx_license_key
        detected_license["spdx_license_key"] = spdx_key

        if spdx_key:
            is_license_ref = spdx_key.lower().startswith("licenseref-")
            if is_license_ref:
                spdx_url = SCANCODE_LICENSE_TEXT_URL.format(lic.key)
            else:
                # TODO: Is this replacing spdx_key???
                spdx_key = lic.spdx_license_key.rstrip("+")
                spdx_url = spdx_license_url.format(spdx_key)
        else:
            spdx_url = ""
        detected_license["spdx_url"] = spdx_url

    return result


def get_licenses(location, license_url_template=SCANCODE_LICENSEDB_URL, **kwargs):
    """
    Return a mapping of license match data from detecting license
    in the file at ``location`` suitable for use in template.

    The mapping can be empty if there are no matches.
    """
    from licensedcode.cache import get_index

    idx = get_index()

    # gets matches from a license file
    matches = idx.match(
        location=location,
        unknown_licenses=True,
        **kwargs,
    )

    if not matches:
        return {}

    query = matches[0].query

    # Assign a numeric id to every match.
    matches_by_id = dict(enumerate(matches))

    del matches

    license_matches = []

    for mid, match in matches_by_id.items():
        license_matches.append(
            get_match_details(
                mid=mid,
                match=match,
                license_url_template=license_url_template,
                spdx_license_url=SPDX_LICENSE_URL,
            )
        )

    license_tokens = get_license_tokens(
        query=query,
        matches_by_id=matches_by_id,
        stopwords=STOPWORDS,
    )

    for tkn in license_tokens:
        if tkn.match_ids:
            rules, seperator = [], ", "
            for rule_id in tkn.match_ids:
                rules.append(license_matches[rule_id]["license_expression"])
            tkn.match_rules = seperator.join(rules)
            del rules
        else:
            tkn.match_rules = "No match found."

    match_colors = get_build_colors(matches_by_id=matches_by_id)

    return {
        "license_matches": license_matches,
        "license_tokens": license_tokens,
        "match_colors": match_colors,
        "license_keys_count": get_license_keys_count(matches=matches_by_id.values()),
        "percentage_of_license_text": get_percentage_of_license_text(
            query=query, matches=matches_by_id.values()
        ),
    }


def get_license_tokens(query, matches_by_id, stopwords=STOPWORDS):
    """
    Return a list of tokens from the list of ``matches`` in ``query``.
    """
    # Token(value="", pos=3, is_text=True, is_matched=True, match_ids=[mid, mid, mid])
    tokens = list(
        tokenize_matched_text(
            location=query.location,
            query_string=query.query_string,
            dictionary=query.idx.dictionary,
            start_line=query.start_line,
        )
    )

    for mid, match in matches_by_id.items():
        tag_matched_tokens(tokens=tokens, match_qspan=match.qspan, mid=mid)

    return tokens


def tokenize_matched_text(location, query_string, dictionary, start_line=1):
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
        for is_text, token_str in matched_query_text_tokenizer(line):
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


def tag_matched_tokens(tokens, match_qspan, mid):
    """
    Tag an iterable of ``tokens`` tagging each token with ``mid`` match id
    if matched meaning the token is in the ``match_qspan``.
    """
    previous_is_matched = False
    for tok in tokens:
        if previous_is_matched and not tok.is_text:
            tok.match_ids.append(mid)
            tok = attr.evolve(tok, is_matched=True)
            previous_is_matched = False
        elif tok.pos != -1 and tok.is_known and tok.pos in match_qspan:
            tok.match_ids.append(mid)
            tok = attr.evolve(tok, is_matched=True)
            previous_is_matched = True


def get_build_colors(matches_by_id):
    """
    Return a mapping of mid to css color code.

    .matched1 {background-color: rgba(30, 220, 90, 0.3);}
    .matched2 {background-color: rgba(30, 90, 220, 0.3);}
    .matched3 {background-color: rgba(220, 90, 30, 0.3);}
    """
    return [
        f""".matched{mid} {{
        background-color: rgba(
        {(244 * (mid+1)) % 255}, {(234 * (mid+1)) % 255}, {(130 * (mid+1)) % 255}, 0.3);
        border-bottom: 3px solid rgba(
        {(244 * (mid+1)) % 255}, {(234 * (mid+1)) % 255}, {(130 * (mid+1)) % 255}, 0.7);
        }}"""
        for mid in matches_by_id
    ]


def get_percentage_of_license_text(query, matches):
    """
    Return percentage of license text matched in ``query`` Query by
    a list of ``matches`` percentage is a float between 0 and 100.
    """

    # TODO: percentage of license text should be done by scancode-toolkit.
    if not matches:
        return 0

    qspans = (match.qspan for match in matches)

    matched_tokens_length = len(Span().union(*qspans))
    query_tokens_length = query.tokens_length(with_unknown=True)
    return round((matched_tokens_length / query_tokens_length) * 100, 2)


def get_rule_text_url(rule, base_url=SCANCODE_BASE_URL):
    """
    Return a URL to the text file of a ``rule`` Rule.
    Return None if there is no URL for the ``rule``.
    """

    if isinstance(rule, (models.SpdxRule, models.UnknownRule)):
        return

    if rule.is_from_license:
        return f"{base_url}/licenses/{rule.identifier}"

    else:
        return f"{base_url}/rules/{rule.identifier}"


def get_license_keys_count(matches):
    """
    Return the number of unique license keys found in a list of license matches.
    """
    keys = set()
    for match in matches:
        keys.update(match.rule.license_keys())

    return len(keys)

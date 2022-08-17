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

import sys
import tempfile

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render

import attr
from licensedcode.match import tokenize_matched_text
from licensedcode.stopwords import STOPWORDS

from scantext.forms import LicenseScanForm

TRACE_HIGHLIGHTED_TEXT = True
SCANCODE_REPO_URL = "https://github.com/nexB/scancode-toolkit"
SCANCODE_BASE_URL = SCANCODE_REPO_URL + "/tree/develop/src/licensedcode/data/licenses"
SCANCODE_LICENSE_TEXT_URL = SCANCODE_BASE_URL + "/{}.LICENSE"
SCANCODE_LICENSE_DATA_URL = SCANCODE_BASE_URL + "/{}.yml"
SPDX_LICENSE_URL = "https://spdx.org/licenses/{}"
DEJACODE_LICENSE_URL = "https://enterprise.dejacode.com/urn/urn:dje:license:{}"
SCANCODE_LICENSEDB_URL = "https://scancode-licensedb.aboutcode.org/{}"


def license_scanview(request):
    if request.method != "POST":
        return render(
            request, "scantext/license_scan_form.html", {"form": LicenseScanForm()}
        )

    form = LicenseScanForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(
            request, "scantext/license_scan_form.html", {"form": LicenseScanForm()}
        )

    input_text = form.cleaned_data["input_text"]
    input_file = request.FILES.get("input_file", False)

    if input_text and input_file:
        message = "Provide text or a text file but not both."
        messages.warning(request, message)
        return render(
            request,
            "scantext/license_scan_form.html",
            {
                "form": LicenseScanForm(),
            },
        )

    if not input_text and not input_file:
        message = "Provide text or a text file to scan."
        messages.warning(request, message)
        return render(
            request,
            "scantext/license_scan_form.html",
            {
                "form": LicenseScanForm(),
            },
        )

    # The flush in tempfile is required to ensure that the content is
    # written to the disk before it's read by get_licenses function
    if input_text:
        with tempfile.NamedTemporaryFile(mode="w") as temp_file:
            temp_file.write(input_text)
            temp_file.flush()
            expressions = get_licenses(location=temp_file.name)
    elif input_file:
        try:
            with tempfile.NamedTemporaryFile(mode="w") as temp_file:
                input_text = str(input_file.read(), "UTF-8")
                temp_file.write(input_text)
                temp_file.flush()
                expressions = get_licenses(location=temp_file.name)
        except UnicodeDecodeError:
            message = "Please upload a valid text file."
            messages.warning(request, message)
            return render(
                request,
                "scantext/license_scan_form.html",
                {
                    "form": LicenseScanForm(),
                },
            )

    if not expressions["licenses"] and not expressions["license_expressions"]:
        message = "Couldn't detect any license from the provided input."
        messages.info(request, message)
        return render(
            request,
            "scantext/license_summary.html",
            {
                "text": input_text,
                "detected_licenses": expressions,
            },
        )
    # if TRACE_HIGHLIGHTED_TEXT:
    #     from pprint import pprint
    #     pprint(expressions, indent=4)

    return render(
        request,
        "scantext/license_summary.html",
        {
            "text": input_text,
            "detected_licenses": expressions,
        },
    )


def get_licenses(
    location,
    license_url_template=SCANCODE_LICENSEDB_URL,
    deadline=sys.maxsize,
    **kwargs,
):
    """
    Return a mapping or detected_licenses for licenses detected in the file at
    `location`
    This mapping contains two keys:
     - 'licenses' with a value that is list of mappings of license information.
     - 'license_expressions' with a value that is list of license expression
       strings.
    `min_score` is a minimum score threshold from 0 to 100. The default is 0,
    meaning that all license matches are returned. If specified, matches with a
    score lower than `minimum_score` are not returned.
    By Default ``unknown_licenses`` is set to True to detect unknown licenses.
    """
    from licensedcode.cache import get_index
    from licensedcode.spans import Span

    idx = get_index()

    detected_licenses = []
    detected_expressions = []
    detected_expressions_with_scores = []

    # gets matches from a license file
    matches = idx.match(
        location=location,
        min_score=0,
        deadline=deadline,
        unknown_licenses=True,
        **kwargs,
    )

    qspans = []
    match = None
    complete_text_in_array = []
    # run through a list of matches
    for match in matches:
        qspans.append(match.qspan)

        detected_expressions.append(match.rule.license_expression)
        detected_expressions_with_scores.append([match.rule.license_expression, match.score()])
        detected_licenses.extend(
            _licenses_data_from_match(
                match=match,
                license_url_template=license_url_template,
            )
        )

        complete_text_in_array.append(
            get_highlighted_lines(
                match=match,
                stopwords=STOPWORDS,
                trace=TRACE_HIGHLIGHTED_TEXT,
            )
        )

    percentage_of_license_text = 0
    if match:
        # we need at least one match to compute a license_coverage
        matched_tokens_length = len(Span().union(*qspans))
        query_tokens_length = match.query.tokens_length(with_unknown=True)
        percentage_of_license_text = round(
            (matched_tokens_length / query_tokens_length) * 100, 2
        )

    return dict(
        [
            ("licenses", detected_licenses),
            ("license_expressions", detected_expressions),
            ("license_expressions_scores", detected_expressions_with_scores),
            ("percentage_of_license_text", percentage_of_license_text),
            ("complete_text_in_array", complete_text_in_array),
        ]
    )


def _licenses_data_from_match(
    match,
    license_url_template=SCANCODE_LICENSEDB_URL,
):
    """
    Return a list of "licenses" scan data built from a license match.
    Used directly only internally for testing.
    """
    from licensedcode import cache

    licenses = cache.get_licenses_db()

    # Returned matched_text will also include the text detected
    matched_text = match.matched_text(
        whole_lines=False,
        highlight=True,
        highlight_matched="<matched>{}</matched>",
        highlight_not_matched="<notmatched>{}</notmatched>",
    )

    detected_licenses = []
    for license_key in match.rule.license_keys():
        lic = licenses.get(license_key)
        result = {}
        detected_licenses.append(result)
        result["key"] = lic.key
        result["score"] = match.score()
        result["name"] = lic.name
        result["short_name"] = lic.short_name
        result["category"] = lic.category
        result["is_exception"] = lic.is_exception
        result["is_unknown"] = lic.is_unknown
        result["owner"] = lic.owner
        result["homepage_url"] = lic.homepage_url
        result["text_url"] = lic.text_urls[0] if lic.text_urls else ""
        result["reference_url"] = license_url_template.format(lic.key)
        result["scancode_text_url"] = SCANCODE_LICENSE_TEXT_URL.format(lic.key)
        result["scancode_data_url"] = SCANCODE_LICENSE_DATA_URL.format(lic.key)
        result["rule"] = match.rule.license_expression
        result["rules"] = match.rule.license_keys()

        spdx_key = lic.spdx_license_key
        result["spdx_license_key"] = spdx_key

        if spdx_key:
            is_license_ref = spdx_key.lower().startswith("licenseref-")
            if is_license_ref:
                spdx_url = SCANCODE_LICENSE_TEXT_URL.format(lic.key)
            else:
                spdx_key = lic.spdx_license_key.rstrip("+")
                spdx_url = SPDX_LICENSE_URL.format(spdx_key)
        else:
            spdx_url = ""
        result["spdx_url"] = spdx_url
        result["start_line"] = match.start_line
        result["end_line"] = match.end_line
        result["matched_text"] = matched_text
        matched_rule = result["matched_rule"] = {}
        matched_rule["identifier"] = match.rule.identifier
        matched_rule["license_expression"] = match.rule.license_expression
        matched_rule["licenses"] = match.rule.license_keys()
        matched_rule["referenced_filenames"] = match.rule.referenced_filenames
        matched_rule["is_license_text"] = match.rule.is_license_text
        matched_rule["is_license_notice"] = match.rule.is_license_notice
        matched_rule["is_license_reference"] = match.rule.is_license_reference
        matched_rule["is_license_tag"] = match.rule.is_license_tag
        matched_rule["is_license_intro"] = match.rule.is_license_intro
        matched_rule["has_unknown"] = match.rule.has_unknown
        matched_rule["matcher"] = match.matcher
        matched_rule["rule_length"] = match.rule.length
        matched_rule["matched_length"] = match.len()
        matched_rule["match_coverage"] = match.coverage()
        matched_rule["rule_relevance"] = match.rule.relevance

    return detected_licenses


def logger_debug(*args):
    pass


def get_highlighted_lines(
    match,
    stopwords=STOPWORDS,
    trace=TRACE_HIGHLIGHTED_TEXT,
):
    """
    Yield highlighted text lines (with line returns) for the whole
    of the matched and unmatched text of a ``query``.
    """
    query = match.query
    tokens = tokenize_matched_text(
        location=query.location,
        query_string=query.query_string,
        dictionary=query.idx.dictionary,
        start_line=match.query.start_line,
        _cache={},
    )
    tokens = tag_matched_tokens(tokens=tokens, match_qspan=match.qspan)

    header = """<style>
    .license-match {
        font-size: 18px;
        white-space: pre-wrap;
    }

    .matched {
        background-color: rgba(30, 220, 90, 0.3);
    }
    </style>
    <div class="license-match">
    """
    footer = """</div>"""

    body = ""
    highlight_matched = '<span class="matched">{}</span>'
    highlight_not_matched = '<span class="not-matched">{}</span>'
    for token in tokens:
        val = token.value
        if token.is_text and val.lower() not in stopwords:
            if token.is_matched:
                body += highlight_matched.format(val)
            else:
                body += highlight_not_matched.format(val)
        else:
            # we do not highlight punctuation and stopwords.
            body += highlight_not_matched.format(val)

    return header + body + footer


def tag_matched_tokens(tokens, match_qspan):
    """
    Yield Tokens from a ``tokens`` iterable of Token objects.
    Known matched tokens are tagged as "is_matched=True" if they are matched.
    """
    for tok in tokens:
        # tagged known matched tokens (useful for highlighting)
        if tok.pos != -1 and tok.is_known and tok.pos in match_qspan:
            tok = attr.evolve(tok, is_matched=True)
        yield tok

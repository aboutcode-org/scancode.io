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
from pprint import pprint

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render

import attr
from licensedcode import query
from licensedcode.match import tokenize_matched_text
from licensedcode.spans import Span
from licensedcode.stopwords import STOPWORDS
from licensedcode.tokenize import index_tokenizer
from licensedcode.tokenize import matched_query_text_tokenizer

from scantext.forms import LicenseScanForm

TRACE_HIGHLIGHTED_TEXT = True
SCANCODE_REPO_URL = "https://github.com/nexB/scancode-toolkit"
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

    if not expressions:
        message = "Couldn't detect any license from the provided input."
        messages.warning(request, message)
        return render(
            request,
            "scantext/license_scan_form.html",
            {
                "form": LicenseScanForm(),
            },
        )

    # pprint(expressions)

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
    from licensedcode.cache import get_index
    from licensedcode.spans import Span

    idx = get_index()

    detected_licenses = []
    detected_expressions_and_scores = []

    # gets matches from a license file
    matches = idx.match(
        location=location,
        min_score=0,
        deadline=deadline,
        unknown_licenses=True,
        **kwargs,
    )

    if not matches:
        return False

    qspans = []
    match = None
    complete_text = None

    for match in matches:
        qspans.append(match.qspan)
        detected_expressions_and_scores.append(
            [match.rule.license_expression, match.score()]
        )
        detected_licenses.append(
            get_mapping(
                match=match,
                include_text=True,
                license_url_template=license_url_template,
                spdx_license_url=SPDX_LICENSE_URL,
            )
        )

    complete_text = get_highlighted_lines(
        matches=matches,
        stopwords=STOPWORDS,
        trace=TRACE_HIGHLIGHTED_TEXT,
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
            ("complete_text", complete_text),
            ("license_expressions_and_scores", detected_expressions_and_scores),
            ("percentage_of_license_text", percentage_of_license_text),
        ]
    )


def logger_debug(*args):
    pass


def get_highlighted_lines(
    matches,
    stopwords=STOPWORDS,
    trace=TRACE_HIGHLIGHTED_TEXT,
):
    tokens = []

    query = matches[0].query
    tokens = tokenize_matched_text(
        location=query.location,
        query_string=query.query_string,
        dictionary=query.idx.dictionary,
        start_line=query.start_line,
        _cache={},
    )

    class_position = 1
    for match in matches:
        tokens = tag_matched_tokens(
            tokens=tokens, match_qspan=match.qspan, class_position=class_position
        )
        class_position += 1

    body = []
    for token in tokens:
        val = token.value
        if token.is_text and val.lower() not in stopwords:
            if token.is_matched:
                body.append([token.value, token.is_matched % 3])
            else:
                body.append([token.value, -1])
        else:
            # we do not highlight punctuation and stopwords.
            body.append([token.value, -1])

    return body


def tag_matched_tokens(tokens, match_qspan, class_position):

    for tok in tokens:
        # tagged known matched tokens (useful for highlighting)
        if tok.pos != -1 and tok.is_known and tok.pos in match_qspan:
            tok = attr.evolve(tok, is_matched=class_position)
        yield tok


def get_mapping(
    match,
    license_url_template,
    spdx_license_url,
    include_text=False,
    license_text_diagnostics=False,
):
    """
    Return a list of "matches" scan data built from a license match.
    """
    from licensedcode import cache

    licenses = cache.get_licenses_db()

    matched_text = None
    if include_text:
        if license_text_diagnostics:
            matched_text = match.matched_text(whole_lines=False, highlight=True)
        else:
            matched_text = match.matched_text(whole_lines=False, highlight=False)

    SCANCODE_BASE_URL = (
        "https://github.com/nexB/scancode-toolkit/tree/develop/src/licensedcode/data/"
    )
    SCANCODE_LICENSE_TEXT_URL = SCANCODE_BASE_URL + "/{}.LICENSE"
    SCANCODE_LICENSE_DATA_URL = SCANCODE_BASE_URL + "/{}.yml"

    result = {}

    # Detection Level Information
    result["score"] = match.score()
    result["start_line"] = match.start_line
    result["end_line"] = match.end_line
    result["matched_length"] = match.len()
    result["match_coverage"] = match.coverage()
    result["matcher"] = match.matcher

    # LicenseDB Level Information (Rule that was matched)
    result["license_expression"] = match.rule.license_expression
    result["rule_identifier"] = match.rule.identifier  # .RULE OR .LICENSE
    result["referenced_filenames"] = match.rule.referenced_filenames
    result["is_license_text"] = match.rule.is_license_text
    result["is_license_notice"] = match.rule.is_license_notice
    result["is_license_reference"] = match.rule.is_license_reference
    result["is_license_tag"] = match.rule.is_license_tag
    result["is_license_intro"] = match.rule.is_license_intro
    result["rule_length"] = match.rule.length
    result["rule_relevance"] = match.rule.relevance
    if include_text:
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

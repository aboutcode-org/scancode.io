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
from licensedcode import models
from licensedcode import query
from licensedcode.spans import Span
from licensedcode.stopwords import STOPWORDS
from licensedcode.tokenize import index_tokenizer
from licensedcode.tokenize import matched_query_text_tokenizer

from scantext.forms import LicenseScanForm
from scantext.match_text import tokenize_matched_text

TRACE_HIGHLIGHTED_TEXT = True

SCANCODE_BASE_URL = (
    "https://github.com/nexB/scancode-toolkit/tree/develop/src/licensedcode/data"
)
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
    # TODO: check this to handle input files
    # https://github.com/nexB/commoncode/blob/9131627677d3ef171ddc472991a5c4d4a3431ee3/src/commoncode/fileutils.py#L99

    if input_text:
        with tempfile.NamedTemporaryFile(mode="w") as temp_file:
            temp_file.write(input_text)
            temp_file.flush()
            expressions = get_licenses(location=temp_file.name)
    elif input_file:
        try:
            # rework on how to handle temporary files.
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
        message = "Could not detect any license."
        messages.warning(request, message)
        return render(
            request,
            "scantext/license_scan_form.html",
            {
                "form": LicenseScanForm(),
            },
        )

    # import json
    # print(json.dumps(expressions, indent=2))

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
    **kwargs,
):
    """
    Return a mapping of license match data from detecting license
    in the file at ``location`` suitable for use in template.

    The mapping can be empty if there are no matches.
    """
    from licensedcode.cache import get_index
    from licensedcode.spans import Span

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
        trace=TRACE_HIGHLIGHTED_TEXT,
    )

    match_colors = build_colors(matches_by_id=matches_by_id)
    # print(match_colors)

    return {
        "license_matches": license_matches,
        "license_tokens": license_tokens,
        "match_colors": match_colors,
        "license_keys_count": get_license_keys_count(matches=matches_by_id.values()),
        "percentage_of_license_text": get_percentage_of_license_text(
            query=query, matches=matches_by_id.values()
        ),
    }


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


def get_license_tokens(
    query,
    matches_by_id,
    stopwords=STOPWORDS,
    trace=TRACE_HIGHLIGHTED_TEXT,
):
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


def build_colors(matches_by_id):
    """
    Return a mapping of mid to css color code.

    .matched1 {background-color: rgba(30, 220, 90, 0.3);}
    .matched2 {background-color: rgba(30, 90, 220, 0.3);}
    .matched3 {background-color: rgba(220, 90, 30, 0.3);}
    """
    return [
        f""".matched{mid} {{background-color: rgba(
        {(244 * (mid+1)) % 255}, {(234 * (mid+1)) % 255}, {(130 * (mid+1)) % 255},
        0.3);}}"""
        for mid in matches_by_id
    ]


def get_match_details(
    mid,
    match,
    license_url_template,
    spdx_license_url,
):
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
    result["score"] = match.score()
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


def get_license_keys_count(matches):
    """
    Return the number of unique license keys found in a list of license matches.
    """
    keys = set()
    for match in matches:
        keys.update(match.rule.license_keys())

    return len(keys)


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

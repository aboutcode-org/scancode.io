#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

import io
from pathlib import Path
from unittest import mock

from django.test import TestCase

from scanpipe.models import CodebaseResource
from scanpipe.models import DiscoveredDependency
from scanpipe.models import DiscoveredPackage
from scanpipe.models import Project
from scanpipe.pipes import purldb
from scanpipe.tests import dependency_data2
from scanpipe.tests import dependency_data3
from scanpipe.tests import package_data1


class ScanPipePurlDBTest(TestCase):
    data_location = Path(__file__).parent.parent / "data"

    def setUp(self):
        self.project1 = Project.objects.create(name="Analysis")

    def test_scanpipe_pipes_purldb_get_unique_resolved_purls(self):
        DiscoveredPackage.create_from_data(self.project1, package_data1)
        CodebaseResource.objects.create(
            project=self.project1, path="data.tar.gz-extract/Gemfile.lock"
        )
        DiscoveredDependency.create_from_data(self.project1, dependency_data2)

        expected = {"pkg:gem/appraisal@2.2.0"}
        result = purldb.get_unique_resolved_purls(self.project1)

        self.assertEqual(expected, result)

    def test_scanpipe_pipes_purldb_get_unique_unresolved_purls(self):
        DiscoveredPackage.create_from_data(self.project1, package_data1)
        CodebaseResource.objects.create(
            project=self.project1,
            path="daglib-0.3.2.tar.gz-extract/daglib-0.3.2/PKG-INFO",
        )
        DiscoveredDependency.create_from_data(self.project1, dependency_data3)

        expected = {("pkg:pypi/dask", "vers:pypi/>=1.0")}
        result = purldb.get_unique_unresolved_purls(self.project1)

        self.assertEqual(expected, result)

    @mock.patch("scanpipe.pipes.purldb.request_post")
    @mock.patch("scanpipe.pipes.purldb.is_available")
    def test_scanpipe_pipes_purldb_feed_purldb(
        self, mock_is_available, mock_request_post
    ):
        mock_is_available.return_value = True

        packages = [("pkg:pypi/dask", "vers:pypi/>=1.0")]

        def mock_request_post_return(url, data, headers, timeout):
            return {
                "queued_packages_count": 1,
                "queued_packages": [],
                "unqueued_packages_count": 1,
                "unqueued_packages": [],
                "unsupported_packages_count": 0,
                "unsupported_packages": [],
            }

        mock_request_post.side_effect = mock_request_post_return

        buffer = io.StringIO()
        purldb.feed_purldb(
            packages=packages,
            chunk_size=10,
            logger=buffer.write,
        )

        expected_log = buffer.getvalue()
        self.assertIn(
            "Successfully queued 1 PURLs for indexing in PurlDB", expected_log
        )
        self.assertIn(
            "1 PURLs were already present in PurlDB index queue", expected_log
        )

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

from django.db import transaction

from rest_framework import serializers

from scanner.models import EmailSubscription
from scanner.models import Scan
from scanner.models import WebhookSubscription
from scanner.tasks import download_and_scan
from scanpipe.api import ExcludeFromListViewMixin


class ScanSerializer(
    ExcludeFromListViewMixin,
    serializers.HyperlinkedModelSerializer,
):
    data_url = serializers.HyperlinkedIdentityField(view_name="scan-data")
    summary_url = serializers.HyperlinkedIdentityField(view_name="scan-summary")
    email = serializers.EmailField(write_only=True, required=False)
    created_by = serializers.UUIDField(write_only=True, allow_null=True, required=False)
    webhook_url = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Scan
        fields = (
            "url",
            "uuid",
            "uri",
            "filename",
            "sha1",
            "md5",
            "size",
            "created_date",
            "scancode_version",
            "task_id",
            "task_start_date",
            "task_end_date",
            "task_exitcode",
            "task_output",
            "status",
            "execution_time",
            "created_by",
            "data_url",
            "summary_url",
            "email",
            "webhook_url",
        )
        read_only_fields = (
            "scancode_version",
            "created_date",
            "task_start_date",
            "task_end_date",
            "task_exitcode",
            "task_output",
            "status",
            "execution_time",
            "filename",
            "sha1",
            "md5",
            "size",
        )
        exclude_from_list_view = ["task_output"]

    def validate_uri(self, value):
        """
        Remove leading and trailing whitespaces.
        """
        return value.strip()

    def create(self, validated_data):
        """
        Trigger the task on Scan creation.
        Also create Subscriptions if requested.
        Note that Subscriptions have to be created before the `download_and_scan`
        task is triggered.
        """
        webhook_url = validated_data.pop("webhook_url", None)
        created_by = validated_data.get("created_by", None)
        email = validated_data.pop("email", None)

        scan = super().create(validated_data)

        if webhook_url and created_by:
            WebhookSubscription.objects.create(
                scan=scan,
                user_uuid=created_by,
                target_url=webhook_url,
            )

        if email:
            EmailSubscription.objects.create(scan=scan, email=email)

        # Ensure the task is executed after the transaction is successfully committed.
        transaction.on_commit(
            lambda: download_and_scan.apply_async(args=[scan.pk], queue="default")
        )

        return scan

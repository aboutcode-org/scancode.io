#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#


class ExcludeFromListViewMixin:
    """
    Exclude the `exclude_from_list_view` fields from the list view,
    but still available in the detail view.
    """

    def get_fields(self):
        fields = super().get_fields()

        exclude_from_list_view = getattr(self.Meta, "exclude_from_list_view", None)
        if exclude_from_list_view:
            view = self.context.get("view", None)
            if view and not view.detail:
                for exclude_field in exclude_from_list_view:
                    fields.pop(exclude_field, None)

        return fields

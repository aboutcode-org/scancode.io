# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
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
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

import subprocess

from scanpipe.pipes import run_command_safely


def get_images_from_kubectl(namespace=None, context=None):
    """
    Extract container images from a running Kubernetes cluster using kubectl.

    Args:
        namespace: Specific namespace to query (None for all namespaces)
        context: Kubernetes context to use (None for current context)

    Returns:
        list: List of unique image references

    """
    cmd = ["kubectl", "get", "pods"]

    if namespace:
        cmd.extend(["-n", namespace])
    else:
        cmd.append("--all-namespaces")

    if context:
        cmd.extend(["--context", context])

    # Get all images including init containers
    cmd.extend(
        ["-o", "jsonpath={.items[*].spec['initContainers','containers'][*].image}"]
    )

    try:
        result = run_command_safely(cmd)
    except subprocess.SubprocessError as error:
        raise RuntimeError(f"Failed to execute kubectl command: {error}")
    except FileNotFoundError:
        raise FileNotFoundError(
            "kubectl not found. Please ensure kubectl is installed and in your PATH."
        )

    # Parse the space-separated images
    images = result.strip().split()

    # Remove duplicates while preserving order
    unique_images = list(dict.fromkeys(image for image in images if image))

    return unique_images

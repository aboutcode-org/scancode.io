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

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

SCANCODE_IMAGE = "ghcr.io/aboutcode-org/scancode.io:latest"
DB_IMAGE = "postgres:13"
DB_USER = "scancode"
DB_PASS = os.getenv("SCANCODE_DB_PASS", "scancode")
DB_NAME = "scancode"
D2D_DIR = Path("d2d")


def get_free_port():
    """Find a free host port for Postgres."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def safe_run(cmd, capture_output=False, silent=False):
    """Run subprocess command safely with full binary path."""
    if not silent:
        print(f"Running: {' '.join(cmd)}")

    cmd[0] = shutil.which(cmd[0]) or cmd[0]

    try:
        return subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=capture_output,
        )
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd)}")
        print(e.stderr or e.stdout or str(e))
        sys.exit(1)


def wait_for_postgres(container_name, timeout=60):
    """Wait until the Postgres container is ready."""
    print("Waiting for Postgres to be ready...")
    for _ in range(timeout):
        result = subprocess.run(
            ["docker", "exec", container_name, "pg_isready", "-U", DB_USER],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            print("Postgres is ready.")
            return
        time.sleep(1)
    raise RuntimeError("Postgres did not become ready in time.")


def prepare_d2d_dir(from_file, to_file):
    """Ensure d2d folder exists and contains required files."""
    D2D_DIR.mkdir(exist_ok=True)

    from_dest = D2D_DIR / Path(from_file).name
    to_dest = D2D_DIR / Path(to_file).name

    shutil.copy(from_file, from_dest)
    shutil.copy(to_file, to_dest)
    print(f"Files copied to: {D2D_DIR.resolve()}")

    return from_dest.name, to_dest.name


def main():
    parser = argparse.ArgumentParser(
        description="Run ScanCode.io pipelines in Docker with isolated Postgres DB "
        "(using ./d2d directory)."
    )
    parser.add_argument(
        "--input-file",
        action="append",
        required=True,
        help="Format: path/to/file:tag (tag must be 'from' or 'to')",
    )
    parser.add_argument(
        "--option",
        action="append",
        help="Options for the pipeline, e.g. Python, Java, Javascript",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file to write the ScanCode results (JSON format)",
    )
    args = parser.parse_args()

    file_map = {}
    for f in args.input_file:
        try:
            path, tag = f.split(":")
            file_map[tag] = os.path.abspath(path)
        except ValueError:
            print(f"Invalid --input-file format: {f}. Use path:tag", file=sys.stderr)
            sys.exit(1)

    if "from" not in file_map or "to" not in file_map:
        print("Both :from and :to input files are required.", file=sys.stderr)
        sys.exit(1)

    from_name, to_name = prepare_d2d_dir(file_map["from"], file_map["to"])

    db_container_name = f"scancode_db_{uuid.uuid4().hex[:6]}"
    db_port = get_free_port()
    print(f"Using Postgres host port: {db_port}")

    project_name = f"scanpipe_{uuid.uuid4().hex[:8]}"

    docker_bin = shutil.which("docker") or "docker"

    try:
        safe_run(
            [
                docker_bin,
                "run",
                "-d",
                "--name",
                db_container_name,
                "-e",
                f"POSTGRES_USER={DB_USER}",
                "-e",
                f"POSTGRES_PASSWORD={DB_PASS}",
                "-e",
                f"POSTGRES_DB={DB_NAME}",
                "-p",
                f"{db_port}:5432",
                DB_IMAGE,
            ],
            silent=True,
        )

        wait_for_postgres(db_container_name)
        db_url = (
            f"postgresql://{DB_USER}:{DB_PASS}@host.docker.internal:{db_port}/{DB_NAME}"
        )

        pipeline_name = "map_deploy_to_develop"

        if args.option:
            pipeline_name = f"{pipeline_name}:"

        for option in args.option or []:
            pipeline_name += f"{option},"

        pipeline_cmd = (
            f"scanpipe create-project {project_name} "
            f"--input-file /code/{from_name}:from "
            f"--input-file /code/{to_name}:to "
            f"--pipeline {pipeline_name} && "
            f"scanpipe execute --project {project_name}"
        )

        docker_cmd = [
            docker_bin,
            "run",
            "--rm",
            "-v",
            f"{D2D_DIR.resolve()}:/code",
            "-e",
            f"DATABASE_URL={db_url}",
            "--network",
            "host",
            SCANCODE_IMAGE,
            "sh",
            "-c",
            pipeline_cmd,
        ]

        print("Running ScanCode pipeline:")
        result = safe_run(docker_cmd, capture_output=False)

        pipeline_cmd = f"scanpipe output --project {project_name} --format json --print"

        docker_cmd = [
            docker_bin,
            "run",
            "--rm",
            "-v",
            f"{D2D_DIR.resolve()}:/code",
            "-e",
            f"DATABASE_URL={db_url}",
            "--network",
            "host",
            SCANCODE_IMAGE,
            "sh",
            "-c",
            pipeline_cmd,
        ]

        result = safe_run(docker_cmd, capture_output=True)

        with open(args.output, "w") as f:
            f.write(result.stdout)

    finally:
        subprocess.run(["docker", "rm", "-f", db_container_name], check=False)


if __name__ == "__main__":
    main()

import logging

import packagedcode
from commoncode.resource import VirtualCodebase
from packageurl import PackageURL
from scancode import ScancodeError

from scanpipe import pipes
from scanpipe.models import CodebaseResource

from LicenseClassifier.classifier import LicenseClassifier

logger = logging.getLogger("scanpipe.pipes")

def save_scan_file_results(codebase_resource, scan_results, scan_errors):
    """
    Save the resource scan file results in the database.
    Create project errors if any occurred during the scan.
    """
    if scan_errors:
        codebase_resource.add_errors(scan_errors)
        codebase_resource.status = "scanned-with-error"
    else:
        codebase_resource.status = "scanned"

    codebase_resource.set_scan_results(scan_results, save=True)

def _log_progress(scan_func, resource, resource_count, index):
    progress = f"{index / resource_count * 100:.1f}% ({index}/{resource_count})"
    logger.info(f"{scan_func.__name__} {progress} pk={resource.pk}")


def run_glc(location, output_file, search_subdir, raise_on_error=False):
    """
    Scan `location` content and write results into `output_file`.
    """

    l = LicenseClassifier()
    l.catalogueDir(location, search_subdir, output_file)
    return


def get_virtual_codebase(project, input_location):
    """
    Return a ScanCode virtual codebase built from the JSON scan file at
    `input_location`.
    """
    temp_path = project.tmp_path / "scancode-temp-resource-cache"
    temp_path.mkdir(parents=True, exist_ok=True)
    print(input_location)
    return VirtualCodebase(input_location, temp_dir=str(temp_path), max_in_memory=0)


def create_codebase_resources(project, scanned_codebase):
    """
    Save the resources of a ScanCode `scanned_codebase` scancode.resource.Codebase
    object to the DB as CodebaseResource of the `project`.
    This function can be used to expends an existing `project` Codebase with new
    CodebaseResource objects as the existing objects (based on the `path`) will be
    skipped.
    """
    for scanned_resource in scanned_codebase.walk(skip_root=True):
        resource_data = {}

        for field in CodebaseResource._meta.fields:
            # Do not include the path as provided by the scanned_resource since it
            # includes the "root". The `get_path` method is used instead.
            if field.name == "path":
                continue
            value = getattr(scanned_resource, field.name, None)
            if value is not None:
                resource_data[field.name] = value

        resource_type = "FILE" if scanned_resource.is_file else "DIRECTORY"
        resource_data["type"] = CodebaseResource.Type[resource_type]
        resource_path = scanned_resource.get_path(strip_root=True)

        CodebaseResource.objects.get_or_create(
            project=project,
            path=resource_path,
            defaults=resource_data,
        )

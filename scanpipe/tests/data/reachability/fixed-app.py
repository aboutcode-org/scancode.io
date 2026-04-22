import os


class ReportGenerator:
    """A dummy class to test AST class method parsing."""

    def __init__(self, base_dir):
        self.base_dir = base_dir


def serve_report(request_payload):
    """Top-level function handling a request."""
    generator = ReportGenerator("/var/reports")
    requested_file = request_payload.get("file")

    # Helper function nested inside serve_report
    def build_file_path(filename):
        # FIXED: Validate that the resolved path stays within the base_dir
        base = os.path.abspath(generator.base_dir)
        target = os.path.abspath(os.path.join(base, filename))
        if not target.startswith(base):
            raise ValueError("Path Traversal Detected")
        return target

    if not requested_file:
        return "Error: No file specified"

    try:
        target_path = build_file_path(requested_file)
    except ValueError:
        return "Error: Invalid path"

    if os.path.exists(target_path):
        return f"Serving content of {target_path}"

    return "Error: File not found"


def unrelated_top_level_function():
    """An extra function to test AST node boundaries."""
    return "I am just here to add AST complexity."

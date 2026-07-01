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
        # VULNERABLE: Direct concatenation allows Path Traversal
        # An attacker passing "../../etc/passwd" could read system files.
        return os.path.join(generator.base_dir, filename)

    if not requested_file:
        return "Error: No file specified"

    target_path = build_file_path(requested_file)

    if os.path.exists(target_path):
        return f"Serving content of {target_path}"

    return "Error: File not found"


def unrelated_top_level_function():
    """Test AST node boundaries."""
    return "I am just here to add AST complexity."

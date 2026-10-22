import os

from flask import Flask
from flask import request

app = Flask(__name__)

debug = False


class ReportGenerator:
    """A dummy class to test AST class method parsing."""

    def __init__(self, base_dir):
        self.base_dir = base_dir


@app.route("/report")
def handle_request():
    """HTTP entry point so atom tags a framework-route source."""
    generator = ReportGenerator("/var/reports")
    requested_file = request.args.get("file")

    # Helper function nested inside the route handler
    def build_file_path(filename):
        # VULNERABLE: Direct concatenation allows Path Traversal
        return os.path.join(generator.base_dir, filename)

    if not requested_file:
        return "Error: No file specified"

    target_path = build_file_path(requested_file)

    with open(target_path) as f:
        return f.read()


def unrelated_top_level_function():
    """Test AST node boundaries."""
    return "I am just here to add AST complexity."

import json
from .core import CodeGenerator

class APITestGenerator(CodeGenerator):
    """Generates API test code from structured request data."""
    def generate(self, data: list) -> str:
        """Generates Python test code for API requests."""
        code_lines = [
            "import pytest",
            "# Assuming APIClient is available as a pytest fixture or can be imported.",
            "# For example: from your_project.api_client import APIClient",
            "",
            "# This is auto-generated test code. Please review and enhance as needed.",
            "",
        ]

        for i, req in enumerate(data):
            method = req.get("method", "GET").lower()
            url = req.get("url", "")
            post_data = req.get("postData")
            response_status = req.get("response_status")

            test_name = f"test_api_request_{method}_{i}"
            code_lines.append(f"def {test_name}(api_client): # api_client should be a fixture or passed in")
            code_lines.append(f"    # Request: {method.upper()} {url}")

            request_args = []
            if post_data:
                try:
                    # Try to parse as JSON
                    json_data = json.loads(post_data)
                    request_args.append(f"json={json.dumps(json_data)}")
                except json.JSONDecodeError:
                    # Treat as plain data
                    request_args.append(f"data='{post_data.replace("'", "\\'")}'")

            request_args_str = ", ".join(request_args)
            if request_args_str:
                code_lines.append(f"    response = api_client.{method}(\"{url}\", {request_args_str})")
            else:
                code_lines.append(f"    response = api_client.{method}(\"{url}\")")

            if response_status:
                code_lines.append(f"    response.assert_status_code({response_status})")
            code_lines.append("    # Add more assertions here based on response content")
            code_lines.append("\n")

        return "\n".join(code_lines)
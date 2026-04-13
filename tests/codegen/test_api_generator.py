import pytest
from phoenixframe.codegen.api_generator import APITestGenerator

class MockAPIClient:
    """A mock APIClient for testing generated code."""
    def get(self, url, **kwargs):
        self.last_request = {"method": "GET", "url": url, "kwargs": kwargs}
        return MockResponse(200, "{}")

    def post(self, url, **kwargs):
        self.last_request = {"method": "POST", "url": url, "kwargs": kwargs}
        return MockResponse(200, "{}")

    def assert_status_code(self, status_code):
        assert self.status_code == status_code

class MockResponse:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content

    def assert_status_code(self, status_code):
        assert self.status_code == status_code

def test_api_generator_basic_get_request():
    """Tests generation for a basic GET request."""
    data = [
        {
            "method": "GET",
            "url": "http://example.com/data",
            "response_status": 200
        }
    ]
    generator = APITestGenerator()
    generated_code = generator.generate(data)

    # Execute the generated code in a controlled environment
    local_vars = {"pytest": pytest, "api_client": MockAPIClient()}
    exec(generated_code, {}, local_vars)

    # Verify the generated test function exists and can be called
    assert "test_api_request_get_0" in local_vars
    local_vars["test_api_request_get_0"](local_vars["api_client"])

    # Verify the mock APIClient received the correct call
    assert local_vars["api_client"].last_request["method"] == "GET"
    assert local_vars["api_client"].last_request["url"] == "http://example.com/data"

def test_api_generator_post_with_json_data():
    """Tests generation for a POST request with JSON data."""
    data = [
        {
            "method": "POST",
            "url": "http://example.com/submit",
            "postData": "{\"name\": \"test\", \"value\": 123}",
            "response_status": 200
        }
    ]
    generator = APITestGenerator()
    generated_code = generator.generate(data)

    local_vars = {"pytest": pytest, "api_client": MockAPIClient()}
    exec(generated_code, {}, local_vars)

    assert "test_api_request_post_0" in local_vars
    local_vars["test_api_request_post_0"](local_vars["api_client"])

    assert local_vars["api_client"].last_request["method"] == "POST"
    assert local_vars["api_client"].last_request["url"] == "http://example.com/submit"
    assert local_vars["api_client"].last_request["kwargs"]["json"] == {"name": "test", "value": 123}

def test_api_generator_post_with_plain_data():
    """Tests generation for a POST request with plain data."""
    data = [
        {
            "method": "POST",
            "url": "http://example.com/upload",
            "postData": "plain text data",
            "response_status": 200
        }
    ]
    generator = APITestGenerator()
    generated_code = generator.generate(data)

    local_vars = {"pytest": pytest, "api_client": MockAPIClient()}
    exec(generated_code, {}, local_vars)

    assert "test_api_request_post_0" in local_vars
    local_vars["test_api_request_post_0"](local_vars["api_client"])

    assert local_vars["api_client"].last_request["method"] == "POST"
    assert local_vars["api_client"].last_request["url"] == "http://example.com/upload"
    assert local_vars["api_client"].last_request["kwargs"]["data"] == "plain text data"

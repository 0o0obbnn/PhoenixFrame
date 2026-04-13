import pytest
import json
from phoenixframe.codegen.har_parser import HARParser

def test_har_parser_valid_har():
    """Tests HARParser with a valid HAR file content."""
    har_content = json.dumps({
        "log": {
            "entries": [
                {
                    "request": {
                        "method": "GET",
                        "url": "http://example.com/api/data",
                        "headers": [{"name": "Accept", "value": "application/json"}]
                    },
                    "response": {
                        "status": 200,
                        "content": {"text": "{\"message\": \"success\"}"}
                    }
                },
                {
                    "request": {
                        "method": "POST",
                        "url": "http://example.com/api/submit",
                        "headers": [{"name": "Content-Type", "value": "application/json"}],
                        "postData": {"mimeType": "application/json", "text": "{\"key\": \"value\"}"}
                    },
                    "response": {
                        "status": 201,
                        "content": {"text": "{\"id\": 123}"}
                    }
                }
            ]
        }
    })

    parser = HARParser()
    parsed_data = parser.parse(har_content)

    assert len(parsed_data) == 2

    # Verify first request
    assert parsed_data[0]["method"] == "GET"
    assert parsed_data[0]["url"] == "http://example.com/api/data"
    assert parsed_data[0]["headers"] == {"Accept": "application/json"}
    assert parsed_data[0]["postData"] is None
    assert parsed_data[0]["response_status"] == 200
    assert parsed_data[0]["response_content"] == "{\"message\": \"success\"}"

    # Verify second request
    assert parsed_data[1]["method"] == "POST"
    assert parsed_data[1]["url"] == "http://example.com/api/submit"
    assert parsed_data[1]["headers"] == {"Content-Type": "application/json"}
    assert parsed_data[1]["postData"] == "{\"key\": \"value\"}"
    assert parsed_data[1]["response_status"] == 201
    assert parsed_data[1]["response_content"] == "{\"id\": 123}"

def test_har_parser_invalid_json():
    """Tests HARParser with invalid JSON content."""
    invalid_har_content = "{invalid json"
    parser = HARParser()
    with pytest.raises(ValueError, match="Invalid HAR file format: Not a valid JSON."):
        parser.parse(invalid_har_content)

def test_har_parser_missing_keys():
    """Tests HARParser with HAR content missing essential keys."""
    har_content_missing_log = json.dumps({"some_other_key": {}})
    parser = HARParser()
    parsed_data = parser.parse(har_content_missing_log)
    assert len(parsed_data) == 0

    har_content_missing_entries = json.dumps({"log": {"version": "1.2"}})
    parser = HARParser()
    parsed_data = parser.parse(har_content_missing_entries)
    assert len(parsed_data) == 0

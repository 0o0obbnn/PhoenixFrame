import pytest
import json
import yaml
from phoenixframe.codegen.openapi_parser import OpenAPIParser

def test_openapi_parser_valid_yaml():
    """Tests OpenAPIParser with a valid YAML OpenAPI content."""
    openapi_content = """
openapi: 3.0.0
info:
  title: Sample API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get all users
      operationId: getUsers
      responses:
        '200':
          description: A list of users
    post:
      summary: Create a new user
      operationId: createUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
  /users/{id}:
    get:
      summary: Get user by ID
      operationId: getUserById
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: User data
"""

    parser = OpenAPIParser()
    parsed_data = parser.parse(openapi_content)

    assert "info" in parsed_data
    assert parsed_data["info"]["title"] == "Sample API"
    assert "endpoints" in parsed_data
    assert len(parsed_data["endpoints"]) == 3

    assert "getUsers" in parsed_data["endpoints"]
    assert parsed_data["endpoints"]["getUsers"]["method"] == "GET"
    assert parsed_data["endpoints"]["getUsers"]["path"] == "/users"

    assert "createUser" in parsed_data["endpoints"]
    assert parsed_data["endpoints"]["createUser"]["method"] == "POST"
    assert parsed_data["endpoints"]["createUser"]["path"] == "/users"
    assert parsed_data["endpoints"]["createUser"]["requestBody"] is not None

    assert "getUserById" in parsed_data["endpoints"]
    assert parsed_data["endpoints"]["getUserById"]["method"] == "GET"
    assert parsed_data["endpoints"]["getUserById"]["path"] == "/users/{id}"
    assert len(parsed_data["endpoints"]["getUserById"]["parameters"]) == 1

def test_openapi_parser_valid_json():
    """Tests OpenAPIParser with a valid JSON OpenAPI content."""
    openapi_content = json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "Another API", "version": "1.0.0"},
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "operationId": "healthCheck",
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    })

    parser = OpenAPIParser()
    parsed_data = parser.parse(openapi_content)

    assert "info" in parsed_data
    assert parsed_data["info"]["title"] == "Another API"
    assert "endpoints" in parsed_data
    assert len(parsed_data["endpoints"]) == 1
    assert "healthCheck" in parsed_data["endpoints"]

def test_openapi_parser_invalid_format():
    """Tests OpenAPIParser with invalid OpenAPI content."""
    invalid_content = "not a valid openapi spec"
    parser = OpenAPIParser()
    with pytest.raises(ValueError, match="Error parsing OpenAPI/Swagger file"):
        parser.parse(invalid_content)

def test_openapi_parser_missing_openapi_key():
    """Tests OpenAPIParser with content missing 'openapi' key."""
    invalid_content = yaml.dump({"info": {"title": "Missing OpenAPI"}})
    parser = OpenAPIParser()
    with pytest.raises(ValueError, match="Invalid OpenAPI/Swagger specification format."):
        parser.parse(invalid_content)

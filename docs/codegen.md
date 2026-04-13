# Test Asset Codification Engine

## Overview

The PhoenixFrame Test Asset Codification Engine is a powerful new feature introduced in v3.2, designed to significantly accelerate the initial development phase of your automated tests. It acts as a bridge, transforming raw external test assets (like recorded scripts or API definitions) into structured, maintainable, and production-ready PhoenixFrame test code.

This engine promotes a "record-to-code" or "spec-to-code" workflow, reducing manual effort and ensuring consistency with PhoenixFrame's best practices (e.g., Page Object Model, data-driven testing).

## Usage

The engine is primarily accessed via the `phoenix generate` CLI command, with various subcommands for different asset types.

### 1. Generating API Tests from HAR (HTTP Archive) Files

HAR files capture all HTTP traffic during a browser session. This feature allows you to convert recorded network requests into executable API test cases.

**Command:**

```bash
phoenix generate har <path/to/your/archive.har> [--output <output_file.py>]
```

**Example:**

```bash
phoenix generate har my_login_flow.har -o tests/api/login_tests.py
```

**How it works:**

-   Parses the `.har` file to extract individual HTTP requests (method, URL, headers, body).
-   Generates a Python `pytest` function for each request.
-   Each generated function uses PhoenixFrame's `APIClient` (or a similar API testing utility) to send the request.
-   Includes basic assertions for HTTP status codes (e.g., `response.assert_status_code(200)`).
-   **Best Practice:** Review the generated code, add more specific assertions (e.g., validate response body content), and parameterize data where necessary.

### 2. Generating API Test Skeletons from OpenAPI/Swagger Specifications

OpenAPI (formerly Swagger) specifications provide a standardized, machine-readable description of RESTful APIs. This feature helps you quickly scaffold a comprehensive API test suite based on your API's contract.

**Command:**

```bash
phoenix generate openapi <path/to/your/spec.yaml_or_json> [--output <output_file.py>]
```

**Example:**

```bash
phoenix generate openapi api_v1.yaml -o tests/api/generated_api_skeletons.py
```

**How it works:**

-   Parses the OpenAPI/Swagger specification file.
-   Identifies all defined API endpoints and their methods.
-   Generates a Python `pytest` function (test skeleton) for each endpoint/method combination.
-   Includes comments and placeholders for common test scenarios (e.g., successful response, invalid input, authentication failure).
-   **Best Practice:** This generates *skeletons*. You need to fill in the actual request bodies, parameters, and detailed assertions based on your API's behavior and business logic.

### 3. Generating POM and Tests from Playwright Codegen Scripts

Playwright's `codegen` command is excellent for quickly recording UI interactions. This feature transforms those raw, procedural scripts into maintainable Page Object Model (POM) based tests, adhering to PhoenixFrame's best practices.

**Command:**

```bash
phoenix generate playwright-codegen <path/to/your/script.py> \
    [--output-pom <output_pom.py>] \
    [--output-test <output_test.py>] \
    [--output-data <output_data.yaml>]
```

**Example:**

```bash
phoenix generate playwright-codegen recorded_login.py \
    --output-pom pages/LoginPage.py \
    --output-test tests/ui/test_login.py \
    --output-data data/login_data.yaml
```

**How it works:**

-   Parses the Playwright Codegen Python script using AST (Abstract Syntax Tree) analysis.
-   Identifies `page.locator()`, `page.fill()`, `page.click()`, `expect()` and other key interactions.
-   **POM Generation:** Creates or updates a Page Object Model (POM) class, abstracting selectors and common interactions into methods.
-   **Data Extraction:** Extracts hardcoded test data (e.g., text entered into input fields) into a separate YAML data file, promoting data-driven testing.
-   **Test Case Generation:** Generates a `pytest` test function that utilizes the newly created/updated POM and the extracted data, making the test more readable and maintainable.
-   **Best Practice:** The generated POM and test code provide a strong starting point. You should refine selectors, add more robust error handling, and enhance assertions to cover all relevant UI states and business rules.

## Future Enhancements

-   **AI-Assisted Refactoring**: Leverage AI to suggest POM updates when UI changes are detected.
-   **Smart Data Generation**: Automatically generate diverse test data based on API schemas.


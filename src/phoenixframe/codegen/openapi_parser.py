import yaml
import json
from .core import AssetParser

class OpenAPIParser(AssetParser):
    """Parses an OpenAPI/Swagger specification file."""
    def parse(self, source: str) -> dict:
        """Parses the given OpenAPI/Swagger content (YAML/JSON string) and returns a structured representation."""
        try:
            # Try parsing as YAML first, then JSON
            try:
                spec_data = yaml.safe_load(source)
            except yaml.YAMLError:
                spec_data = json.loads(source)

            # Basic validation (can be enhanced with openapi-spec-validator)
            if not isinstance(spec_data, dict) or "openapi" not in spec_data:
                raise ValueError("Invalid OpenAPI/Swagger specification format.")

            # Extract endpoints (simplified for now)
            endpoints = {}
            paths = spec_data.get("paths", {})
            for path, methods in paths.items():
                for method, details in methods.items():
                    operation_id = details.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}")
                    endpoints[operation_id] = {
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary"),
                        "description": details.get("description"),
                        "parameters": details.get("parameters", []),
                        "requestBody": details.get("requestBody"),
                        "responses": details.get("responses", {})
                    }
            return {"info": spec_data.get("info", {}), "endpoints": endpoints}

        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid OpenAPI/Swagger file format: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing OpenAPI/Swagger file: {e}")

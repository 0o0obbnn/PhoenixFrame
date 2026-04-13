import json
from .core import AssetParser

class HARParser(AssetParser):
    """Parses a HAR file to extract HTTP request entries."""
    def parse(self, source: str) -> list:
        """Parses the given HAR file content (JSON string) and returns a list of request entries."""
        try:
            har_data = json.loads(source)
            entries = har_data.get("log", {}).get("entries", [])
            requests = []
            for entry in entries:
                request = entry.get("request", {})
                response = entry.get("response", {})
                requests.append({
                    "method": request.get("method"),
                    "url": request.get("url"),
                    "headers": {h["name"]: h["value"] for h in request.get("headers", [])},
                    "postData": request.get("postData", {}).get("text"),
                    "response_status": response.get("status"),
                    "response_content": response.get("content", {}).get("text"),
                })
            return requests
        except json.JSONDecodeError:
            raise ValueError("Invalid HAR file format: Not a valid JSON.")
        except Exception as e:
            raise ValueError(f"Error parsing HAR file: {e}")

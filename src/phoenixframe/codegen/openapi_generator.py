from .core import CodeGenerator

class OpenAPITestGenerator(CodeGenerator):
    """Generates API test code skeletons from OpenAPI/Swagger specification data."""
    def generate(self, data: dict) -> str:
        """Generates Python test code skeletons for OpenAPI endpoints."""
        code_lines = [
            "import pytest",
            "# Assuming APIClient is available as a pytest fixture or can be imported.",
            "# For example: from your_project.api_client import APIClient",
            "",
            "# This is auto-generated test code. Please review and enhance as needed.",
            "",
        ]

        # 处理None或非字典类型输入
        if not isinstance(data, dict):
            data = {}
            
        endpoints = data.get("endpoints", {})
        
        # 确保endpoints是字典类型
        if not isinstance(endpoints, dict):
            endpoints = {}

        for op_id, endpoint_info in endpoints.items():
            # 确保endpoint_info是字典类型
            if not isinstance(endpoint_info, dict):
                endpoint_info = {}
                
            path = endpoint_info.get("path")
            method = endpoint_info.get("method")
            summary = endpoint_info.get("summary", "")

            test_func_name = f"test_{op_id}"
            code_lines.append(f"def {test_func_name}(api_client):  # api_client should be a fixture or passed in")
            
            # 处理缺失字段的情况，保持与测试期望一致
            path_str = str(path) if path is not None else "None"
            method_str = str(method) if method is not None else "None"
            code_lines.append(f'    """Test case for {method_str} {path_str} - {summary}"""')
            
            # 使用默认值进行代码生成
            actual_path = path if path is not None else "/"
            actual_method = method if method is not None else "GET"
            
            code_lines.append("    # Example: Successful scenario (HTTP 200/201)")
            code_lines.append(f'    # response = api_client.{actual_method.lower()}("{actual_path}", json={{}})')
            code_lines.append("    # response.assert_status_code(200)  # Or 201, etc.")
            code_lines.append("")
            code_lines.append("    # Example: Invalid input scenario (HTTP 400)")
            code_lines.append(f'    # response = api_client.{actual_method.lower()}("{actual_path}", json={{}})')
            code_lines.append("    # response.assert_status_code(400)")
            code_lines.append("")
            code_lines.append("    # Example: Authentication required scenario (HTTP 401)")
            code_lines.append(f'    # response = api_client.{actual_method.lower()}("{actual_path}")')
            code_lines.append("    # response.assert_status_code(401)")
            code_lines.append("")

        return "\n".join(code_lines)
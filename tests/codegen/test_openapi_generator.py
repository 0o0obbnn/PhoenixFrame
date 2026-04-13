"""
OpenAPI测试生成器测试
测试OpenAPI规范到测试代码的转换功能
"""
import pytest
from src.phoenixframe.codegen.openapi_generator import OpenAPITestGenerator


class TestOpenAPITestGenerator:
    """测试OpenAPI测试生成器"""
    
    def test_generator_initialization(self):
        """测试生成器初始化"""
        generator = OpenAPITestGenerator()
        assert generator is not None
        assert hasattr(generator, 'generate')
    
    def test_generate_empty_data(self):
        """测试空数据生成"""
        generator = OpenAPITestGenerator()
        result = generator.generate({})
        
        # 检查基础结构
        assert "import pytest" in result
        assert "auto-generated test code" in result
        
        # 空数据应该没有测试函数
        assert "def test_" not in result
    
    def test_generate_single_endpoint(self):
        """测试单个端点生成"""
        generator = OpenAPITestGenerator()
        
        data = {
            "endpoints": {
                "get_users": {
                    "path": "/api/users",
                    "method": "GET",
                    "summary": "Get all users"
                }
            }
        }
        
        result = generator.generate(data)
        
        # 检查导入
        assert "import pytest" in result
        
        # 检查测试函数
        assert "def test_get_users(api_client):" in result
        assert "Test case for GET /api/users - Get all users" in result
        
        # 检查注释示例
        assert "# response = api_client.get(\"/api/users\", json={})" in result
        assert "# response.assert_status_code(200)" in result
        assert "# response.assert_status_code(400)" in result
        assert "# response.assert_status_code(401)" in result
    
    def test_generate_multiple_endpoints(self):
        """测试多个端点生成"""
        generator = OpenAPITestGenerator()
        
        data = {
            "endpoints": {
                "get_users": {
                    "path": "/api/users",
                    "method": "GET",
                    "summary": "Get all users"
                },
                "create_user": {
                    "path": "/api/users",
                    "method": "POST",
                    "summary": "Create a new user"
                },
                "update_user": {
                    "path": "/api/users/{id}",
                    "method": "PUT",
                    "summary": "Update user by ID"
                }
            }
        }
        
        result = generator.generate(data)
        
        # 检查所有测试函数都被生成
        assert "def test_get_users(api_client):" in result
        assert "def test_create_user(api_client):" in result
        assert "def test_update_user(api_client):" in result
        
        # 检查路径和方法
        assert "GET /api/users - Get all users" in result
        assert "POST /api/users - Create a new user" in result
        assert "PUT /api/users/{id} - Update user by ID" in result
        
        # 检查不同HTTP方法的调用
        assert "api_client.get(\"/api/users\"" in result
        assert "api_client.post(\"/api/users\"" in result
        assert "api_client.put(\"/api/users/{id}\"" in result
    
    def test_generate_endpoint_without_summary(self):
        """测试没有summary的端点生成"""
        generator = OpenAPITestGenerator()
        
        data = {
            "endpoints": {
                "delete_user": {
                    "path": "/api/users/{id}",
                    "method": "DELETE"
                    # 没有summary字段
                }
            }
        }
        
        result = generator.generate(data)
        
        # 检查测试函数
        assert "def test_delete_user(api_client):" in result
        assert "Test case for DELETE /api/users/{id} -" in result
        assert "api_client.delete(\"/api/users/{id}\"" in result
    
    def test_generate_with_complex_operation_ids(self):
        """测试复杂操作ID的处理"""
        generator = OpenAPITestGenerator()
        
        data = {
            "endpoints": {
                "getUsersByStatus": {
                    "path": "/api/users/status/{status}",
                    "method": "GET",
                    "summary": "Get users by status"
                },
                "search-users-by-name": {
                    "path": "/api/users/search",
                    "method": "POST",
                    "summary": "Search users by name"
                }
            }
        }
        
        result = generator.generate(data)
        
        # 检查操作ID被正确转换为测试函数名
        assert "def test_getUsersByStatus(api_client):" in result
        assert "def test_search-users-by-name(api_client):" in result
        
        # 检查路径正确
        assert "GET /api/users/status/{status}" in result
        assert "POST /api/users/search" in result
    
    def test_generate_different_http_methods(self):
        """测试不同HTTP方法的生成"""
        generator = OpenAPITestGenerator()
        
        data = {
            "endpoints": {
                "get_resource": {
                    "path": "/api/resource",
                    "method": "GET",
                    "summary": "Get resource"
                },
                "post_resource": {
                    "path": "/api/resource",
                    "method": "POST",
                    "summary": "Create resource"
                },
                "put_resource": {
                    "path": "/api/resource/{id}",
                    "method": "PUT",
                    "summary": "Update resource"
                },
                "patch_resource": {
                    "path": "/api/resource/{id}",
                    "method": "PATCH",
                    "summary": "Patch resource"
                },
                "delete_resource": {
                    "path": "/api/resource/{id}",
                    "method": "DELETE",
                    "summary": "Delete resource"
                }
            }
        }
        
        result = generator.generate(data)
        
        # 检查所有HTTP方法的调用都被正确生成
        assert "api_client.get(\"/api/resource\"" in result
        assert "api_client.post(\"/api/resource\"" in result
        assert "api_client.put(\"/api/resource/{id}\"" in result
        assert "api_client.patch(\"/api/resource/{id}\"" in result
        assert "api_client.delete(\"/api/resource/{id}\"" in result
    
    def test_generate_code_structure(self):
        """测试生成代码的结构"""
        generator = OpenAPITestGenerator()
        
        data = {
            "endpoints": {
                "simple_test": {
                    "path": "/api/test",
                    "method": "GET",
                    "summary": "Simple test"
                }
            }
        }
        
        result = generator.generate(data)
        lines = result.split('\n')
        
        # 检查代码结构
        assert lines[0] == "import pytest"
        assert any("APIClient" in line for line in lines[:5])
        assert any("auto-generated test code" in line for line in lines[:5])
        
        # 检查函数结构
        function_start = next(i for i, line in enumerate(lines) if "def test_simple_test" in line)
        assert lines[function_start + 1].strip().startswith('"""Test case for')
        assert lines[function_start + 1].strip().endswith('"""')
        
        # 检查注释示例的完整性
        example_lines = [line for line in lines if "# response = api_client" in line or "# response.assert_status_code" in line]
        assert len(example_lines) >= 6  # 至少应该有6行示例（每种场景2行）
    
    def test_generate_with_missing_endpoint_fields(self):
        """测试端点字段缺失的情况"""
        generator = OpenAPITestGenerator()
        
        data = {
            "endpoints": {
                "incomplete_endpoint": {
                    # 缺少path, method, summary
                }
            }
        }
        
        result = generator.generate(data)
        
        # 应该生成基础结构，即使端点信息不完整
        assert "import pytest" in result
        assert "def test_incomplete_endpoint(api_client):" in result
        
        # 缺失字段应该有合理的默认处理
        assert "Test case for None None" in result or "Test case for  " in result
    
    def test_generate_preserves_endpoint_order(self):
        """测试端点顺序的保持"""
        generator = OpenAPITestGenerator()
        
        data = {
            "endpoints": {
                "first_endpoint": {
                    "path": "/api/first",
                    "method": "GET",
                    "summary": "First endpoint"
                },
                "second_endpoint": {
                    "path": "/api/second",
                    "method": "POST",
                    "summary": "Second endpoint"
                },
                "third_endpoint": {
                    "path": "/api/third",
                    "method": "PUT",
                    "summary": "Third endpoint"
                }
            }
        }
        
        result = generator.generate(data)
        
        # 找到每个测试函数的位置
        first_pos = result.find("def test_first_endpoint")
        second_pos = result.find("def test_second_endpoint")
        third_pos = result.find("def test_third_endpoint")
        
        # 检查顺序（在Python 3.7+中，字典保持插入顺序）
        assert first_pos < second_pos < third_pos


class TestOpenAPITestGeneratorEdgeCases:
    """测试OpenAPI生成器边界情况"""
    
    def test_generate_with_none_data(self):
        """测试None数据输入"""
        generator = OpenAPITestGenerator()
        
        # 这应该不抛出异常，而是优雅处理
        result = generator.generate(None)
        assert "import pytest" in result
    
    def test_generate_with_malformed_data(self):
        """测试格式错误的数据"""
        generator = OpenAPITestGenerator()
        
        # 测试非字典类型的endpoints
        data = {
            "endpoints": "not_a_dict"
        }
        
        # 应该优雅处理，不抛出异常
        result = generator.generate(data)
        assert "import pytest" in result
    
    def test_generate_with_empty_endpoints(self):
        """测试空的endpoints"""
        generator = OpenAPITestGenerator()
        
        data = {
            "endpoints": {}
        }
        
        result = generator.generate(data)
        
        # 应该包含基础结构但没有测试函数
        assert "import pytest" in result
        assert "def test_" not in result
    
    def test_generate_output_format_consistency(self):
        """测试输出格式的一致性"""
        generator = OpenAPITestGenerator()
        
        data = {
            "endpoints": {
                "test_endpoint": {
                    "path": "/api/test",
                    "method": "GET",
                    "summary": "Test endpoint"
                }
            }
        }
        
        result = generator.generate(data)
        
        # 检查输出是字符串
        assert isinstance(result, str)
        
        # 检查没有多余的空行在开头或结尾
        lines = result.split('\n')
        assert lines[0].strip() != ""  # 第一行不应该是空行
        
        # 检查每个测试函数后有适当的空行分隔
        test_function_lines = [i for i, line in enumerate(lines) if line.startswith("def test_")]
        if len(test_function_lines) > 1:
            # 如果有多个测试函数，检查它们之间有空行分隔
            for i in range(len(test_function_lines) - 1):
                current_func_line = test_function_lines[i]
                next_func_line = test_function_lines[i + 1]
                # 在两个函数之间应该有空行
                assert any(lines[j].strip() == "" for j in range(current_func_line + 1, next_func_line))


@pytest.fixture
def sample_openapi_data():
    """示例OpenAPI数据fixture"""
    return {
        "endpoints": {
            "list_users": {
                "path": "/api/v1/users",
                "method": "GET",
                "summary": "List all users"
            },
            "create_user": {
                "path": "/api/v1/users",
                "method": "POST",
                "summary": "Create a new user"
            },
            "get_user": {
                "path": "/api/v1/users/{user_id}",
                "method": "GET",
                "summary": "Get user by ID"
            },
            "update_user": {
                "path": "/api/v1/users/{user_id}",
                "method": "PUT",
                "summary": "Update user by ID"
            },
            "delete_user": {
                "path": "/api/v1/users/{user_id}",
                "method": "DELETE",
                "summary": "Delete user by ID"
            }
        }
    }


class TestOpenAPITestGeneratorWithFixture:
    """使用fixture的OpenAPI生成器测试"""
    
    def test_generate_complete_api_test_suite(self, sample_openapi_data):
        """测试生成完整的API测试套件"""
        generator = OpenAPITestGenerator()
        result = generator.generate(sample_openapi_data)
        
        # 检查所有端点都被处理
        expected_functions = [
            "test_list_users",
            "test_create_user", 
            "test_get_user",
            "test_update_user",
            "test_delete_user"
        ]
        
        for func_name in expected_functions:
            assert f"def {func_name}(api_client):" in result
        
        # 检查CRUD操作的完整性
        assert "GET /api/v1/users - List all users" in result
        assert "POST /api/v1/users - Create a new user" in result
        assert "GET /api/v1/users/{user_id} - Get user by ID" in result
        assert "PUT /api/v1/users/{user_id} - Update user by ID" in result
        assert "DELETE /api/v1/users/{user_id} - Delete user by ID" in result
        
        # 检查不同HTTP方法的客户端调用
        assert "api_client.get(\"/api/v1/users\"" in result
        assert "api_client.post(\"/api/v1/users\"" in result
        assert "api_client.put(\"/api/v1/users/{user_id}\"" in result
        assert "api_client.delete(\"/api/v1/users/{user_id}\"" in result
    
    def test_generated_code_is_valid_python(self, sample_openapi_data):
        """测试生成的代码是有效的Python代码"""
        generator = OpenAPITestGenerator()
        result = generator.generate(sample_openapi_data)
        
        # 尝试编译生成的代码
        try:
            compile(result, '<generated>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")
    
    def test_generated_code_structure_quality(self, sample_openapi_data):
        """测试生成代码的结构质量"""
        generator = OpenAPITestGenerator()
        result = generator.generate(sample_openapi_data)
        
        lines = result.split('\n')
        
        # 检查导入语句在顶部
        import_lines = [i for i, line in enumerate(lines) if line.startswith('import')]
        assert len(import_lines) > 0
        assert import_lines[0] == 0  # 第一个导入应该在第一行
        
        # 检查每个测试函数都有docstring
        test_function_lines = [i for i, line in enumerate(lines) if line.startswith("def test_")]
        for func_line in test_function_lines:
            # 下一行应该是docstring开始
            assert lines[func_line + 1].strip().startswith('"""')
            assert lines[func_line + 1].strip().endswith('"""')
        
        # 检查代码注释的存在
        comment_lines = [line for line in lines if line.strip().startswith('#')]
        assert len(comment_lines) > 10  # 应该有足够多的注释示例
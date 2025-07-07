### **PhoenixFrame v3.2 - 精细化开发排期 (Gemini CLI 执行版)**

**授权确认:** 您已授权 Gemini CLI 在当前项目目录 (`G:\nifa\PhoenixFrame`) 中执行增、改、查等文件和命令操作。

**开发模式:** 我将严格按照此排期，一步一步执行任务。每完成一个关键节点，会向您同步状态。

**时间单位:** `h` 代表“小时 (hour)”。

---

#### **第一阶段：项目地基与环境搭建 (预计: 4h)**

**目标:** 建立一个健壮的、自动化的、符合现代 Python 工程实践的项目骨架。

| 任务 ID | 模块 | 任务拆解 (Task Breakdown) | 核心指令 | 预估 (h) |
| :--- | :--- | :--- | :--- | :--- |
| **1.1** | **版本控制** | 1.1.1: 在项目根目录执行 `git init`。 | `run_shell_command` | 0.1 |
| **1.2** | **目录结构** | 1.2.1: 创建核心源码目录 `src/phoenixframe`。 <br> 1.2.2: 创建测试代码目录 `tests`。 <br> 1.2.3: 在 `src/phoenixframe` 中创建空的 `__init__.py`。 <br> 1.2.4: 在 `tests` 中创建空的 `__init__.py`。 | `run_shell_command`, `write_file` | 0.2 |
| **1.3** | **依赖管理** | 1.3.1: 创建 `pyproject.toml` 文件。 <br> 1.3.2: 写入 `[build-system]` 和基础的 `[tool.poetry]` 配置。 <br> 1.3.3: 添加核心依赖 `pytest`, `click`, `pydantic`, `pyyaml`。 <br> 1.3.4: 添加开发依赖 `ruff`, `pytest-cov`。 | `write_file` | 1.0 |
| **1.4** | **代码规范** | 1.4.1: 在 `pyproject.toml` 中添加 `[tool.ruff]` 和 `[tool.ruff.lint]` 配置，定义代码规范规则。 | `replace` | 0.5 |
| **1.5** | **Git 忽略** | 1.5.1: 创建 `.gitignore` 文件。 <br> 1.5.2: 添加通用 Python 忽略规则 (如 `__pycache__/`, `.pytest_cache/`, `*.pyc`) 和 IDE 配置文件。 | `write_file` | 0.2 |
| **1.6** | **CI/CD** | 1.6.1: 创建 `.github/workflows/` 目录。 <br> 1.6.2: 创建 `ci.yml` 文件。 <br> 1.6.3: 编写 CI 工作流：检出代码 -> 设置 Python -> 安装依赖 -> 运行 `ruff check .` -> 运行 `pytest`。 | `run_shell_command`, `write_file` | 1.5 |
| **1.7** | **阶段验证** | 1.7.1: 提交所有初始化文件到 Git。 <br> 1.7.2: (可选) 推送到远程仓库，验证 CI 是否通过。 | `run_shell_command` | 0.5 |

---

#### **第二阶段：核心引擎与 CLI 增强 (预计: 8h)**

**目标:** 实现设计文档中规划的、用于提升框架易用性的辅助性 CLI 命令。

| 任务 ID | 模块 | 任务拆解 (Task Breakdown) | 核心指令 | 预估 (h) |
| :--- | :--- | :--- | :--- | :--- |
| **2.1** | **CLI 入口** | 2.1.1: 创建 `src/phoenixframe/cli.py`。 <br> 2.1.2: 使用 `click` 设置一个主命令组 `phoenix`。 | `write_file` | 0.5 |
| **2.2** | **`doctor` 命令** | 2.2.1: 创建 `src/phoenixframe/doctor.py`。 <br> 2.2.2: 实现 `check_python_version()` 函数。 <br> 2.2.3: 实现 `check_dependencies()` 函数 (读取 `pyproject.toml`)。 <br> 2.2.4: 在 `cli.py` 中集成 `doctor` 命令。 <br> 2.2.5: 创建 `tests/test_doctor.py` 并编写单元测试。 | `write_file`, `replace` | 4.0 |
| **2.3** | **`env` 命令** | 2.3.1: 创建 `src/phoenixframe/env.py`。 <br> 2.3.2: 实现 `list_environments()` 函数，需能解析 YAML 文件。 <br> 2.3.3: 在 `cli.py` 中集成 `env list` 命令。 <br> 2.3.4: 创建 `tests/test_env.py`，准备一个 `mock_phoenix.yaml` 并编写单元测试。 | `write_file`, `replace` | 3.5 |

---

#### **第三阶段：测试资产代码化引擎 (预计: 24h)**

**目标:** 完成 v3.2 的核心亮点功能，这是项目攻坚的关键。

| 任务 ID | 模块 | 任务拆解 (Task Breakdown) | 核心指令 | 预估 (h) |
| :--- | :--- | :--- | :--- | :--- |
| **3.1** | **引擎骨架** | 3.1.1: 创建 `src/phoenixframe/codegen/` 目录及 `__init__.py`。 <br> 3.1.2: 创建 `src/phoenixframe/codegen/core.py`，定义 `AssetParser` 和 `CodeGenerator` 抽象基类。 <br> 3.1.3: 在 `cli.py` 中添加 `generate` 命令组。 | `write_file`, `replace` | 2.0 |
| **3.2** | **HAR 支持** | 3.2.1: 创建 `src/phoenixframe/codegen/har_parser.py`。 <br> 3.2.2: 实现 `HARParser` 类，继承 `AssetParser`，完成对 `.har` 文件的解析。 <br> 3.2.3: 创建 `src/phoenixframe/codegen/api_generator.py`，实现 `APITestGenerator`，将解析数据转为 API 测试代码。 <br> 3.2.4: 在 `generate` 命令组中添加 `from-har` 子命令。 <br> 3.2.5: 编写 `tests/codegen/test_har_parser.py` 和 `test_api_generator.py` 的单元测试。 | `write_file`, `replace` | 8.0 |
| **3.3** | **OpenAPI 支持** | 3.3.1: 创建 `src/phoenixframe/codegen/openapi_parser.py`。 <br> 3.3.2: 实现 `OpenAPIParser` 类，解析 OpenAPI 规范。 <br> 3.3.3: 复用或扩展 `APITestGenerator` 以支持 OpenAPI 数据结构。 <br> 3.3.4: 在 `generate` 命令组中添加 `from-openapi` 子命令。 <br> 3.3.5: 编写对应的单元测试。 | `write_file`, `replace` | 6.0 |
| **3.4** | **Playwright 支持** | 3.4.1: 创建 `src/phoenixframe/codegen/playwright_parser.py`。 <br> 3.4.2: **核心:** 使用 `ast` 模块实现对 Python 脚本的解析，提取关键操作。 <br> 3.4.3: 创建 `src/phoenixframe/codegen/pom_generator.py`，实现 `POMGenerator`，将解析数据转为 POM 模式代码和 YAML 数据文件。 <br> 3.4.4: 在 `generate` 命令组中添加 `from-playwright` 子命令。 <br> 3.4.5: 编写对应的单元测试。 | `write_file`, `replace` | 8.0 |

---

#### **第四阶段：文档与发布 (预计: 4h)**

**目标:** 确保项目成果可以被他人理解和使用。

| 任务 ID | 模块 | 任务拆解 (Task Breakdown) | 核心指令 | 预估 (h) |
| :--- | :--- | :--- | :--- | :--- |
| **4.1** | **文档** | 4.1.1: 更新 `README.md`，加入新功能介绍和 CLI 用法。 <br> 4.1.2: 创建 `docs/` 目录和 `codegen.md`，详细描述代码生成引擎。 <br> 4.1.3: 为所有 CLI 命令添加完整的 `help` 文档。 | `write_file`, `replace` | 3.0 |
| **4.2** | **发布准备** | 4.2.1: 更新 `CHANGELOG.md`。 <br> 4.2.2: 在 `pyproject.toml` 中将版本号更新为 `3.2.0`。 <br> 4.2.3: 创建 Git tag `v3.2.0`。 | `write_file`, `replace`, `run_shell_command` | 1.0 |

---

**总计预估时间: 40 小时 (约 5 个标准工作日)**

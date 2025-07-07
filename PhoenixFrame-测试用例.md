# PhoenixFrame v3.2 - 测试用例

**版本:** 1.0
**日期:** 2023年10月29日

## 1. 宗旨

本文档定义了 PhoenixFrame v3.2 版本所需满足的核心测试用例。所有用例的通过是版本发布的先决条件。本文档将作为开发过程中的验收标准，指导功能实现并确保其质量、稳定性和安全性。

---

## 2. 测试用例详情

### 模块一：命令行接口 (CLI)

#### 2.1. `phoenix doctor` 命令

| 用例ID | 测试标题 | 前提条件 | 测试步骤 | 预期结果 | 类型 | 优先级 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CLI-DOC-001** | 在健康环境中执行检查 | 1. `uv` 虚拟环境已激活。<br>2. `pyproject.toml` 中所有依赖已安装。 | 1. 在终端执行 `phoenix doctor`。 | 1. 命令成功退出 (exit code 0)。<br>2. 输出报告所有检查项均为“OK”或“Passed”。 | 功能 | 高 |
| **CLI-DOC-002** | 在缺少依赖的环境中执行检查 | 1. `uv` 虚拟环境已激活。<br>2. 手动从 `pyproject.toml` 移除一个依赖（如 `pydantic`）但未同步。 | 1. 在终端执行 `phoenix doctor`。 | 1. 命令成功退出。<br>2. 输出明确报告 `pydantic` 依赖缺失或版本不匹配。 | 功能 | 高 |
| **CLI-DOC-003** | 检查 `doctor` 命令的帮助信息 | 无 | 1. 在终端执行 `phoenix doctor --help`。 | 1. 显示清晰、格式正确的帮助信息，描述命令用途和所有可用选项。 | 易用性 | 中 |

#### 2.2. `phoenix generate` 命令 (核心功能)

| 用例ID | 测试标题 | 前提条件 | 测试步骤 | 预期结果 | 类型 | 优先级 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CLI-GEN-001** | 从有效的 HAR 文件生成 API 测试 | 1. 准备一个有效的 `.har` 文件 (`test.har`)。<br>2. 文件中包含至少2个HTTP请求。 | 1. 执行 `phoenix generate --from har test.har`。 | 1. 命令成功退出。<br>2. 在指定目录生成一个新的 Python 文件 (如 `test_generated.py`)。<br>3. 生成的文件包含2个 `pytest` 测试函数。<br>4. 每个函数都正确调用了框架的 API 客户端，并包含基础的状态码断言。 | 功能 | **极高** |
| **CLI-GEN-002** | 从有效的 OpenAPI 文件生成测试骨架 | 1. 准备一个有效的 `openapi.yaml` 文件，包含多个端点。 | 1. 执行 `phoenix generate --from openapi openapi.yaml`。 | 1. 命令成功退出。<br>2. 为每个 API 端点生成一个独立的 Python 测试文件。<br>3. 每个文件包含多个测试用例骨架（成功、认证失败、无效参数等）。<br>4. 如果规范中含 Schema，则生成对应的 Pydantic 模型。 | 功能 | **极高** |
| **CLI-GEN-003** | 从有效的 Playwright Codegen 脚本生成 POM 测试 | 1. 准备一个有效的 Playwright Codegen 脚本 (`codegen_script.py`)。<br>2. 脚本包含页面交互和硬编码数据。 | 1. 执行 `phoenix generate --from playwright-codegen codegen_script.py`。 | 1. 命令成功退出。<br>2. 生成一个新的 POM 类文件 (`*.py`)。<br>3. 生成一个包含提取数据的 YAML 文件 (`*.yaml`)。<br>4. 生成一个使用该 POM 和数据文件的新测试用例文件 (`test_*.py`)。 | 功能 | **极高** |
| **CLI-GEN-004** | 使用不存在的文件路径 | 无 | 1. 执行 `phoenix generate --from har non_existent_file.har`。 | 1. 命令失败退出 (exit code > 0)。<br>2. 向用户显示清晰的“文件未找到”错误信息。 | 负面 | 高 |
| **CLI-GEN-005** | 使用格式错误的输入文件 | 1. 准备一个 JSON 语法错误的 `.har` 文件。 | 1. 执行 `phoenix generate --from har malformed.har`。 | 1. 命令失败退出。<br>2. 显示清晰的“文件解析失败”或“格式错误”信息。 | 负面 | 高 |
| **CLI-GEN-006** | 检查 `generate` 命令的帮助信息 | 无 | 1. 执行 `phoenix generate --help`。 | 1. 显示 `generate` 命令的用途。<br>2. 清晰列出所有子命令 (`from-har`, `from-openapi` 等) 及其用法。 | 易用性 | 中 |

---

### 模块二：安全与加密 (`CryptoUtil`)

| 用例ID | 测试标题 | 前提条件 | 测试步骤 | 预期结果 | 类型 | 优先级 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-CRY-001** | 使用国密算法成功加解密 | 1. 准备一段明文字符串。 | 1. 调用 `CryptoUtil.sm4_encrypt()` 加密字符串。<br>2. 使用上一步得到的密文和密钥，调用 `CryptoUtil.sm4_decrypt()` 解密。 | 1. 加密成功，返回非明文的字符串。<br>2. 解密成功，返回的字符串与原始明文完全一致。 | 功能 | 高 |
| **SEC-CRY-002** | 密钥加载优先级测试 | 1. 准备三个不同的密钥，分别存放在 KMS、环境变量、本地文件中。<br>2. 配置框架同时可访问这三个源。 | 1. 调用 `CryptoUtil` 的密钥加载逻辑。 | 1. 验证加载到的密钥是来自 KMS 的密钥，证明优先级最高。 | 安全 | **极高** |
| **SEC-CRY-003** | 使用错误的密钥解密 | 1. 使用密钥 A 加密一段数据。 | 1. 尝试使用密钥 B 解密上一步的数据。 | 1. 解密函数应抛出特定的解密失败异常或返回错误状态，而不是返回无意义的乱码。 | 负面 | 高 |

---

### 模块三：API 自动化 (声明式引擎)

| 用例ID | 测试标题 | 前提条件 | 测试步骤 | 预期结果 | 类型 | 优先级 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **API-DEC-001** | `setup_hooks` 和 `teardown_hooks` 执行测试 | 1. 准备一个 `.hr.yml` 文件，其中包含 `setup_hooks` 和 `teardown_hooks`，钩子函数会打印特定日志。 | 1. 使用 `phoenix run` 执行该 YAML 文件。 | 1. 在测试步骤执行前，`setup_hooks` 的日志被打印。<br>2. 在测试步骤执行后，`teardown_hooks` 的日志被打印。 | 功能 | 高 |
| **API-DEC-002** | `schema_validate` 验证器测试 | 1. 准备一个 API，其响应体符合特定的 JSON Schema。<br>2. 准备一个 `.hr.yml`，使用 `schema_validate` 验证器。 | 1. 执行测试。 | 1. 测试用例通过。 | 功能 | 高 |
| **API-DEC-003** | `schema_validate` 验证器失败测试 | 1. API 响应体故意与 JSON Schema 不符。 | 1. 执行测试。 | 1. 测试用例失败，并明确指出 Schema 验证失败的字段和原因。 | 负面 | 高 |

---

### 模块四：可观测性 (Observability)

| 用例ID | 测试标题 | 前提条件 | 测试步骤 | 预期结果 | 类型 | 优先级 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OBS-LOG-001** | 结构化日志验证 | 1. 配置日志级别为 INFO，格式为 JSON。 | 1. 运行任意一个测试用例。 | 1. 控制台或日志文件输出的日志是有效的 JSON 格式。<br>2. 每条日志记录都包含 `timestamp`, `level`, `message` 等标准字段。 | 功能 | 高 |
| **OBS-LOG-002** | 上下文 ID (`test_run_id`) 注入验证 | 1. 配置日志格式包含 `test_run_id`。 | 1. 同时并行运行2个测试用例。 | 1. 检查日志输出，属于同一个测试用例的所有日志，都包含相同的 `test_run_id`。<br>2. 两个不同测试用例的 `test_run_id` 必须不同。 | 功能 | **极高** |

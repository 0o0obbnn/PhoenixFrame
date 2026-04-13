PhoenixFrame 开发排期计划 (基于功能最小粒度)
本开发排期计划旨在将 PhoenixFrame v3.2 的功能拆解为最小可实现的单元，并按照逻辑依赖和优先级进行分阶段安排。

阶段一：核心基础框架 (Foundation)
此阶段专注于构建框架的基石，确保核心测试运行、配置和基本自动化能力。

项目初始化与配置管理

实现 phoenix init <project_name> 命令，生成基础项目结构。

定义并创建项目骨架（例如：tests/, configs/, pages/, apis/, data/, utils/ 目录）。

编写 phoenix init 命令的 Click/Typer 实现。

实现文件和目录的创建逻辑，包括 .gitignore 和 README.md。

集成 YAML 作为配置格式。

确定核心配置 phoenix.yaml 的初始结构（例如：环境配置、报告配置）。

编写 YAML 文件读写工具函数（使用 PyYAML 库）。

集成 Pydantic 进行配置模型定义和校验。

定义核心配置的 Pydantic 模型（例如：ConfigModel）。

实现配置加载时使用 Pydantic 进行数据类型校验和默认值填充。

实现配置加载与管理模块。

编写配置加载函数，处理默认值、环境变量覆盖（例如：os.getenv）。

实现配置的全局访问机制（例如：单例模式或依赖注入）。

核心引擎与运行器

集成 pytest 作为测试运行器。

编写 conftest.py 文件，配置 pytest 插件（例如：allure-pytest）。

实现 pytest 钩子函数的注册和自定义（例如：pytest_runtest_makereport）。

实现 PhoenixRunner 的基础调度逻辑。

定义 PhoenixRunner 类，作为框架的执行入口。

实现测试用例的发现（例如：通过 pytest.main）和执行调度。

定义并实现核心配置模块。

将 Pydantic 定义的核心配置集成到引擎中，确保配置在运行时可用。

设计并实现基础的生命周期钩子机制。

定义框架级别的生命周期事件（例如：on_test_run_start, on_test_case_end, on_step_start）。

实现钩子函数的注册和调用（例如：通过事件发布/订阅模式）。

设计并实现插件系统的基础架构。

定义插件接口（例如：抽象基类或协议）。

实现插件的加载和管理机制（例如：通过 setuptools entry points）。

命令行接口 (CLI) 基础功能

实现 phoenix run [options] 命令的测试执行入口。

编写 run 命令的 Click/Typer 实现。

调用 PhoenixRunner 执行测试，并传递 CLI 参数。

处理 CLI 参数到 PhoenixRunner 配置的映射。

实现 phoenix report 命令的报告查看入口。

编写 report 命令的 Click/Typer 实现。

调用 Allure CLI 命令（例如：allure serve）或直接打开报告目录。

集成 Click / Typer 作为 CLI 库。

设置主 phoenix 命令和子命令结构。

Web 自动化 (Selenium 基础)

实现 selenium_page Fixture 的基础功能，提供页面交互能力。

定义 selenium_page pytest Fixture，提供 WebDriver 实例。

初始化 WebDriver (例如：Chrome, Firefox)。

实现基本页面操作方法（例如：get(url), find_element(locator), click(), fill(text)）。

实现 WebDriver 的生命周期管理（启动、关闭）。

集成 Selenium 驱动管理。

考虑使用 webdriver_manager 库自动下载和管理 WebDriver 驱动。

API 自动化 (编程式基础)

实现基础的 APIClient，封装 requests 库。

定义 APIClient 类，作为所有 API 请求的基类。

封装 requests.get, requests.post, requests.put, requests.delete 等 HTTP 方法。

实现基本的 HTTP 请求发送和响应处理。

实现请求参数（headers, params, json, data, files）的传递。

实现响应对象的封装，提供便捷的属性访问（例如：response.status_code, response.json()）。

实现基础的断言机制（例如：状态码断言）。

在 APIClient 响应对象上添加 assert_status_code(expected_code) 方法。

考虑添加 assert_json_value(jsonpath, expected_value) 基础断言。

基础可观测性

集成 logging 模块，实现结构化日志的基础输出。

配置 Python logging 模块，设置日志级别和处理器。

实现 JSON 格式的日志 formatter（例如：使用 python-json-logger）。

集成 colorlog 提升日志可读性。

配置 colorlog 库，为控制台输出添加颜色。

实现 test_run_id 的生成和基础注入到日志中。

在 PhoenixRunner 启动时生成一个唯一的 UUID 作为 test_run_id。

使用 logging.Filter 或自定义 logging.Formatter 将 test_run_id 注入到每个日志记录中。

阶段二：核心功能增强 (Core Enhancements)
在基础框架之上，扩展和强化 Web 及 API 自动化能力，并引入 BDD 支持。

API 自动化 (声明式引擎)

实现 PhoenixRunner 对 YAML 格式测试用例的解析和执行。

编写 YAML 解析器，将 YAML 文件内容转换为 Python 对象。

定义声明式测试用例的 Pydantic 模型，严格校验 YAML 结构。

实现将解析后的 YAML 对象转换为可执行的测试步骤对象。

实现 setup_hooks 和 teardown_hooks 的执行逻辑。

解析 YAML 中的 setup_hooks 和 teardown_hooks 定义（例如：函数名字符串）。

实现动态导入和执行 Python 函数作为 hook。

实现内置复杂验证器（contains, jsonpath_validate, less_than, has_keys）。

在声明式引擎中实现这些验证逻辑，支持对响应内容的复杂校验。

考虑使用 jsonpath-ng 或类似库实现 jsonpath_validate。

实现 schema_validate (JSON Schema) 功能。

集成 jsonschema 库。

实现根据外部 JSON Schema 文件对 API 响应体进行结构校验。

实现可复用的测试块 (include 关键字)。

实现 YAML 文件中的 include 引用机制，支持引用其他 YAML 文件中的测试步骤。

处理循环引用和相对/绝对文件路径解析。

实现文件上传语法解析和处理。

解析 YAML 中文件上传的定义（例如：files: {"file_field": "path/to/file.txt"}）。

在 APIClient 中实现文件上传的 requests 调用。

API 自动化 (编程式高级)

实现 APIClient 的自动认证机制（例如：Token 刷新）。

设计认证策略接口（例如：AuthStrategy 抽象类）。

实现基于 Token 的认证器，支持自动获取和刷新 Token。

将认证器集成到 APIClient，使其在每次请求前自动处理认证。

实现链式断言库。

设计一个响应断言类，支持对 APIClient 响应对象进行链式调用。

实现 assert_json_path(path, expected_value), assert_header(name, value) 等高级断言方法。

实现自动追踪集成，为每次请求生成 Trace ID 并注入请求头。

在 APIClient 发送请求前创建 OpenTelemetry Span。

将生成的 Trace ID 和 Span ID 注入到请求头中（例如：traceparent）。

Web 自动化 (Playwright 基础)

实现 playwright_page Fixture 的基础功能，提供异步页面交互能力。

定义 playwright_page pytest Fixture，提供 Playwright Page 实例。

初始化 Playwright Browser 和 Page。

实现基本异步页面操作方法（例如：await page.goto(url), await page.locator(selector).click()）。

实现 Playwright 的生命周期管理（启动、关闭浏览器上下文）。

集成 Playwright 驱动管理。

确保 Playwright 依赖（例如：浏览器二进制文件）已正确安装和配置。

BDD 支持

集成 pytest-bdd。

配置 pytest-bdd 插件，使其能够发现 .feature 文件。

编写一个简单的 .feature 文件示例。

实现 BDD 步骤定义和关联。

编写 steps 文件，使用 given, when, then 装饰器定义 BDD 步骤。

确保 BDD 步骤能够调用框架的 Web/API 自动化能力和 Fixture。

CLI 脚手架

实现 phoenix scaffold --type page --name <name> 命令，生成页面对象模板。

编写命令逻辑，根据模板生成 Python 类文件。

创建 Page Object 模板文件，包含基本结构和示例元素。

实现 phoenix scaffold --type api --name <name> 命令，生成 API 对象模板。

编写命令逻辑，根据模板生成 Python 类文件。

创建 API Client 模板文件，包含基本结构和示例方法。

实现 phoenix scaffold --type bdd --name <name> 命令，生成 BDD 步骤定义模板。

编写命令逻辑，根据模板生成 Python 文件。

创建 BDD 步骤文件模板，包含 given, when, then 示例。

阶段三：高级能力与跨领域集成 (Advanced Capabilities & Integrations)
引入企业级可观测性、安全、性能和辅助工具，并完善 CLI。

企业级可观测性

集成 OpenTelemetry SDK。

安装 opentelemetry-sdk 及其相关导出器（例如：opentelemetry-exporter-otlp）。

配置 TracerProvider 和 SpanProcessor。

实现全链路追踪，为 API 请求和关键业务步骤创建 Trace Span。

在 PhoenixRunner 中创建测试运行的根 Span。

在 APIClient 的每个请求和 selenium_page/playwright_page 的关键操作中创建子 Span。

实现 Span 的上下文传播，确保 Trace ID 在不同组件间传递。

实现度量 (Metrics) 的收集和上报。

定义关键指标（例如：测试执行总时间、通过率、失败率、API 响应时间 P95）。

使用 OpenTelemetry Meter 记录和聚合这些指标。

实现浏览器控制台日志的自动采集和关联到 Allure 报告。

在 Web 驱动中注入 JavaScript，捕获浏览器控制台日志（INFO, WARN, ERROR）。

将捕获的日志作为附件或步骤详情关联到 Allure 报告的对应测试步骤中。

确保 test_run_id 贯穿所有日志和 Trace。

将 test_run_id 作为 OpenTelemetry Trace 的资源属性或 Span 属性注入。

安全加密与密钥管理

实现 CryptoUtil 模块的基础加密解密功能。

封装 cryptography 库，提供对称加密（例如：AES）和非对称加密（例如：RSA）的常用接口。

研究并考虑支持国密算法（例如：使用 gmssl 库）。

实现通过环境变量加载密钥的机制。

编写密钥加载函数，优先从环境变量读取密钥值或密钥文件路径。

实现与 KMS (Key Management System) 的集成接口（例如：HashiCorp Vault, AWS KMS）。

设计 KMS 抽象接口，允许插拔不同的 KMS 实现。

实现至少一个主流 KMS 的具体集成（例如：使用 hvac 库集成 HashiCorp Vault）。

实现 phoenix crypto ... 命令。

编写 CLI 命令，提供密钥生成、文本加密、文本解密等辅助功能。

提供 .env.example 安全配置模板。

创建示例文件，指导用户通过环境变量配置密钥路径或 KMS 地址，避免硬编码。

OCR 识别

集成 pytesseract 和 OpenCV。

安装 pytesseract 和 opencv-python 库。

确保 Tesseract-OCR 引擎已安装并可调用。

实现 OCR 识别工具类。

封装图像预处理（例如：灰度化、二值化）功能。

封装文字识别和结果解析功能。

性能测试集成

集成 Locust。

编写 Locust 脚本的示例，演示如何定义用户行为和任务。

提供 Locust 测试脚本的编写规范和集成示例。

编写文档，指导用户如何编写和运行 Locust 脚本。

提供与 PhoenixFrame 报告（例如：Allure）集成的初步方案，将性能测试结果链接到报告。

安全测试集成

集成 ZAP API Client。

编写 Python 脚本，通过 ZAP API Client 触发 DAST (动态应用安全测试) 扫描。

集成 Bandit。

配置 Bandit 静态代码分析工具，定义扫描规则。

提供基础的 DAST 和 SAST 扫描能力。

在 CLI 中添加触发 ZAP 和 Bandit 扫描的命令或选项。

将扫描结果集成到报告或日志中，并提供安全风险等级评估。

CLI 诊断与环境管理

实现 phoenix doctor 命令，检查环境配置、依赖、驱动版本。

编写系统检查逻辑，验证 Python 版本、依赖库安装、WebDriver 路径、环境变量等。

输出详细的诊断报告，指出潜在问题和解决方案。

实现 phoenix env list 命令，列出 phoenix.yaml 中已配置的环境。

解析 phoenix.yaml 中的环境配置部分。

格式化输出环境列表，包括环境名称、基础 URL 等关键信息。

阶段四：测试资产代码化引擎 (Test Asset Codification Engine)
此阶段专注于 v3.2 的核心创新点，将外部资产转换为可维护的测试代码。此阶段可与阶段三并行开发，但需依赖阶段一和阶段二提供的核心框架能力。

引擎核心

设计并实现引擎的通用解析层。

定义输入资产的通用接口（例如：AssetParser）。

实现不同资产类型（Playwright Codegen, HAR, OpenAPI）的分发逻辑。

设计并实现 AST (抽象语法树) 生成的统一模型。

定义一个中间表示 (IR) 来统一表示 UI 交互、API 请求、断言等。

实现从不同解析器到 IR 的转换逻辑。

设计并实现代码写入层，遵循 PhoenixFrame 最佳实践。

使用模板引擎（例如：Jinja2）生成 Python 代码文件。

确保生成的代码符合 POM、数据驱动、Fixture 使用等框架规范。

Playwright Codegen 脚本转换

实现 Playwright 原始 Python 脚本的解析器。

使用 Python 内置的 ast 模块解析 codegen 脚本的抽象语法树。

实现智能分析逻辑，识别页面交互和数据。

遍历 AST，识别 page.locator(...), element.click(), element.fill(...) 等方法调用。

提取定位器字符串、操作类型和相关数据。

实现 POM 映射和元素占位符生成。

实现定位器字符串到 Page Object 元素名的映射规则（例如：通过哈希或正则匹配）。

如果元素不存在，生成新的 Page Object 元素定义占位符。

实现硬编码数据提取到 YAML 数据文件。

识别脚本中的硬编码字符串（例如：用户名、密码、搜索词）。

将这些字符串提取到独立的 YAML 数据文件中，并在生成的代码中替换为数据引用。

实现代码重构为 POM 模式的 pytest 函数。

根据 AST 分析结果和 POM 映射，生成调用 Page Object 方法的 pytest 测试函数。

确保生成的代码可读、可维护。

HAR (HTTP Archive) 文件转换

实现 .har 文件的解析器。

使用 json 模块解析 HAR 文件内容。

遍历 log.entries 数组，提取每个 HTTP 请求和响应的详细信息。

实现 HTTP 请求条目到 APIClient 调用的转换。

从 HAR entry 提取 method, url, headers, queryString, postData 等信息。

生成对应的 APIClient 调用代码，自动填充参数。

实现基础断言（状态码、Content-Type）的生成。

从 HAR entry 的 response 中提取状态码和 Content-Type。

生成 response.assert_status_code(...) 和 response.assert_header('Content-Type', ...) 等基础断言。

实现高级依赖关系识别和变量关联。

分析连续请求中的数据流（例如：一个请求的响应体中的 ID 作为下一个请求的路径参数或请求体）。

生成变量提取 (extract) 和使用 (${variable}) 的代码，实现请求间的依赖传递。

Postman / OpenAPI (Swagger) 定义转换

实现 Postman Collection JSON 或 OpenAPI YAML/JSON 文件的解析器。

使用 json 或 PyYAML 解析文件，并理解 Postman Collection 或 OpenAPI 规范结构。

实现端点和方法的遍历。

遍历 API 定义中的所有路径 (path) 和方法 (method)。

实现带类型提示的 APIClient 客户端函数生成。

根据 API 路径和方法名生成 Python 函数签名。

根据请求参数和响应结构生成类型提示（使用 Python typing 模块和 Pydantic 模型）。

实现基础测试用例骨架（成功、认证失败、无效参数）的生成。

为每个 API 端点生成至少三个基础测试函数，覆盖常见场景。

填充占位符断言和注释，指导用户完善测试逻辑。

实现 JSON Schema 到 Pydantic 数据模型的生成。

解析 OpenAPI 定义中的 components/schemas 部分。

生成对应的 Pydantic 模型类，用于请求和响应的类型校验。

CLI generate 命令集成

实现 phoenix generate --from <type> <source_file> 命令，调用对应的转换器。

编写 generate 命令的 Click/Typer 实现。

根据 --from 参数（playwright-codegen, har, openapi）调用不同的测试资产代码化转换逻辑。

阶段五：CI/CD 深度集成与未来展望 (CI/CD & Future Roadmap)
此阶段专注于框架在 CI/CD 流程中的应用和未来能力的探索。

CI/CD 深度集成

提供质量门禁的示例流水线逻辑（测试覆盖率、漏洞扫描、性能阈值）。

编写 GitHub Actions 或 Jenkinsfile 示例，演示如何配置质量门禁。

集成 pytest-cov 生成测试覆盖率报告，并设置阈值。

集成 Bandit 扫描结果，并设置高危漏洞阈值。

集成 Locust 性能报告阈值检查（例如：P95 响应时间）。

提供动态环境管理与 Docker/Kubernetes 结合的示例。

编写 Dockerfile 和 Kubernetes YAML 示例，用于构建和部署测试环境。

演示如何在 CI/CD 流水线中动态创建和销毁测试环境。

实现不稳定 (Flaky) 测试的自动重试和标记机制。

配置 pytest-rerunfailures 或类似插件，实现测试失败自动重试。

实现将重试后成功但首次失败的测试标记为“不稳定”的逻辑。

将不稳定测试数据上报到度量系统，以便团队关注和治理。

移动端测试支持 (未来)

研究并集成 Appium，扩展框架至原生 App 和移动 Web。

评估 Appium 的集成方式，包括驱动初始化和会话管理。

设计 appium_page Fixture，提供移动端元素定位和交互能力。

编写基础的移动端页面对象和测试用例示例。

AI 辅助代码生成与维护 (未来)

研究智能重构建议机制。

探索代码变更检测技术（例如：AST 差异分析）。

研究 LLM (大型语言模型) 在分析代码变更并推荐 Page Object 或测试用例更新方面的应用。

研究失败原因智能分析机制。

收集失败测试的上下文数据，包括日志、Trace、堆栈信息、截图、视频。

研究 LLM 对这些数据进行分析，给出可能的根本原因猜测和修复建议。

研究测试数据智能生成机制。

探索基于 API Schema (例如：OpenAPI) 或数据模型生成测试数据的方法。

研究 LLM 在生成边界值、异常值、复杂结构化数据等测试数据中的应用。

开发者体验再升级 (未来)

规划并开发 VSCode 插件，提供配置语法高亮、自动补全、实时校验、变量跳转、图形化界面支持等。

定义插件的功能列表和用户故事。

研究 VSCode 插件开发技术栈（例如：TypeScript, Language Server Protocol）。

设计插件的架构和用户交互流程，提升开发效率。
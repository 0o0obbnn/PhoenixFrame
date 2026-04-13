PhoenixFrame Gemini CLI 开发项目规则
本规则文档旨在为 PhoenixFrame 项目的开发提供指导，特别针对在 Linux 环境下使用 uv 进行项目管理，并与 Gemini CLI 协作的场景。Gemini 将依据本规则理解项目结构、执行任务、生成代码及提供协助。

1. 项目结构与模块化 (Project Structure & Modularity)
项目将遵循以下核心目录结构和模块化原则：

根目录 (phoenix-frame/): 项目的顶层目录。

src/: 存放所有框架核心源代码。

phoenix/: 框架主包。

cli/: 命令行接口相关代码。

core/: 核心引擎、配置、生命周期钩子、插件系统等。

web/: Web 自动化相关模块 (Selenium, Playwright)。

api/: API 自动化相关模块 (APIClient, 声明式引擎)。

observability/: 日志、追踪、度量相关。

security/: 加密、密钥管理相关。

utils/: 通用工具类 (OCR 等)。

codegen/: 测试资产代码化引擎的核心逻辑。

__init__.py: 包初始化文件。

tests/: 存放所有测试用例。

ui/: Web UI 测试。

api/: API 测试 (编程式和声明式)。

bdd/: BDD Feature 文件和步骤定义。

configs/: 存放项目配置文件 (phoenix.yaml 等)。

data/: 存放测试数据文件 (YAML, JSON 等)。

docs/: 存放项目文档。

templates/: 存放代码生成器使用的模板文件。

pyproject.toml: uv 和 setuptools 项目配置。

README.md: 项目介绍。

.gitignore: Git 忽略文件配置。

模块化原则:

高内聚，低耦合: 每个模块应专注于单一职责，并尽可能减少与其他模块的直接依赖。

清晰的 API 边界: 模块间通过明确定义的公共 API 进行交互，隐藏内部实现细节。

可测试性: 所有模块都应易于进行单元测试和集成测试。

2. 依赖管理与环境 (Dependency Management & Environment)
项目使用 uv 进行依赖管理和虚拟环境创建。

Python 版本: 统一使用 Python 3.9+。

虚拟环境:

通过 uv venv 创建虚拟环境。

通过 uv pip install -e . 安装项目及其开发依赖。

依赖声明: 所有项目依赖和开发依赖均在 pyproject.toml 中声明。

环境激活: 在进行任何开发操作前，确保虚拟环境已激活 (source .venv/bin/activate)。

Gemini 指导:

安装依赖: 当需要安装新依赖时，请使用 uv pip install <package_name>。

更新依赖: 当需要更新依赖时，请使用 uv pip install --upgrade <package_name> 或 uv update。

环境信息: 在执行代码或测试前，请始终确认当前环境已激活，并已安装所有必要的依赖。如果遇到依赖问题，请尝试重新安装或更新。

3. 代码风格与质量 (Code Style & Quality)
遵循 Python 最佳实践和自动化工具进行代码质量管理。

PEP 8: 严格遵循 PEP 8 编码规范。

类型提示: 广泛使用 Python 类型提示 (typing)，提高代码可读性和可维护性。

Linting: 使用 ruff 进行代码风格检查和格式化。

Gemini 指导: 在生成或修改代码后，请运行 ruff check . 和 ruff format . 进行检查和格式化。

Docstrings: 所有模块、类、函数和复杂方法都应包含清晰的 Docstrings，解释其目的、参数、返回值和异常。

注释: 对于复杂逻辑或非显而易见的实现，添加行内注释。

4. 测试 (Testing)
项目采用 pytest 作为测试框架，并遵循一定的测试规范。

测试文件命名: 测试文件应以 test_ 开头 (例如：test_api_client.py)。

测试函数命名: 测试函数应以 test_ 开头 (例如：test_create_user_success)。

Fixtures: 广泛使用 pytest Fixtures 进行测试环境的准备和清理。

测试数据: 测试数据应与测试逻辑分离，优先使用 data/ 目录下的 YAML/JSON 文件。

报告: 使用 allure-pytest 生成详细的测试报告。

Gemini 指导:

运行所有测试: 使用 pytest 命令运行所有测试。

运行特定测试: 使用 pytest tests/api/test_user.py 或 pytest tests/ui/test_login.py::test_login_success 运行特定测试。

生成报告: 在测试运行后，使用 allure generate allure-results --clean -o allure-report 生成 Allure 报告，并使用 allure serve allure-report 查看。

编写测试: 在实现新功能时，请同时编写相应的单元测试和集成测试。

5. 测试驱动开发 (Test-Driven Development - TDD)
PhoenixFrame 项目将严格遵循测试驱动开发（TDD）的实践，以确保功能的准确性、代码质量和设计不偏离初衷。

核心原则: 先写测试，后写代码。 任何新功能或缺陷修复，都必须首先编写一个或多个失败的测试用例。

TDD 循环:

红 (Red): 编写一个针对新功能或缺陷的测试，运行它，并确认它失败。这个失败是预期的，因为它所对应的功能尚未实现。

绿 (Green): 编写最少量、最简单的代码，使刚刚失败的测试通过。此时，不追求代码的完美，只追求测试通过。

重构 (Refactor): 在所有测试都通过的前提下，优化代码结构、提高可读性、消除重复、改进设计。在重构的每一步后，都应再次运行所有测试，确保没有引入新的缺陷。

验收标准: 只有当所有相关测试（包括新编写的测试和现有回归测试）都通过时，该功能才被认为是完成的，并可以进行提交或集成。

Gemini 指导:

任务开始: 在您请求开始任何功能开发任务时，Gemini 将首先要求您提供或生成相应的失败测试用例。

代码生成: Gemini 将在确保测试失败后，为您生成最少量的代码以使测试通过。

测试验证: 在生成代码后，Gemini 将提示您运行测试并验证其通过。

重构建议: 在测试通过后，Gemini 将根据需要提供代码重构的建议，并协助您进行重构，同时确保测试持续通过。

功能准确性: Gemini 将始终以测试通过作为功能准确性的唯一基准。

6. CLI 使用 (CLI Usage)
开发过程中将频繁使用 phoenix 命令行工具。

phoenix init <project_name>: 初始化新项目。

phoenix run [options]: 运行测试。

phoenix report: 查看测试报告。

phoenix crypto ...: 调用加密工具。

phoenix scaffold --type <type> --name <name>: 生成代码模板。

phoenix generate --from <type> <source_file>: 调用测试资产代码化引擎。

phoenix doctor: 检查环境配置。

phoenix env list: 列出环境配置。

Gemini 指导: 请熟悉并优先使用这些 CLI 命令来执行开发任务，例如生成模板、运行测试或检查环境。

7. Git 工作流 (Git Workflow)
项目将采用基于特性分支的 Git 工作流。

主分支: main 分支为稳定版本，所有开发都在特性分支上进行。

特性分支: 从 main 分支创建新的特性分支 (例如：feat/add-api-codegen, bugfix/fix-login-bug)。

提交信息: 提交信息应清晰、简洁，遵循 Conventional Commits 规范 (例如：feat: add new user registration API test)。

Pull Request (PR): 完成特性开发后，提交 PR 到 main 分支，并请求代码审查。

Gemini 指导: 在进行代码修改前，请确保您在正确的分支上。提交代码时，请提供清晰的提交信息。

8. Gemini CLI 交互指南 (Gemini CLI Interaction Guidelines)
为了确保 Gemini 能够高效地协助开发，请遵循以下指南：

明确任务: 每次请求都应包含明确的任务描述和预期输出。例如：“请实现 phoenix/core/config.py 中的 load_config 函数，它应该能够从 phoenix.yaml 加载配置并使用 Pydantic 进行校验。”

提供上下文: 在需要修改现有代码时，请提供相关的代码片段或文件路径，以便 Gemini 理解上下文。

逐步进行: 对于复杂的功能，请将其分解为更小的、可管理的子任务，并逐步请求 Gemini 完成。

反馈与迭代: 如果 Gemini 生成的代码不符合预期，请提供具体的反馈，并请求迭代修改。

文件路径: 在提及文件时，请使用相对于项目根目录的完整路径（例如：src/phoenix/core/config.py）。

依赖库: 在需要使用新的第三方库时，请告知 Gemini，并说明其用途，以便 Gemini 能够将其添加到 pyproject.toml 中。

测试验证: 在功能实现后，请明确要求 Gemini 生成或运行相应的测试用例进行验证。

问题诊断: 当遇到错误或异常时，请提供完整的错误信息和堆栈跟踪，以便 Gemini 进行诊断和修复。

本规则文档将作为 PhoenixFrame 项目开发过程中的核心参考，旨在提高开发效率、确保代码质量并促进与 Gemini CLI 的有效协作。
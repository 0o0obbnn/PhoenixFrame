# PhoenixFrame - 项目开发规则书

**版本:** 1.0
**日期:** 2023年10月29日

## 1. 宗旨 (Purpose)

本规则书旨在为 PhoenixFrame 项目的所有贡献者（包括人类工程师与 Gemini CLI 等 AI 工程师）提供一套统一、明确、可执行的开发标准。遵守本规则将最大限度地保证代码质量、提升协作效率、降低维护成本。

**所有开发活动，无一例外，均需严格遵守此规则。**

---

## 2. 环境搭建与管理 (Environment Setup)

项目使用 `uv` 进行虚拟环境和依赖包管理，它提供了极高的性能和统一的体验。

#### 2.1. 首次设置

1.  **确认 `uv` 已安装**：
    ```bash
    uv --version
    ```

2.  **创建虚拟环境**：在项目根目录执行。所有开发活动必须在虚拟环境中进行。
    ```bash
    # 这会在项目根目录创建一个 .venv 文件夹
    uv venv
    ```

3.  **激活虚拟环境**：
    -   **Windows (CMD/PowerShell):**
        ```bash
        .venv\Scripts\activate
        ```
    -   **Linux/macOS (Bash/Zsh):**
        ```bash
        source .venv/bin/activate
        ```
    激活后，你的终端提示符前应出现 `(.venv)`。

4.  **同步依赖**：使用 `pyproject.toml` 文件安装所有项目依赖。
    ```bash
    # 该命令会安装所有主要依赖和开发依赖
    uv pip sync pyproject.toml
    ```

#### 2.2. 日常开发

每次开始工作前，务必先执行 `source .venv/bin/activate` (或 Windows 等效命令) 激活虚拟环境。

---

## 3. 依赖管理 (Dependency Management)

**单一可信源**: `pyproject.toml` 是项目依赖的唯一、最终的定义文件。严禁使用 `requirements.txt` 等其他文件管理依赖。

#### 3.1. 添加新依赖

-   **添加生产依赖** (如 `requests`, `pydantic`):
    ```bash
    uv pip install <package-name>
    ```
    *示例: `uv pip install httpx`*

-   **添加开发依赖** (仅用于测试、linting 等，如 `pytest-mock`):
    ```bash
    uv pip install --dev <package-name>
    ```
    *示例: `uv pip install pytest-mock`*

#### 3.2. 移除依赖

```bash
uv pip uninstall <package-name>
```

#### 3.3. 更新依赖

- **更新单个包**: 
  ```bash
  uv pip install --upgrade <package-name>
  ```
- **更新所有包**: 谨慎操作。建议逐个更新关键包，并充分测试。

**黄金规则**: 任何通过 `uv pip install/uninstall` 对 `pyproject.toml` 的修改，都应立即提交到版本控制。

---

## 4. 代码规范 (Coding Style)

我们使用 `ruff` 作为统一的 Linter 和 Formatter，以保证代码风格的一致性。

#### 4.1. 格式化 (Formatting)

- **规则**: 所有提交的代码**必须**使用 `ruff format` 进行格式化。
- **执行**: 在提交代码前，运行以下命令：
  ```bash
  ruff format .
  ```

#### 4.2. 代码检查 (Linting)

- **规则**: 所有提交的代码**必须**通过 `ruff check` 且无任何错误。
- **执行**: 在提交代码前，运行以下命令：
  ```bash
  ruff check .
  ```
- **自动修复**: `ruff` 可以自动修复大量常见问题：
  ```bash
  ruff check . --fix
  ```

#### 4.3. 命名约定 (Naming Conventions)

- **变量/函数/方法**: `snake_case` (小写蛇形), e.g., `user_name`, `calculate_total()`.
- **类 (Class)**: `PascalCase` (驼峰式), e.g., `class TestAssetCodificationEngine:`.
- **常量 (Constant)**: `UPPER_SNAKE_CASE` (大写蛇形), e.g., `DEFAULT_TIMEOUT = 30`.
- **模块/包**: `snake_case` (小写蛇形), e.g., `har_parser.py`.

#### 4.4. 类型提示 (Type Hinting)

- **规则**: 所有函数和方法的签名**必须**包含类型提示。对于复杂的变量，也推荐使用类型提示。
- **示例**:
  ```python
  from typing import List

  def process_users(user_ids: List[int]) -> bool:
      # ... function body ...
      return True
  ```

---

## 5. 版本控制 (Git)

#### 5.1. 分支模型 (Branching Model)

我们采用基于 **Feature Branch** 的工作流。

-   `main`: 永远是可发布、生产就绪的代码。**禁止直接向 `main` 提交代码**。合并只能通过 Pull Request (PR) 进行。
-   `develop`: 主要开发分支，集成了所有已完成的功能。是创建新分支的基础。
-   `feat/<feature-name>`: 用于开发新功能。e.g., `feat/har-parser`.
-   `fix/<bug-name>`: 用于修复 Bug。e.g., `fix/cli-doctor-path-issue`.

**开发流程**:

1.  切换到 `develop` 分支并拉取最新代码: `git checkout develop && git pull`
2.  创建你的功能/修复分支: `git checkout -b feat/your-feature-name`
3.  完成开发和测试。
4.  提交代码 (见 5.2)，推送到远程: `git push -u origin feat/your-feature-name`
5.  创建 Pull Request 到 `develop` 分支。

#### 5.2. 提交信息规范 (Commit Message Convention)

所有提交信息**必须**遵循 **Conventional Commits** 规范。这有助于自动化生成 CHANGELOG 和版本管理。

**格式**:
```
<type>: <subject>

[optional body]

[optional footer]
```

-   **`<type>`** 必须是以下之一:
    -   `feat`: 新功能
    -   `fix`: Bug 修复
    -   `docs`: 文档变更
    -   `style`: 代码风格调整 (不影响逻辑)
    -   `refactor`: 代码重构
    -   `test`: 添加或修改测试
    -   `chore`: 构建过程或辅助工具的变动

-   **示例**:
    ```
    feat: add HAR parser to codegen engine

    Implement the initial version of HARParser that can read a .har file
    and extract a list of HTTP request entries. Basic validation is included.
    ```

---

## 6. 测试 (Testing)

- **框架**: 使用 `pytest`。
- **位置**: 所有测试代码必须放在 `tests/` 目录下，并尽可能模仿 `src/` 的目录结构。
- **命名**: 测试文件必须以 `test_*.py` 命名，测试函数必须以 `test_*` 开头。
- **核心原则**: 任何 `feat` 或 `fix` 类型的提交，**必须**包含相应的单元测试或集成测试。
- **运行测试**:
  ```bash
  # 运行所有测试
  pytest

  # 运行并生成覆盖率报告
  pytest --cov=src/phoenixframe
  ```

---

## 7. 文档 (Documentation)

- **Docstrings**: 所有公共的模块、类、函数和方法**必须**有符合 **Google Python Style** 的 Docstring。
- **项目文档**: 核心设计和用户指南应在 `docs/` 目录下以 Markdown 格式维护。

---

## 8. 附录：速查手册 (Cheat Sheet)

| 任务 | 命令 |
| :--- | :--- |
| **创建并激活环境** | `uv venv && source .venv/bin/activate` |
| **安装所有依赖** | `uv pip sync pyproject.toml` |
| **添加新依赖** | `uv pip install <package-name>` |
| **格式化代码** | `ruff format .` |
| **检查并修复代码** | `ruff check . --fix` |
| **运行所有测试** | `pytest` |
| **运行测试并看覆盖率**| `pytest --cov=src/phoenixframe` |

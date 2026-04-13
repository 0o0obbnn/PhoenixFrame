# PhoenixFrame

[![Version](https://img.shields.io/badge/version-3.2.0-blue.svg)](https://github.com/phoenixframe/phoenixframe)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-76%25-yellow.svg)](tests/)

**An enterprise-grade test automation framework with POM+Workflow architecture**

PhoenixFrame is a comprehensive Python-based test automation solution designed for enterprise applications. It combines Page Object Model (POM) with Workflow patterns to provide unified testing capabilities across Web UI, API, Performance, and Security testing.

## 🚀 Quick Start

### Installation

```bash
# Install using uv (recommended)
pip install uv
git clone https://github.com/phoenixframe/phoenixframe.git
cd PhoenixFrame
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip sync pyproject.toml
```

### 5-Minute Tutorial

1. **Initialize a new project**:
   ```bash
   phoenix init my-test-project
   cd my-test-project
   ```

2. **Generate test code from HAR file**:
   ```bash
   phoenix generate har network-traffic.har --output api_tests.py
   ```

3. **Create a page object**:
   ```bash
   phoenix scaffold page LoginPage --base-url https://example.com/login
   ```

4. **Run tests**:
   ```bash
   phoenix run tests/ --env dev
   ```

5. **Generate report**:
   ```bash
   phoenix report
   ```

## ✨ Key Features

### 🔧 Test Asset Codification Engine (v3.2 Highlight)
Automatically generate high-quality, maintainable test code from:
- **HAR files**: Convert network traffic to API tests
- **OpenAPI/Swagger specs**: Generate comprehensive API test suites
- **Playwright scripts**: Transform recordings into POM-based tests

### 🎯 Unified Testing Framework
- **Web UI Testing**: Selenium & Playwright support with smart waiting strategies
- **API Testing**: Declarative YAML and programmatic Python approaches
- **Performance Testing**: Locust integration with automated reporting
- **Security Testing**: SAST, DAST, and dependency scanning

### 📊 Enterprise Observability
- **Distributed Tracing**: OpenTelemetry integration for full request tracking
- **Structured Logging**: JSON logs with test_run_id correlation
- **Metrics Collection**: Prometheus-compatible metrics export
- **Real-time Monitoring**: Built-in performance and health monitoring

### 📋 BDD Support
- **pytest-bdd Integration**: Full Behavior Driven Development support
- **Feature Management**: Automatic feature discovery and step generation
- **Step Libraries**: Comprehensive predefined step definitions

### 🛡️ Security First
- **SAST Scanning**: Bandit integration for static code analysis
- **DAST Testing**: OWASP ZAP integration for dynamic security testing
- **Dependency Scanning**: Safety integration for vulnerability detection
- **Data Masking**: GDPR/CCPA compliant data anonymization

### 📈 Data Management
- **Test Data Factories**: Builder pattern for flexible data generation
- **Version Control**: Git-like versioning for test datasets
- **Dependency Management**: Automatic resolution of data dependencies
- **Data Masking**: Field-level privacy protection

## 📚 Documentation

### Getting Started
- [Quick Start Guide](docs/quickstart.md) - 5-minute tutorial
- [Installation Guide](docs/installation.md) - Detailed setup instructions
- [Project Structure](docs/project-structure.md) - Understanding the framework

### Core Features
- [Web Automation](docs/web-automation.md) - Selenium & Playwright usage
- [API Testing](docs/api-testing.md) - Declarative and programmatic approaches
- [BDD Testing](docs/bdd-testing.md) - Behavior Driven Development
- [Performance Testing](docs/performance-testing.md) - Locust integration
- [Security Testing](docs/security-testing.md) - SAST, DAST, and scanning

### Advanced Topics
- [Observability](docs/observability.md) - Logging, tracing, and metrics
- [Data Management](docs/data-management.md) - Test data lifecycle
- [Code Generation](docs/codegen.md) - Asset codification engine
- [CLI Reference](docs/cli-reference.md) - Complete command guide
- [Configuration](docs/configuration.md) - Environment and settings

### Developer Guide
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute
- [Development Setup](docs/development.md) - Setting up dev environment
- [Architecture Guide](docs/architecture.md) - Framework design principles
- [Plugin Development](docs/plugin-development.md) - Extending the framework

### Migration & Troubleshooting
- [Migration Guide](docs/migration.md) - Upgrading between versions
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions
- [FAQ](docs/faq.md) - Frequently asked questions
- [Best Practices](docs/best-practices.md) - Recommended patterns

## 🎯 CLI Commands

### Project Management
```bash
phoenix init <project-name>     # Initialize new project
phoenix doctor                  # Check environment health
phoenix env list               # List configured environments
```

### Code Generation
```bash
# From HAR files
phoenix generate har traffic.har --output api_tests.py

# From OpenAPI specifications
phoenix generate openapi api-spec.yaml --output api_skeleton.py

# From Playwright recordings
phoenix generate playwright-codegen script.py --output-pom page.py
```

### Scaffolding
```bash
phoenix scaffold page LoginPage --base-url https://app.example.com
phoenix scaffold api UserAPI --base-url https://api.example.com
phoenix scaffold test Calculator --test-type unit
phoenix scaffold feature "User Login" --scenarios "Success,Failure"
```

### Testing
```bash
phoenix run tests/ --env staging         # Run tests in specific environment
phoenix run tests/ -- -v -k "login"     # Pass pytest arguments
phoenix bdd run features/               # Run BDD tests
```

### Data Management
```bash
phoenix data dataset create users --data-type user --count 100
phoenix data dataset list              # List all datasets
phoenix data mask apply dataset_id --email --phone
phoenix data version commit dataset_id -m "Updated user data"
```

### Performance & Security
```bash
phoenix performance run --target-url https://api.example.com --users 50
phoenix security scan --sast --dast --dependency
```

### Observability
```bash
phoenix observability metrics --output metrics.json
```

## 🏗️ Architecture

PhoenixFrame follows the **POM+Workflow** architecture pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Interface                            │
├─────────────────────────────────────────────────────────────┤
│  Code Generation Engine  │  Scaffolding System             │
├──────────────┬──────────────┬───────────────┬──────────────┤
│  Web Testing │ API Testing  │ BDD Testing   │ Performance  │
├──────────────┼──────────────┼───────────────┼──────────────┤
│          Observability Stack (Logging, Tracing, Metrics)   │
├──────────────┼──────────────┼───────────────┼──────────────┤
│ Data Management  │ Security Testing │ Plugin System     │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

- **Core Framework**: Configuration, runners, lifecycle management
- **Testing Modules**: Web (Selenium/Playwright), API, BDD, Performance
- **Observability**: OpenTelemetry tracing, structured logging, metrics
- **Data Layer**: Factories, repositories, version control, masking
- **Security**: SAST, DAST, dependency scanning, encryption
- **CLI Tools**: Project management, code generation, scaffolding

## 📊 Current Status

| Module | Implementation | Tests | Documentation |
|--------|---------------|-------|---------------|
| Core Framework | ✅ 85% | ✅ 85% | ✅ 80% |
| Web Testing | 🟡 40% | ✅ 92% | 🟡 60% |
| API Testing | ✅ 70% | ✅ 88% | ✅ 70% |
| BDD Integration | 🟡 30% | ✅ 100% | 🟡 40% |
| Performance Testing | ✅ 60% | ✅ 85% | 🟡 55% |
| Security Testing | 🟡 20% | ✅ 80% | 🟡 45% |
| Data Management | ✅ 95% | ✅ 85% | ✅ 70% |
| CLI Tools | ✅ 90% | ✅ 80% | ✅ 80% |
| Observability | 🟡 40% | 🟡 65% | 🟡 50% |
| Code Generation | ✅ 80% | ✅ 95% | ✅ 85% |

**Overall Test Coverage**: 76.24% (35 test files covering 49 source files)

## 🎯 Roadmap

### v3.2.1 (Current - Q1 2024)
- [ ] Complete Web automation core features
- [ ] Enhance BDD implementation
- [ ] Improve CLI test coverage
- [ ] Add troubleshooting documentation

### v3.3.0 (Q2 2024)
- [ ] Enterprise observability features
- [ ] Advanced security scanning
- [ ] Plugin ecosystem
- [ ] Performance optimization

### v4.0.0 (Q3 2024)
- [ ] Multi-tenant support
- [ ] Cloud-native deployment
- [ ] Advanced AI-driven test generation
- [ ] Real-time collaboration features

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/phoenixframe/phoenixframe.git
cd PhoenixFrame
uv venv
source .venv/bin/activate
uv pip install -e ".[dev,test,all]"
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m "unit"
pytest -m "integration"
pytest -m "web"
```

## 📝 Examples

Check out the [examples](examples/) directory for:
- [Data Management Example](examples/data_management_example.py)
- [Performance Testing Example](examples/performance_test_example.py)
- [API Testing Workflows](examples/api_testing_examples/)
- [Web Automation Patterns](examples/web_automation_examples/)

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/phoenixframe/phoenixframe/issues)
- **Discussions**: [GitHub Discussions](https://github.com/phoenixframe/phoenixframe/discussions)
- **Wiki**: [Project Wiki](https://github.com/phoenixframe/phoenixframe/wiki)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Selenium](https://selenium.dev/) - Web automation foundation
- [Playwright](https://playwright.dev/) - Modern web testing
- [pytest](https://pytest.org/) - Testing framework
- [OpenTelemetry](https://opentelemetry.io/) - Observability standards
- [Locust](https://locust.io/) - Performance testing platform

---

**PhoenixFrame** - Empowering enterprise test automation with modern architecture and comprehensive tooling.

[🔝 Back to top](#phoenixframe)
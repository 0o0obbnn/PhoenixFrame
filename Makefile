# PhoenixFrame Makefile
# Enterprise-grade development workflow automation

.PHONY: help install install-dev install-all clean lint format type-check test test-unit test-integration test-e2e test-coverage security-check pre-commit build docs serve-docs release

# Default target
help:
	@echo "PhoenixFrame Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup Commands:"
	@echo "  install          Install basic dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  install-all      Install all optional dependencies"
	@echo "  setup-pre-commit Setup pre-commit hooks"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black and ruff"
	@echo "  type-check       Run type checking with mypy"
	@echo "  security-check   Run security scans"
	@echo "  pre-commit       Run all pre-commit checks"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-e2e         Run end-to-end tests only"
	@echo "  test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Build Commands:"
	@echo "  clean            Clean build artifacts"
	@echo "  build            Build package"
	@echo "  docs             Build documentation"
	@echo "  serve-docs       Serve documentation locally"
	@echo ""
	@echo "Release Commands:"
	@echo "  release          Create a new release"

# Installation commands
install:
	pip install -e .

install-dev:
	pip install -e ".[dev,test]"

install-all:
	pip install -e ".[all]"

setup-pre-commit:
	pre-commit install
	pre-commit install --hook-type commit-msg

# Code quality commands
lint:
	@echo "Running Ruff linting..."
	ruff check src/ tests/
	@echo "✅ Linting completed"

format:
	@echo "Formatting code with Black..."
	black src/ tests/
	@echo "Formatting code with Ruff..."
	ruff format src/ tests/
	@echo "✅ Code formatting completed"

type-check:
	@echo "Running MyPy type checking..."
	mypy src/phoenixframe --ignore-missing-imports
	@echo "✅ Type checking completed"

security-check:
	@echo "Running Bandit security scan..."
	bandit -r src/ -f json -o bandit-report.json || true
	@echo "Running Safety dependency check..."
	safety check --json --output safety-report.json || true
	@echo "✅ Security checks completed"

pre-commit:
	@echo "Running pre-commit checks..."
	pre-commit run --all-files
	@echo "✅ Pre-commit checks completed"

# Testing commands
test:
	@echo "Running all tests..."
	pytest tests/ -v
	@echo "✅ All tests completed"

test-unit:
	@echo "Running unit tests..."
	pytest tests/ -m "unit" -v
	@echo "✅ Unit tests completed"

test-integration:
	@echo "Running integration tests..."
	pytest tests/ -m "integration" -v
	@echo "✅ Integration tests completed"

test-e2e:
	@echo "Running end-to-end tests..."
	pytest tests/ -m "e2e" -v
	@echo "✅ End-to-end tests completed"

test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ \
		--cov=src/phoenixframe \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-report=xml \
		--cov-fail-under=80
	@echo "✅ Coverage report generated in htmlcov/"

test-parallel:
	@echo "Running tests in parallel..."
	pytest tests/ -n auto -v
	@echo "✅ Parallel tests completed"

# Build commands
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup completed"

build: clean
	@echo "Building package..."
	python -m build
	@echo "✅ Package built successfully"

# Documentation commands
docs:
	@echo "Building documentation..."
	mkdocs build
	@echo "✅ Documentation built in site/"

serve-docs:
	@echo "Serving documentation locally..."
	mkdocs serve

# Release commands
release: clean lint type-check test-coverage security-check build
	@echo "Creating release..."
	@echo "✅ Release package ready in dist/"
	@echo "Run 'twine upload dist/*' to publish to PyPI"

# Development workflow
dev-setup: install-dev setup-pre-commit
	@echo "✅ Development environment setup completed"

dev-check: lint type-check test-coverage
	@echo "✅ Development checks completed"

# CI simulation
ci: lint type-check test-coverage security-check build
	@echo "✅ CI pipeline simulation completed"

# Quick development cycle
quick: format lint test-unit
	@echo "✅ Quick development cycle completed"

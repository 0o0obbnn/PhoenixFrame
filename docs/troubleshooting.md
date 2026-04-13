# Troubleshooting Guide

This guide helps you resolve common issues when using PhoenixFrame. If you can't find a solution here, please check our [FAQ](faq.md) or [open an issue](https://github.com/phoenixframe/phoenixframe/issues).

## 🔍 Quick Diagnosis

### Health Check

Run the built-in health check to diagnose common issues:

```bash
phoenix doctor
```

This command will check:
- Python version compatibility
- Required dependencies
- Web driver availability
- Database connections
- Configuration validity

### Common Symptoms

| Symptom | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| Command not found | Installation issue | [Installation Problems](#installation-problems) |
| Import errors | Missing dependencies | [Dependency Issues](#dependency-issues) |
| Web tests failing | Driver problems | [Web Driver Issues](#web-driver-issues) |
| Slow test execution | Configuration issue | [Performance Problems](#performance-problems) |
| Permission errors | File system access | [Permission Issues](#permission-issues) |

---

## 📦 Installation Problems

### Python Version Compatibility

**Error**: `PhoenixFrame requires Python 3.9 or higher`

**Solutions**:
```bash
# Check Python version
python --version

# Install Python 3.9+ using pyenv
pyenv install 3.9.18
pyenv global 3.9.18

# Or use conda
conda install python=3.9
```

### Virtual Environment Issues

**Error**: `ModuleNotFoundError: No module named 'phoenixframe'`

**Solutions**:
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Or use uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Package Installation Failures

**Error**: `pip install failed with exit code 1`

**Solutions**:
```bash
# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Install with verbose output to see the error
pip install -e . -v

# For specific dependency conflicts
pip install --force-reinstall <package-name>

# Clear pip cache
pip cache purge
```

---

## 🔧 Dependency Issues

### Missing Optional Dependencies

**Error**: `ModuleNotFoundError: No module named 'selenium'`

**Solutions**:
```bash
# Install specific test type dependencies
pip install "phoenixframe[web]"      # For web testing
pip install "phoenixframe[api]"      # For API testing
pip install "phoenixframe[perf]"     # For performance testing
pip install "phoenixframe[security]" # For security testing
pip install "phoenixframe[all]"      # All dependencies

# Or install manually
pip install selenium playwright locust
```

### Conflicting Dependencies

**Error**: `ERROR: pip's dependency resolver does not currently have a necessary feature`

**Solutions**:
```bash
# Use dependency resolver
pip install --use-feature=2020-resolver

# Create fresh environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -e .

# Use uv for better dependency resolution
uv pip install -e .
```

### Version Conflicts

**Error**: `Conflicting dependencies: package A requires X>=2.0, package B requires X<2.0`

**Solutions**:
```bash
# Check dependency tree
pip show <package-name>
pip freeze | grep <package-name>

# Pin specific versions in requirements
echo "package-name==1.9.0" >> requirements.txt
pip install -r requirements.txt

# Use compatible versions
pip install "package-name>=1.8,<2.0"
```

---

## 🌐 Web Driver Issues

### Chrome Driver Problems

**Error**: `selenium.common.exceptions.WebDriverException: 'chromedriver' executable needs to be in PATH`

**Solutions**:
```bash
# Install ChromeDriver via WebDriver Manager (automatic)
pip install webdriver-manager

# Or download manually
# 1. Check Chrome version: chrome://version/
# 2. Download matching ChromeDriver: https://chromedriver.chromium.org/
# 3. Add to PATH or specify path in tests

# Using webdriver-manager in code
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver

driver = webdriver.Chrome(ChromeDriverManager().install())
```

### Firefox Driver Issues

**Error**: `selenium.common.exceptions.WebDriverException: 'geckodriver' executable needs to be in PATH`

**Solutions**:
```bash
# Install GeckoDriver via WebDriver Manager
pip install webdriver-manager

# Or install via package manager
# Ubuntu/Debian
sudo apt-get install firefox-geckodriver

# macOS
brew install geckodriver

# Windows
# Download from: https://github.com/mozilla/geckodriver/releases
```

### Playwright Issues

**Error**: `playwright._impl._api_types.Error: Executable doesn't exist`

**Solutions**:
```bash
# Install Playwright browsers
playwright install

# Install specific browsers
playwright install chromium
playwright install firefox
playwright install webkit

# Install with dependencies
playwright install --with-deps

# Check installation
playwright install --help
```

### Browser Version Compatibility

**Error**: `This version of ChromeDriver only supports Chrome version X`

**Solutions**:
```bash
# Update Chrome browser
# Then update ChromeDriver
pip install --upgrade webdriver-manager

# Or use Playwright (auto-manages browsers)
pip install playwright
playwright install

# Check browser versions
google-chrome --version
firefox --version
```

---

## 🚀 Performance Problems

### Slow Test Execution

**Symptoms**: Tests taking much longer than expected

**Solutions**:
```bash
# Enable headless mode
export PHOENIX_HEADLESS=true

# Reduce implicit waits
export PHOENIX_IMPLICIT_WAIT=5

# Use parallel execution
pytest -n auto  # Requires pytest-xdist

# Optimize wait strategies
# Use explicit waits instead of sleep()
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

wait = WebDriverWait(driver, 10)
element = wait.until(EC.element_to_be_clickable((By.ID, "submit")))
```

### Memory Issues

**Error**: `MemoryError` or `OutOfMemoryError`

**Solutions**:
```bash
# Increase memory limits
export PHOENIX_MAX_MEMORY=4096

# Close drivers properly
def teardown():
    driver.quit()  # Not just close()

# Use context managers
with SeleniumDriver() as driver:
    # Your test code here
    pass  # Driver automatically closed

# Monitor memory usage
import psutil
print(f"Memory usage: {psutil.virtual_memory().percent}%")
```

### Database Connection Issues

**Error**: `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) database is locked`

**Solutions**:
```bash
# Close connections properly
def teardown():
    db.close()
    db.dispose()

# Use connection pooling
from sqlalchemy import create_engine
engine = create_engine('sqlite:///test.db', pool_pre_ping=True)

# Check for hanging connections
lsof -p <process_id> | grep database.db
```

---

## 🔐 Permission Issues

### File System Access

**Error**: `PermissionError: [Errno 13] Permission denied`

**Solutions**:
```bash
# Check file permissions
ls -la /path/to/file

# Fix permissions
chmod 755 /path/to/directory
chmod 644 /path/to/file

# Run with elevated privileges (if necessary)
sudo python -m pytest  # Not recommended for regular use

# Use user-specific directories
import os
user_dir = os.path.expanduser("~/.phoenixframe")
os.makedirs(user_dir, exist_ok=True)
```

### Docker/Container Issues

**Error**: `Permission denied` when running in containers

**Solutions**:
```dockerfile
# In Dockerfile
RUN useradd -m -u 1000 testuser
USER testuser

# Or fix permissions
RUN chmod +x /usr/local/bin/phoenix
```

```bash
# When running Docker
docker run --user $(id -u):$(id -g) your-image

# For X11 forwarding (GUI tests)
docker run -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix your-image
```

---

## 📊 Test Execution Issues

### Test Discovery Problems

**Error**: `collected 0 items` or tests not found

**Solutions**:
```bash
# Check test discovery patterns
pytest --collect-only

# Verify test file naming
# Files must start with test_ or end with _test.py
mv mytest.py test_mytest.py

# Check test function naming
# Functions must start with test_
def test_my_function():
    pass

# Verify Python path
export PYTHONPATH=$PYTHONPATH:/path/to/project
```

### Configuration Issues

**Error**: `ConfigurationError: Invalid configuration`

**Solutions**:
```bash
# Validate configuration
phoenix config validate

# Check configuration location
phoenix config show

# Reset to defaults
phoenix config reset

# Common configuration file locations
~/.phoenixframe/config.yaml
./phoenixframe.yaml
./tests/config.yaml
```

### Environment Variable Issues

**Error**: Environment variables not loading

**Solutions**:
```bash
# Check environment files
ls -la .env*

# Load environment manually
export $(cat .env | xargs)

# Debug environment loading
python -c "import os; print(os.environ.get('PHOENIX_ENV', 'not set'))"

# Use dotenv in tests
pip install python-dotenv
from dotenv import load_dotenv
load_dotenv()
```

---

## 📋 BDD Testing Issues

### Feature File Problems

**Error**: `FeatureExecError: Unable to find step definition`

**Solutions**:
```bash
# Check step definitions location
# Default: tests/steps/
ls -la tests/steps/

# Verify step imports
# In conftest.py
pytest_plugins = ["pytest_bdd"]

# Check step patterns
from pytest_bdd import given, when, then

@given('I have a user')
def user_exists():
    pass
```

### Step Definition Issues

**Error**: `StepDefinitionNotFoundError`

**Solutions**:
```python
# Ensure step definitions are properly defined
from pytest_bdd import given, when, then, parsers

@given(parsers.parse('I have {count:d} items'))
def i_have_items(count):
    pass

# Check step discovery
pytest --collect-only -q tests/bdd/
```

---

## 🔄 API Testing Issues

### Connection Problems

**Error**: `requests.exceptions.ConnectionError`

**Solutions**:
```python
# Check network connectivity
import requests
try:
    response = requests.get('https://httpbin.org/get', timeout=5)
    print(f"Status: {response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"Connection error: {e}")

# Configure timeouts
session = requests.Session()
session.timeout = 30

# Use retry strategies
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)
```

### SSL Certificate Issues

**Error**: `requests.exceptions.SSLError`

**Solutions**:
```python
# Disable SSL verification (not recommended for production)
requests.get('https://example.com', verify=False)

# Use custom CA bundle
requests.get('https://example.com', verify='/path/to/ca-bundle.crt')

# Set environment variable
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
```

---

## 🎯 Data Management Issues

### Database Connection Problems

**Error**: `sqlalchemy.exc.OperationalError`

**Solutions**:
```python
# Check database URL format
# SQLite: sqlite:///path/to/database.db
# PostgreSQL: postgresql://user:password@host:port/database
# MySQL: mysql://user:password@host:port/database

# Test connection
from sqlalchemy import create_engine
engine = create_engine('sqlite:///test.db')
try:
    with engine.connect() as conn:
        result = conn.execute('SELECT 1')
        print("Connection successful")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Data Fixture Issues

**Error**: `FixtureNotFoundError`

**Solutions**:
```python
# Check fixture scope
@pytest.fixture(scope="session")
def database():
    # Setup
    yield db
    # Cleanup

# Verify fixture dependencies
@pytest.fixture
def user_data(database):
    return database.create_user()

# Check fixture location
# conftest.py files are auto-discovered
```

---

## 📈 Performance Testing Issues

### Locust Configuration

**Error**: `ModuleNotFoundError: No module named 'locust'`

**Solutions**:
```bash
# Install locust
pip install locust

# Or install with PhoenixFrame
pip install "phoenixframe[perf]"

# Verify installation
locust --version
```

### Performance Test Execution

**Error**: Tests not generating expected load

**Solutions**:
```python
# Check user configuration
class WebsiteUser(HttpUser):
    wait_time = between(1, 5)  # Wait between requests
    
    def on_start(self):
        # Setup code
        pass
    
    @task(3)  # Weight: 3 times more likely
    def view_item(self):
        pass
    
    @task(1)
    def purchase_item(self):
        pass
```

---

## 🛡️ Security Testing Issues

### SAST Tool Issues

**Error**: `bandit: command not found`

**Solutions**:
```bash
# Install bandit
pip install bandit

# Or with PhoenixFrame
pip install "phoenixframe[security]"

# Run security scan
bandit -r src/
```

### DAST Tool Issues

**Error**: OWASP ZAP not starting

**Solutions**:
```bash
# Install OWASP ZAP
# Download from: https://owasp.org/www-project-zap/

# Or use Docker
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://example.com

# Check ZAP configuration
export ZAP_HOME=/path/to/zap
```

---

## 🔍 Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# PhoenixFrame specific logging
from phoenixframe.observability.logger import setup_logging
setup_logging(level="DEBUG", enable_console=True)
```

### Use Interactive Debugging

```python
# Add breakpoints
import pdb; pdb.set_trace()

# Or use ipdb for better experience
import ipdb; ipdb.set_trace()

# In pytest
pytest --pdb  # Drop into debugger on failure
pytest --pdb-trace  # Drop into debugger on start
```

### Capture Screenshots on Failure

```python
def capture_screenshot_on_failure(request, driver):
    if request.node.rep_call.failed:
        screenshot_path = f"screenshots/{request.node.name}.png"
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")
```

---

## 🆘 Getting Help

### Before Asking for Help

1. ✅ Run `phoenix doctor` to check for common issues
2. ✅ Check this troubleshooting guide
3. ✅ Search existing [GitHub Issues](https://github.com/phoenixframe/phoenixframe/issues)
4. ✅ Review the [FAQ](faq.md)
5. ✅ Enable debug logging to get detailed error information

### Creating a Good Issue Report

When creating an issue, include:

```markdown
## Environment
- PhoenixFrame version: `phoenix --version`
- Python version: `python --version`
- OS: `uname -a` (Linux/macOS) or `systeminfo` (Windows)
- Browser versions (if applicable)

## Steps to Reproduce
1. Step one
2. Step two
3. Step three

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Error Messages
```
Full error traceback here
```

## Additional Context
- Configuration files
- Test code snippets
- Screenshots (if relevant)
```

### Support Channels

- **Documentation**: [docs/](.)
- **GitHub Issues**: [Bug reports and feature requests](https://github.com/phoenixframe/phoenixframe/issues)
- **GitHub Discussions**: [Community discussions](https://github.com/phoenixframe/phoenixframe/discussions)
- **Wiki**: [Community knowledge base](https://github.com/phoenixframe/phoenixframe/wiki)

---

## 🔄 Common Workflow Issues

### CI/CD Integration Problems

**Error**: Tests failing in CI but passing locally

**Solutions**:
```yaml
# GitHub Actions example
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -e .[test]
          playwright install --with-deps
      - name: Run tests
        run: |
          export PHOENIX_HEADLESS=true
          pytest -v
        env:
          PHOENIX_ENV: ci
```

### Docker Integration Issues

**Error**: GUI tests failing in Docker

**Solutions**:
```dockerfile
# Dockerfile for GUI tests
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    procps \
    libxss1 \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN echo "deb https://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
RUN apt-get update && apt-get install -y google-chrome-stable

# Install PhoenixFrame
COPY . /app
WORKDIR /app
RUN pip install -e .[all]

# Run tests
CMD ["pytest", "-v"]
```

---

Remember to always check the latest documentation and GitHub issues for the most up-to-date solutions to common problems.
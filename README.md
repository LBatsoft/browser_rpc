# Browser RPC

> High-performance browser automation RPC service based on Playwright + gRPC with powerful anti-detection capabilities

[![CI](https://github.com/LBatsoft/browser_rpc/actions/workflows/ci.yml/badge.svg)](https://github.com/LBatsoft/browser_rpc/actions/workflows/ci.yml)

## ✨ Features

- 🛡️ **Powerful Anti-Detection**: playwright-stealth + custom scripts to bypass common bot detection
- 🔌 **gRPC Interface**: 13 standardized APIs supporting remote calls
- 📡 **Network Interception**: Complete request/response capture capabilities
- 🚀 **High Performance**: Supports multi-session concurrency with resource pool management
- 🎨 **Easy to Use**: Clean Python client API

## 🚀 Quick Start

### One-Click Test (Recommended)

```bash
cd /path/to/browser_rpc
./scripts/quick_test.sh
```

This will automatically: install browser → start server → run tests → cleanup

## 📦 Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Compile Proto Files

```bash
python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/spider.proto
```

### 3. Install Browser (First Time)

```bash
playwright install chromium
```

## 💻 Usage

### Start Server

**gRPC Server:**
```bash
./scripts/start_rpc_server.sh
# or
python rpc_server.py
```

**HTTP Server:**
```bash
./scripts/start_http_server.sh
# or
python http_server.py
```

The HTTP server provides:
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **REST API**: http://localhost:8000/api/*

### Basic Example (gRPC)

```python
import asyncio
from rpc_client import BrowserRPCClient

async def main():
    client = BrowserRPCClient()
    await client.connect()
    
    # Create session
    await client.create_session(headless=True)
    
    # Navigate to page
    await client.navigate('https://www.example.com')
    
    # Get content
    html = await client.get_page_content()
    
    await client.close()

asyncio.run(main())
```

### Basic Example (HTTP)

```python
import asyncio
from http_client import BrowserHTTPClient

async def main():
    client = BrowserHTTPClient(base_url='http://localhost:8000')
    
    try:
        # Create session
        await client.create_session(headless=True)
        
        # Navigate to page
        await client.navigate('https://www.example.com')
        
        # Get content
        html = await client.get_page_content()
        
        # Take screenshot
        await client.take_screenshot(save_path='page.png', full_page=True)
        
    finally:
        await client.close()

asyncio.run(main())
```

### Advanced Example

```python
# Set headers
await client.set_headers({
    'Authorization': 'Bearer token'
})

# Set cookies
await client.set_cookies([{
    'name': 'session',
    'value': 'abc123',
    'domain': '.example.com'
}])

# Wait and click element
await client.wait_for_element('button#submit')
await client.click_element('button#submit')

# Type text
await client.type_text('input#username', 'myname')

# Take screenshot
await client.take_screenshot(save_path='page.png', full_page=True)

# Get network requests
requests = await client.get_network_requests(url_pattern=r'/api/')
for req in requests:
    print(f"{req['method']} {req['url']}")
    if req.get('response'):
        print(f"Response: {req['response']['body']}")
```

### HTTP API Endpoints

The HTTP server provides RESTful API endpoints:

- `POST /api/sessions` - Create browser session
- `DELETE /api/sessions/{session_id}` - Close session
- `POST /api/sessions/{session_id}/navigate` - Navigate to URL
- `POST /api/sessions/{session_id}/execute` - Execute JavaScript
- `GET /api/sessions/{session_id}/content` - Get page HTML
- `POST /api/sessions/{session_id}/network` - Get network requests
- `POST /api/sessions/{session_id}/wait` - Wait for element
- `POST /api/sessions/{session_id}/click` - Click element
- `POST /api/sessions/{session_id}/type` - Type text
- `POST /api/sessions/{session_id}/screenshot` - Take screenshot
- `POST /api/sessions/{session_id}/headers` - Set headers
- `POST /api/sessions/{session_id}/cookies` - Set cookies
- `GET /api/sessions/{session_id}/cookies` - Get cookies

Visit http://localhost:8000/docs for interactive API documentation.

## 📋 Available RPC APIs

| API | Description |
|-----|-------------|
| `CreateSession` | Create browser session |
| `CloseSession` | Close session |
| `Navigate` | Navigate to URL |
| `ExecuteScript` | Execute JavaScript |
| `GetPageContent` | Get page HTML |
| `GetNetworkRequests` | Get network requests |
| `WaitForElement` | Wait for element |
| `ClickElement` | Click element |
| `TypeText` | Type text |
| `TakeScreenshot` | Take screenshot |
| `SetHeaders` | Set request headers |
| `SetCookies` | Set cookies |
| `GetCookies` | Get cookies |

## 🛡️ Anti-Detection Capabilities

### Automatically Hidden Features

- ✅ `navigator.webdriver`
- ✅ `window.chrome` object
- ✅ `plugins` and `mimeTypes`
- ✅ Automation traces (`cdc_*` variables)
- ✅ WebGL fingerprint consistency
- ✅ Permission state simulation

## 🔧 Configuration

### Server Configuration (`config.py`)

```python
RPC_HOST = '0.0.0.0'          # Listen address
RPC_PORT = 50051              # Listen port
MAX_SESSIONS = 10             # Max sessions
SESSION_TIMEOUT = 3600        # Session timeout (seconds)
```

### Client Configuration

```python
# Connect to remote server
client = BrowserRPCClient(host='192.168.1.100', port=50051)
```

## 📊 Performance

- **Single session memory**: 100-200MB
- **Startup time**: 1-3 seconds
- **Default timeout**: 30 seconds
- **Max concurrency**: 10 sessions (configurable)

## 🗂️ Project Structure

```
browser_rpc/
├── proto/
│   └── spider.proto          # gRPC service definition
├── spider_pb2.py             # Generated protobuf code
├── spider_pb2_grpc.py        # Generated gRPC code
├── docs/                     # Documentation
│   ├── README_CN.md
│   ├── anti_detection_notes.md
│   └── startup_guide.md
├── resources/
│   ├── screenshots/          # Test screenshots
│   └── stealth/              # Stealth scripts
├── scripts/
│   ├── install.sh
│   ├── quick_test.sh
│   ├── start_rpc_server.sh
│   └── start_server.sh
├── cdp_client.py             # CDP client implementation
├── rpc_server.py             # gRPC server
├── rpc_client.py             # gRPC client wrapper
├── config.py                 # Configuration
└── requirements.txt          # Dependencies
```

## 🎯 Use Cases

- ✅ Scraping JavaScript-rendered pages
- ✅ Bypassing anti-bot detection
- ✅ Capturing AJAX/API request data
- ✅ Automated testing
- ✅ Page screenshot service
- ✅ Form auto-filling

## ⚠️ Troubleshooting

### Q: Connection refused error?
**A:** Server not started, run `./scripts/start_rpc_server.sh`

### Q: Browser not installed?
**A:** Run `playwright install chromium`

### Q: Port already in use?
**A:** `lsof -ti:50051 | xargs kill -9`

### Q: Module import error?
**A:** `pip install -r requirements.txt`

## 📚 Documentation

- **中文文档**: [docs/README_CN.md](docs/README_CN.md)
- **API Definition**: [proto/spider.proto](proto/spider.proto)
- **Startup Guide**: [docs/startup_guide.md](docs/startup_guide.md)
- **Anti-Detection Notes**: [docs/anti_detection_notes.md](docs/anti_detection_notes.md)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🔄 CI/CD

This project uses GitHub Actions for continuous integration and deployment:

- **CI Workflow** (`.github/workflows/ci.yml`):
  - Tests on Python 3.9, 3.10, and 3.11
  - Installs dependencies and Playwright browsers
  - Compiles Proto files
  - Verifies imports and code syntax
  - Tests server startup
  - Runs code linting (flake8, pylint)

- **CD Workflow** (`.github/workflows/cd.yml`):
  - Creates release archives for version tags
  - Optional GitHub Pages deployment (commented out by default, see workflow file for instructions)

The CI pipeline runs automatically on every push and pull request to the `master` branch.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

Before submitting, please ensure:
- Code passes all CI checks
- Follows the project's code style (configured in `.flake8`)
- Includes appropriate tests if applicable

---

**Version**: 1.0.0  
**Status**: ✅ Production Ready


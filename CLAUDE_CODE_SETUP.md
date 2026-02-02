# Running the Langfuse MCP Server for Claude Code

Complete guide to running the OpenTelemetry MCP server with Langfuse backend so Claude Code can query your tax agent traces.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Recommended)](#quick-start-recommended)
3. [Configuration Options](#configuration-options)
4. [Running the Server](#running-the-server)
5. [Verifying Claude Code Connection](#verifying-claude-code-connection)
6. [Example Usage](#example-usage)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

- ✅ Python 3.11+ installed
- ✅ UV package manager installed
- ✅ Langfuse account with credentials
- ✅ Claude Code installed
- ✅ Tax agent with Langfuse tracing enabled

### Verify Prerequisites

```bash
# Check Python version
python --version  # Should be 3.11+

# Check UV is installed
uv --version

# Check the MCP server code exists
ls /home/diego/Agents/opentelemetry-mcp-server

# Check Claude Code is installed
which claude  # or check your PATH
```

---

## Quick Start (Recommended)

### Step 1: Set Environment Variables

Create a `.env` file in the MCP server directory:

```bash
cd /home/diego/Agents/opentelemetry-mcp-server
```

Create `.env` file:
```bash
# Langfuse Configuration
BACKEND_TYPE=langfuse
BACKEND_URL=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-ffd60946-bab2-4ee6-a534-000e1bea79ef
LANGFUSE_SECRET_KEY=sk-lf-573ae3d4-bcb7-498e-8582-0e201e554c81
LOG_LEVEL=INFO
```

### Step 2: Verify Server Works

Test the server manually:

```bash
cd /home/diego/Agents/opentelemetry-mcp-server

# Load environment and run server
export $(cat .env | xargs)
uv run opentelemetry-mcp --help
```

Expected output:
```
Usage: opentelemetry-mcp [OPTIONS]

Options:
  --backend [jaeger|tempo|traceloop|langfuse]
  --url TEXT                      Backend URL
  ...
```

### Step 3: Configure Claude Code

**Option A: Using Claude Code CLI Configuration**

Create or edit `~/.claude/config.json` (Linux):

```json
{
  "mcpServers": {
    "langfuse-traces": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/diego/Agents/opentelemetry-mcp-server",
        "run",
        "opentelemetry-mcp"
      ],
      "env": {
        "BACKEND_TYPE": "langfuse",
        "BACKEND_URL": "https://cloud.langfuse.com",
        "LANGFUSE_PUBLIC_KEY": "pk-lf-ffd60946-bab2-4ee6-a534-000e1bea79ef",
        "LANGFUSE_SECRET_KEY": "sk-lf-573ae3d4-bcb7-498e-8582-0e201e554c81",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Option B: Using Environment Variables (Simpler)**

If your `.env` file is set up correctly, you can use a simpler config:

```json
{
  "mcpServers": {
    "langfuse-traces": {
      "command": "bash",
      "args": [
        "-c",
        "cd /home/diego/Agents/opentelemetry-mcp-server && export $(cat .env | xargs) && uv run opentelemetry-mcp"
      ]
    }
  }
}
```

### Step 4: Restart Claude Code

```bash
# Quit Claude Code completely
# Then restart it
claude
```

### Step 5: Verify Connection

In Claude Code, test the MCP server:

```
You: List all available MCP servers
Claude: [Should show "langfuse-traces"]

You: List all services in my traces
Claude: [Uses list_services tool]
      Found 4 services:
      - ChatFireworks.chat
      - http://127.0.0.1:8000/api/v1/calculations/history
      - http://127.0.0.1:8000/api/v1/documents
      - http://127.0.0.1:8000/api/v1/documents/
```

---

## Configuration Options

### Method 1: Claude Code Config File (Recommended)

**Location:** `~/.claude/config.json` (Linux/macOS)

**Advantages:**
- ✅ Persistent across sessions
- ✅ Auto-starts with Claude Code
- ✅ Clean separation of concerns

**Complete Config Example:**

```json
{
  "mcpServers": {
    "langfuse-traces": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/diego/Agents/opentelemetry-mcp-server",
        "run",
        "opentelemetry-mcp"
      ],
      "env": {
        "BACKEND_TYPE": "langfuse",
        "BACKEND_URL": "https://cloud.langfuse.com",
        "LANGFUSE_PUBLIC_KEY": "pk-lf-ffd60946-bab2-4ee6-a534-000e1bea79ef",
        "LANGFUSE_SECRET_KEY": "sk-lf-573ae3d4-bcb7-498e-8582-0e201e554c81"
      }
    }
  }
}
```

### Method 2: Environment Variables + .env File

**Best for:** Development and testing

**Step 1:** Create `.env` file in server directory:

```bash
cd /home/diego/Agents/opentelemetry-mcp-server

cat > .env << 'EOF'
BACKEND_TYPE=langfuse
BACKEND_URL=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-ffd60946-bab2-4ee6-a534-000e1bea79ef
LANGFUSE_SECRET_KEY=sk-lf-573ae3d4-bcb7-498e-8582-0e201e554c81
LOG_LEVEL=INFO
EOF
```

**Step 2:** Use simpler config:

```json
{
  "mcpServers": {
    "langfuse-traces": {
      "command": "bash",
      "args": [
        "-c",
        "cd /home/diego/Agents/opentelemetry-mcp-server && export $(cat .env | xargs) && uv run opentelemetry-mcp"
      ]
    }
  }
}
```

### Method 3: Direct CLI (For Testing)

**Best for:** Quick testing without config

```bash
cd /home/diego/Agents/opentelemetry-mcp-server

export BACKEND_TYPE=langfuse
export BACKEND_URL=https://cloud.langfuse.com
export LANGFUSE_PUBLIC_KEY=pk-lf-ffd60946-bab2-4ee6-a534-000e1bea79ef
export LANGFUSE_SECRET_KEY=sk-lf-573ae3d4-bcb7-498e-8582-0e201e554c81

uv run opentelemetry-mcp
```

---

## Running the Server

### Automatic Start (Recommended)

When configured in `~/.claude/config.json`, the server starts automatically when Claude Code starts.

**Verify it's running:**

```bash
# Check Claude Code logs
tail -f ~/.claude/logs/mcp*.log

# Or check for the process
ps aux | grep opentelemetry-mcp
```

### Manual Start (For Development)

**Option 1: Direct UV command**

```bash
cd /home/diego/Agents/opentelemetry-mcp-server
uv run opentelemetry-mcp
```

**Option 2: Loading from .env file**

```bash
cd /home/diego/Agents/opentelemetry-mcp-server
export $(cat .env | xargs)
uv run opentelemetry-mcp
```

**Option 3: With custom backend (overrides .env)**

```bash
cd /home/diego/Agents/opentelemetry-mcp-server
uv run opentelemetry-mcp --backend langfuse --url https://cloud.langfuse.com
```

### Running in Background

If you want to run the server independently:

```bash
cd /home/diego/Agents/opentelemetry-mcp-server

# Start in background with nohup
nohup uv run opentelemetry-mcp > mcp.log 2>&1 &

# Save the PID
echo $! > mcp.pid

# Check logs
tail -f mcp.log

# Stop later
kill $(cat mcp.pid)
```

---

## Verifying Claude Code Connection

### Step 1: Check MCP Server Status

In Claude Code:

```
You: What MCP servers are available?
```

Expected response:
```
I have access to the following MCP servers:
- langfuse-traces: OpenTelemetry trace query server with Langfuse backend
```

### Step 2: Test Basic Queries

**Test 1: List Services**

```
You: List all services available in my traces
```

Expected response:
```
Found 4 services:
1. ChatFireworks.chat
2. http://127.0.0.1:8000/api/v1/calculations/history
3. http://127.0.0.1:8000/api/v1/documents
4. http://127.0.0.1:8000/api/v1/documents/
```

**Test 2: Search Traces**

```
You: Show me the last 10 traces
```

Expected response:
```
Found [N] traces from the last 24 hours:
[Trace details...]
```

**Test 3: Get Specific Trace**

```
You: Get the details for trace [trace-id-from-above]
```

Expected response:
```
Trace Details:
- ID: [trace-id]
- Service: [service-name]
- Duration: [duration]ms
- Status: [status]
- Spans: [N] spans
```

### Step 3: Verify Tools Available

Check that Claude Code has access to all MCP tools:

```
You: What tools can you use to query traces?
```

Expected tools:
- `search_traces` - Search for traces with filters
- `get_trace` - Get specific trace details
- `list_services` - List available services
- `get_service_operations` - List operations for a service
- `search_spans` - Search individual spans
- `get_llm_usage` - Get token usage statistics
- `get_llm_expensive_traces` - Find traces with high token usage
- `get_llm_slow_traces` - Find slow traces
- `get_llm_model_stats` - Get model usage statistics

---

## Example Usage

### Debug Errors

```
You: Show me traces with errors from the last 24 hours
Claude: [Uses search_traces with has_error=true]
```

### Analyze Performance

```
You: Find the 10 slowest traces from yesterday
Claude: [Uses get_llm_slow_traces with time range]
```

### Track Costs

```
You: What's the total token usage for the ChatFireworks.chat service?
Claude: [Uses get_llm_usage with service filter]
```

### Explore Tax Agent

```
You: Show me all traces for the calculations service
Claude: [Uses search_traces with service_name filter]
```

### Deep Dive into Specific Trace

```
You: Get the full details for trace abc123, including all spans
Claude: [Uses get_trace to fetch complete trace data]
```

---

## Troubleshooting

### Problem: "MCP server not found"

**Symptoms:**
- Claude Code says "I don't have access to that MCP server"
- `langfuse-traces` not listed in available servers

**Solutions:**

1. **Check config file location:**
   ```bash
   # Verify config exists
   ls -la ~/.claude/config.json

   # Check syntax
   cat ~/.claude/config.json | python -m json.tool
   ```

2. **Verify server path:**
   ```bash
   # Check the directory exists
   ls -la /home/diego/Agents/opentelemetry-mcp-server

   # Verify UV can run it
   cd /home/diego/Agents/opentelemetry-mcp-server
   uv run opentelemetry-mcp --help
   ```

3. **Restart Claude Code:**
   ```bash
   # Fully quit Claude Code
   pkill claude

   # Start it again
   claude
   ```

### Problem: "Backend health check failed"

**Symptoms:**
- Server starts but can't connect to Langfuse
- Errors about authentication or network

**Solutions:**

1. **Verify credentials:**
   ```bash
   cd /home/diego/Agents/opentelemetry-mcp-server

   # Test credentials directly
   export LANGFUSE_PUBLIC_KEY="pk-lf-ffd60946-bab2-4ee6-a534-000e1bea79ef"
   export LANGFUSE_SECRET_KEY="sk-lf-573ae3d4-bcb7-498e-8582-0e201e554c81"

   uv run python -c "
   from langfuse import Langfuse
   client = Langfuse(
       public_key='pk-lf-ffd60946-bab2-4ee6-a534-000e1bea79ef',
       secret_key='sk-lf-573ae3d4-bcb7-498e-8582-0e201e554c81'
   )
   traces = client.trace.list(limit=1)
   print(f'Connected! Found {len(traces.data)} traces')
   "
   ```

2. **Check region URL:**
   - EU region: `https://cloud.langfuse.com`
   - US region: `https://us.cloud.langfuse.com`

3. **Test with the test script:**
   ```bash
   cd /home/diego/Agents/opentelemetry-mcp-server
   uv run python test_langfuse_backend.py
   ```

### Problem: "No traces returned"

**Symptoms:**
- Server connects successfully
- But search_traces returns 0 results

**Solutions:**

1. **Check if traces exist in Langfuse UI:**
   - Go to https://cloud.langfuse.com
   - Verify traces are visible
   - Check the time range

2. **Try broader time range:**
   ```
   You: Show me traces from the last 7 days
   ```

3. **Try without filters:**
   ```
   You: List all traces without any filters
   ```

### Problem: "Import errors"

**Symptoms:**
- Errors about missing modules
- `ModuleNotFoundError: No module named 'langfuse'`

**Solutions:**

```bash
cd /home/diego/Agents/opentelemetry-mcp-server

# Reinstall dependencies
uv sync

# Verify installation
uv run python -c "import langfuse; print(langfuse.__version__)"

# Run test
uv run python test_langfuse_backend.py
```

### Problem: "Permission denied"

**Symptoms:**
- Can't access config file
- Can't write to log files

**Solutions:**

```bash
# Fix permissions
chmod 600 ~/.claude/config.json
chmod 755 ~/.claude

# Or use sudo (not recommended)
sudo chown -R $USER:$USER ~/.claude
```

### Problem: Server already running

**Symptoms:**
- "Address already in use" error
- Can't start new server instance

**Solutions:**

```bash
# Find and kill existing process
ps aux | grep opentelemetry-mcp
kill [PID]

# Or use pkill
pkill -f opentelemetry-mcp

# Verify it's gone
ps aux | grep opentelemetry-mcp
```

---

## Advanced Configuration

### Using HTTP Transport (For Remote Access)

If you want to access traces from a remote machine:

```bash
cd /home/diego/Agents/opentelemetry-mcp-server

export $(cat .env | xargs)

# Start HTTP server on port 8000
uv run opentelemetry-mcp --transport http --port 8000
```

Then connect your MCP client to `http://localhost:8000/sse`.

### Custom Logging

Add to your `.env` file:

```bash
LOG_LEVEL=DEBUG  # Shows detailed API calls
```

Or to Claude Code config:

```json
{
  "env": {
    "LOG_LEVEL": "DEBUG"
  }
}
```

### Multiple Backend Configurations

You can run multiple MCP servers for different backends:

```json
{
  "mcpServers": {
    "langfuse-traces": {
      "command": "uv",
      "args": ["--directory", "/path/to/opentelemetry-mcp-server", "run", "opentelemetry-mcp"],
      "env": {
        "BACKEND_TYPE": "langfuse",
        "LANGFUSE_PUBLIC_KEY": "pk-lf-...",
        "LANGFUSE_SECRET_KEY": "sk-lf-..."
      }
    },
    "jaeger-traces": {
      "command": "uv",
      "args": ["--directory", "/path/to/opentelemetry-mcp-server", "run", "opentelemetry-mcp"],
      "env": {
        "BACKEND_TYPE": "jaeger",
        "BACKEND_URL": "http://localhost:16686"
      }
    }
  }
}
```

---

## Quick Reference Commands

```bash
# Test the backend
cd /home/diego/Agents/opentelemetry-mcp-server
uv run python test_langfuse_backend.py

# Start server manually
cd /home/diego/Agents/opentelemetry-mcp-server
export $(cat .env | xargs)
uv run opentelemetry-mcp

# Check if server is running
ps aux | grep opentelemetry-mcp

# View Claude Code logs
tail -f ~/.claude/logs/mcp*.log

# Restart Claude Code
pkill claude && claude

# Verify configuration
cat ~/.claude/config.json | python -m json.tool

# Test Langfuse connection
export LANGFUSE_PUBLIC_KEY="pk-lf-ffd60946-bab2-4ee6-a534-000e1bea79ef"
export LANGFUSE_SECRET_KEY="sk-lf-573ae3d4-bcb7-498e-8582-0e201e554c81"
cd /home/diego/Agents/opentelemetry-mcp-server
uv run python -c "from langfuse import Langfuse; print(Langfuse(public_key='pk-lf-ffd60946-bab2-4ee6-a534-000e1bea79ef', secret_key='sk-lf-573ae3d4-bcb7-498e-8582-0e201e554c81').trace.list(limit=1).data)"
```

---

## Next Steps

Once the server is running and verified:

1. **Explore your traces:** "Show me traces from the last hour"
2. **Debug issues:** "Find traces with errors"
3. **Optimize costs:** "What's the most expensive trace?"
4. **Monitor performance:** "Find the 10 slowest traces"

See `LANGFUSE_SETUP.md` for more example queries specific to your tax agent.

---

## Support

- **Repository:** https://github.com/DiegoNavarroNavas/opentelemetry-mcp-server
- **Issues:** https://github.com/DiegoNavarroNavas/opentelemetry-mcp-server/issues
- **Langfuse Docs:** https://langfuse.com/docs
- **MCP Spec:** https://modelcontextprotocol.io/

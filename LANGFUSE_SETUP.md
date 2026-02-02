# Langfuse MCP Server Setup Guide

This guide will help you configure the OpenTelemetry MCP server to query traces from your tax agent's Langfuse instance.

## Prerequisites

- ✅ Langfuse tracing already enabled in your tax agent
- ✅ Langfuse credentials available (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`)
- ✅ MCP server code cloned and dependencies installed

## Step 1: Get Your Langfuse Credentials

1. Go to [cloud.langfuse.com](https://cloud.langfuse.com) (or us.cloud.langfuse.com for US region)
2. Sign in to your account
3. Navigate to **Project Settings** → **API Keys**
4. Copy your **Public Key** (starts with `pk-lf-`)
5. Copy your **Secret Key** (starts with `sk-lf-`)

## Step 2: Configure Claude Desktop

### macOS

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

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
        "LANGFUSE_PUBLIC_KEY": "pk-lf-your-public-key",
        "LANGFUSE_SECRET_KEY": "sk-lf-your-secret-key"
      }
    }
  }
}
```

### Windows

Edit `%APPDATA%\Claude\claude_desktop_config.json` with the same configuration.

### Linux

Edit `~/.config/Claude/claude_desktop_config.json` with the same configuration.

## Step 3: Restart Claude Desktop

1. Completely quit Claude Desktop
2. Restart Claude Desktop
3. The MCP server will automatically start

## Step 4: Verify the Connection

In Claude Code or Claude Desktop, try these queries:

### List Available Services

```
You: "List all available services in my traces"
Claude: [Uses list_services tool] "Found services: coordinator, document-intelligence, tax-copilot, quality-loop"
```

### Search Recent Traces

```
You: "Show me the last 10 traces"
Claude: [Uses search_traces tool] "Found 10 traces from the last hour..."
```

### Get Specific Trace Details

```
You: "Get the details for trace [trace-id]"
Claude: [Uses get_trace tool] "Here are the full details for trace..."
```

### Find Errors

```
You: "Show me traces with errors from the last 24 hours"
Claude: [Uses search_traces with has_error filter] "Found 3 traces with errors..."
```

### Check Token Usage

```
You: "What's the token usage for the qwen2.5-72b model?"
Claude: [Uses get_llm_usage tool] "The qwen2.5-72b model used 15,234 tokens across 50 traces..."
```

## Step 5: Explore Your Tax Agent Traces

### Example Queries for Tax Agent Development

1. **Find slow tax calculations:**
   ```
   "Find the 10 slowest tax-calculation traces from yesterday"
   ```

2. **Analyze document extraction performance:**
   ```
   "Show me document-intelligence traces with duration over 5 seconds"
   ```

3. **Compare model costs:**
   ```
   "What's the total token usage for deepseek-v3p2 vs qwen3-vl?"
   ```

4. **Debug errors:**
   ```
   "Show me traces with status ERROR from the quality-loop service"
   ```

5. **Trace a specific user session:**
   ```
   "Find all traces for session_id [session-id]"
   ```

## Troubleshooting

### Claude doesn't recognize the MCP server

1. Check the config file path is correct for your OS
2. Verify JSON syntax is valid (no trailing commas)
3. Check Claude Desktop logs: `Help` → `Developer` → `Open Logs`
4. Ensure the path to opentelemetry-mcp-server is correct

### "Backend health check failed" error

1. Verify your Langfuse credentials are correct
2. Check the region URL (use `https://cloud.langfuse.com` for EU)
3. Test your credentials with the Langfuse SDK directly:
   ```bash
   cd /home/diego/Agents/opentelemetry-mcp-server
   uv run python -c "
   from langfuse import Langfuse
   client = Langfuse(
       public_key='pk-lf-your-key',
       secret_key='sk-lf-your-key'
   )
   print('Traces:', len(client.trace.list()))
   "
   ```

### No traces returned

1. Verify traces exist in Langfuse UI
2. Check the time range in your query (default is last 24 hours)
3. Try a broader query: "Show me all traces without filters"

### Import errors

1. Make sure dependencies are installed: `uv sync`
2. Check Python version is 3.11+
3. Verify langfuse package is installed: `uv run python -c "import langfuse; print(langfuse.__version__)"`

## Next Steps

Once the connection is working:

1. **Create custom queries:** Build queries specific to your tax agent workflow
2. **Set up monitoring:** Create dashboards for error rates, latency, token usage
3. **Cost optimization:** Identify expensive operations and optimize prompts
4. **Debug workflows:** Trace issues end-to-end through the agent system

## Advanced Configuration

### Using HTTP Transport (for Remote Access)

If you want to access traces from a remote machine:

```bash
cd /home/diego/Agents/opentelemetry-mcp-server

export BACKEND_TYPE=langfuse
export BACKEND_URL=https://cloud.langfuse.com
export LANGFUSE_PUBLIC_KEY=pk-lf-your-key
export LANGFUSE_SECRET_KEY=sk-lf-your-key

uv run opentelemetry-mcp --transport http --port 8000
```

Then connect to `http://localhost:8000/sse` from your MCP client.

### Environment Variables File

Instead of setting env vars in the config, create a `.env` file:

```bash
# .env in opentelemetry-mcp-server directory
BACKEND_TYPE=langfuse
BACKEND_URL=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-your-key
LANGFUSE_SECRET_KEY=sk-lf-your-key
LOG_LEVEL=DEBUG
```

Then update your Claude config to load this file:

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
      ]
    }
  }
}
```

The server will automatically load `.env` from the working directory.

## Support

- **Langfuse Docs:** https://langfuse.com/docs
- **MCP Server Repo:** https://github.com/DiegoNavarroNavas/opentelemetry-mcp-server
- **Issues:** https://github.com/DiegoNavarroNavas/opentelemetry-mcp-server/issues

# Abaqus MCP Bridge

An MCP server and Abaqus/CAE plugin that let MCP clients execute Abaqus Python
inside a running Abaqus/CAE session.

This project was tested with Abaqus/CAE 2023 on Windows. Abaqus 2023 uses an
older embedded Python runtime, so the bridge uses file-based IPC instead of
sockets.

## Architecture

```text
MCP client
  -> mcp_server.py
  -> ~/.abaqus-mcp/commands/cmd_<id>.json
  -> abaqus_mcp_plugin.py running inside Abaqus/CAE
  -> ~/.abaqus-mcp/results/<id>.json
  -> mcp_server.py
  -> MCP client
```

The external MCP server never imports `abaqus`. Abaqus APIs such as `mdb` and
`session` are only accessed from `abaqus_mcp_plugin.py`, which runs inside the
Abaqus/CAE kernel.

## Features

- Execute Abaqus Python scripts remotely
- Query models, parts, materials, steps, loads, boundary conditions, jobs, and viewports
- Submit existing Abaqus jobs and wait for completion
- Read ODB metadata
- Capture viewport images as base64 data URLs
- Stop/start the Abaqus-side polling loop with a menu or `stop.flag`

## Compatibility Notes

- Abaqus 2023: use `mcp_coop_loop()` or `mcp_loop()` for reliable command processing.
  Background threads may start but fail to consume commands in some sessions.
- Abaqus 2024/2025: background mode may be more reliable because the embedded
  Python runtime is newer, but still treat it as experimental until tested.
- This bridge controls a running Abaqus/CAE session. It is not a standalone
  replacement for Abaqus or the Abaqus kernel.

## Installation

Clone or copy this repository to the user's MCP home:

```powershell
git clone https://github.com/YOUR_NAME/abaqus-mcp.git "$env:USERPROFILE\.abaqus-mcp"
```

Install the MCP dependency for the external server:

```powershell
python -m pip install mcp
```

Optional but recommended: install the Abaqus GUI menu.

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\abaqus_plugins" | Out-Null
Copy-Item -Recurse -Force `
  "$env:USERPROFILE\.abaqus-mcp\abaqus_plugins\mcp_control" `
  "$env:USERPROFILE\abaqus_plugins\mcp_control"
```

## MCP Client Configuration

Example `.mcp.json`:

```json
{
  "mcpServers": {
    "abaqus-mcp-server": {
      "command": "python",
      "args": ["C:/Users/YourUsername/.abaqus-mcp/mcp_server.py"],
      "env": {
        "ABAQUS_MCP_HOME": "C:/Users/YourUsername/.abaqus-mcp"
      }
    }
  }
}
```

Use an absolute Python path if your MCP dependency is installed in a virtual
environment.

## Loading the Abaqus Plugin

### Option A: Abaqus startup argument

Start Abaqus/CAE with:

```powershell
abaqus cae startup="$env:USERPROFILE\.abaqus-mcp\start_mcp_in_cae.py"
```

On systems with release-specific commands, replace `abaqus` with `abq2023`,
`abq2025`, or the matching launcher command.

### Option B: Abaqus environment file

Copy the example environment file:

```powershell
Copy-Item "$env:USERPROFILE\.abaqus-mcp\abaqus_v6.env.example" "$env:USERPROFILE\abaqus_v6.env"
```

Then start Abaqus/CAE normally.

## Starting the Command Loop

After the plugin is loaded, start the polling loop from the Abaqus menu:

```text
Plug-ins -> MCP -> Start MCP (Cooperative)
```

For Abaqus 2023, Cooperative or Blocking mode is recommended. The GUI can appear
busy while the loop is running. This is expected: Abaqus is processing MCP
commands in the CAE process.

You can also run commands in the Abaqus Python console:

```python
mcp_coop_loop()   # reliable for Abaqus 2023, may keep the GUI busy
mcp_loop()        # blocking, most reliable
mcp_start()       # background thread, experimental
mcp_stop()        # stop from inside Abaqus
mcp_status()      # print plugin status
```

Stop the loop externally:

```powershell
python "$env:USERPROFILE\.abaqus-mcp\stop_mcp.py"
```

or create the stop flag manually:

```powershell
Set-Content "$env:USERPROFILE\.abaqus-mcp\stop.flag" "stop"
```

## Exposed MCP Tools

- `check_abaqus_connection`
- `ping`
- `execute_script`
- `get_model_info`
- `list_jobs`
- `submit_job`
- `get_odb_info`
- `get_viewport_image`

## Runtime Files

The bridge creates runtime files under `ABAQUS_MCP_HOME`:

```text
commands/
results/
scripts/
screenshots/
status.json
status.json.tmp
stop.flag
mcp.log
thread_error.log
startup_debug.log
```

These files are ignored by Git.

## Troubleshooting

If the client says the plugin is loaded but not responding:

1. In Abaqus/CAE, start `Plug-ins -> MCP -> Start MCP (Cooperative)`.
2. Check that `status.json` updates every few seconds.
3. Run `python stop_mcp.py`, then start the loop again.
4. For Abaqus 2023, avoid relying on background mode until you verify `ping`.

If commands time out, clear stale command/result files:

```powershell
Remove-Item "$env:USERPROFILE\.abaqus-mcp\commands\*.json" -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.abaqus-mcp\results\*.json" -ErrorAction SilentlyContinue
```

## License

MIT

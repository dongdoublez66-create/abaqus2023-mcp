# -*- coding: utf-8 -*-
"""Load the Abaqus MCP bridge from Abaqus/CAE startup=."""

import os
import traceback

mcp_home = os.environ.get('ABAQUS_MCP_HOME', os.path.expanduser('~/.abaqus-mcp'))
mcp_plugin = os.path.join(mcp_home, 'abaqus_mcp_plugin.py')
debug_log = os.path.join(mcp_home, 'startup_debug.log')

def log(message):
    try:
        with open(debug_log, 'a') as f:
            f.write(message + '\n')
    except Exception:
        pass

if os.path.exists(mcp_plugin):
    try:
        log('loading plugin: %s' % mcp_plugin)
        import __main__

        with open(mcp_plugin, 'r') as f:
            exec(f.read(), __main__.__dict__)

        log('plugin loaded; ready for MCP menu start')
        try:
            __main__.write_status('ready', 'Plugin loaded. Use Plug-ins -> MCP -> Start MCP (Cooperative or Blocking).')
        except Exception:
            pass
    except Exception as exc:
        msg = 'Abaqus MCP auto-start failed: %s' % exc
        print(msg)
        log(msg)
        log(traceback.format_exc())
else:
    print('Abaqus MCP plugin not found: %s' % mcp_plugin)
    log('plugin not found: %s' % mcp_plugin)

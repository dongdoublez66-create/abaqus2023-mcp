# Abaqus 2023 MCP Bridge for Codex

这是一个用于 **Codex + Abaqus/CAE 2023** 的 MCP 桥接项目。它可以让 Codex 通过 MCP 工具调用，在已经打开的 Abaqus/CAE 里执行 Abaqus Python，从而完成建模、查询模型、提交作业、读取 ODB、截图等操作。

> 说明：Abaqus 属于 SIMULIA/Dassault Systemes，不是 ANSYS。这个仓库名字里如果写 Ansys2023，只是沿用了本地目录习惯；实际接入对象是 Abaqus/CAE 2023。

## 这个 MCP 能做什么

- 让 Codex 在 Abaqus/CAE 内部执行 Python 脚本
- 查询当前模型、零件、材料、分析步、载荷、边界条件、装配实例
- 查询 Abaqus job，并提交已有 job
- 打开 ODB 文件并读取 step、frame、instance 等元信息
- 截取 Abaqus viewport 图片，返回 base64 图片数据
- 通过 `stop.flag` 从外部停止 Abaqus 侧轮询

## 为什么 2023 版需要这个桥

Codex 外部运行的是普通 Python/MCP server，不能直接：

```python
from abaqus import mdb, session
```

因为 `abaqus`、`mdb`、`session` 这些对象只存在于 Abaqus/CAE 自己的 Python kernel 里。

所以本项目采用 **文件 IPC**：

- Codex 调用 MCP 工具
- 外部 `mcp_server.py` 写入 JSON 命令文件
- Abaqus/CAE 内部插件 `abaqus_mcp_plugin.py` 轮询命令文件
- 插件在 Abaqus kernel 中执行命令
- 插件把结果写成 JSON 文件
- `mcp_server.py` 读取结果并返回给 Codex

这样不需要 socket，也不需要外部 Python 直接 import Abaqus API。对 Abaqus 2023 这种旧 Python 环境更稳。

## 完整通信流程

```text
Codex
  |
  | 1. 调用 MCP 工具，例如 execute_script
  v
mcp_server.py
  |
  | 2. 写入命令文件
  v
%USERPROFILE%\.abaqus-mcp\commands\cmd_<id>.json
  |
  | 3. Abaqus 插件轮询并读取命令
  v
abaqus_mcp_plugin.py 运行在 Abaqus/CAE kernel 内
  |
  | 4. 调用 Abaqus API，例如 mdb、session、openOdb
  v
Abaqus/CAE
  |
  | 5. 写入结果文件
  v
%USERPROFILE%\.abaqus-mcp\results\<id>.json
  |
  | 6. mcp_server.py 读取结果
  v
Codex 得到返回
```

核心目录：

```text
%USERPROFILE%\.abaqus-mcp\
  mcp_server.py                 外部 MCP server，给 Codex 调用
  abaqus_mcp_plugin.py          Abaqus 内部插件，真正调用 mdb/session
  start_mcp_in_cae.py           Abaqus 启动时加载插件的脚本
  stop_mcp.py                   外部停止轮询的小脚本
  abaqus_plugins\mcp_control\   Abaqus 菜单插件
  commands\                     MCP 命令文件
  results\                      MCP 结果文件
  status.json                   Abaqus 插件状态
  stop.flag                     停止信号
```

## 安装步骤

以下假设你使用 Windows，且想把项目放在：

```powershell
$env:USERPROFILE\.abaqus-mcp
```

### 1. 克隆仓库

```powershell
git clone https://github.com/dongdoublez66-create/abaqus2023-mcp.git "$env:USERPROFILE\.abaqus-mcp"
```

### 2. 安装外部 MCP server 依赖

推荐使用虚拟环境：

```powershell
cd "$env:USERPROFILE\.abaqus-mcp"
python -m venv "$env:USERPROFILE\.abaqus-mcp-venv"
& "$env:USERPROFILE\.abaqus-mcp-venv\Scripts\python.exe" -m pip install -r requirements.txt
```

也可以直接安装到系统 Python：

```powershell
python -m pip install -r requirements.txt
```

### 3. 安装 Abaqus 菜单插件

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\abaqus_plugins" | Out-Null
Copy-Item -Recurse -Force `
  "$env:USERPROFILE\.abaqus-mcp\abaqus_plugins\mcp_control" `
  "$env:USERPROFILE\abaqus_plugins\mcp_control"
```

安装后，Abaqus/CAE 菜单里会出现：

```text
Plug-ins -> MCP
```

## 在 Codex 里配置 MCP

Codex 的配置文件通常在：

```text
%USERPROFILE%\.codex\config.toml
```

加入类似配置。请把用户名和 Python 路径改成你自己的：

```toml
[mcp_servers.abaqus-mcp-server]
command = "C:\\Users\\YourUsername\\.abaqus-mcp-venv\\Scripts\\python.exe"
args = [ "C:\\Users\\YourUsername\\.abaqus-mcp\\mcp_server.py" ]

[mcp_servers.abaqus-mcp-server.env]
ABAQUS_MCP_HOME = "C:\\Users\\YourUsername\\.abaqus-mcp"
```

如果你没有用虚拟环境，也可以：

```toml
[mcp_servers.abaqus-mcp-server]
command = "python"
args = [ "C:\\Users\\YourUsername\\.abaqus-mcp\\mcp_server.py" ]

[mcp_servers.abaqus-mcp-server.env]
ABAQUS_MCP_HOME = "C:\\Users\\YourUsername\\.abaqus-mcp"
```

配置完成后，重启 Codex。Codex 应该能看到这些工具：

- `check_abaqus_connection`
- `ping`
- `execute_script`
- `get_model_info`
- `list_jobs`
- `submit_job`
- `get_odb_info`
- `get_viewport_image`

## 启动 Abaqus 并加载插件

### 方法 A：用 startup 参数启动

如果你的命令行里可以直接运行 Abaqus：

```powershell
abaqus cae startup="$env:USERPROFILE\.abaqus-mcp\start_mcp_in_cae.py"
```

如果你的版本命令是 `abq2023`：

```powershell
abq2023 cae startup="$env:USERPROFILE\.abaqus-mcp\start_mcp_in_cae.py"
```

如果你使用 SIMULIA 安装目录下的 launcher，也可以写一个 bat，例如：

```bat
@echo off
set "ABAQUS_MCP_HOME=C:\Users\YourUsername\.abaqus-mcp"
cd /d "E:\SIMULIA\EstProducts\2023\win_b64\resources\install\cmdDirFeature"
call "E:\SIMULIA\EstProducts\2023\win_b64\resources\install\cmdDirFeature\launcher.bat" cae startup="C:\Users\YourUsername\.abaqus-mcp\start_mcp_in_cae.py"
```

### 方法 B：用 abaqus_v6.env 自动加载

复制示例文件：

```powershell
Copy-Item "$env:USERPROFILE\.abaqus-mcp\abaqus_v6.env.example" "$env:USERPROFILE\abaqus_v6.env"
```

然后正常启动 Abaqus/CAE。

## 启动 MCP 监听

插件加载后，只是进入 `ready` 状态。要让 Codex 真正发命令给 Abaqus，需要启动 Abaqus 侧轮询。

在 Abaqus/CAE 顶部菜单点击：

```text
Plug-ins -> MCP -> Start MCP (Cooperative)
```

Abaqus 2023 推荐使用 `Cooperative` 或 `Blocking`：

| 模式 | 菜单 | 特点 |
| --- | --- | --- |
| Background | `Start MCP (Background, Experimental)` | 理论上不阻塞 GUI，但 Abaqus 2023 上可能启动了却不处理命令 |
| Cooperative | `Start MCP (Cooperative)` | Abaqus 2023 推荐；界面可能像卡住，但能处理 MCP 命令 |
| Blocking | `Start MCP (Blocking)` | 最稳；会阻塞当前 Abaqus Python 控制台 |

如果点 `Cooperative` 后 Abaqus 界面像卡住，不一定是错误。它正在主线程里轮询 MCP 命令。此时 Codex 可以正常控制 Abaqus。

## 在 Codex 里验证连接

启动 Abaqus 侧轮询后，在 Codex 中请求：

```text
检查 Abaqus MCP 是否连接
```

或让 Codex 调用：

```text
check_abaqus_connection
ping
```

正常结果类似：

```text
Connected to Abaqus MCP v4.0.0
ping: pong
```

也可以测试执行脚本：

```python
print(mdb.models.keys())
```

Codex 会通过 `execute_script` 把脚本发给 Abaqus 执行。

## 停止 MCP 监听

如果 Abaqus 界面被 Cooperative/Blocking 占住，可以从外部停止：

```powershell
python "$env:USERPROFILE\.abaqus-mcp\stop_mcp.py"
```

或者手动创建停止文件：

```powershell
Set-Content "$env:USERPROFILE\.abaqus-mcp\stop.flag" "stop"
```

Abaqus 插件轮询到 `stop.flag` 后会退出，界面恢复。

## Codex 可以让 Abaqus 做什么

配置成功后，你可以直接对 Codex 说：

```text
在 Abaqus 里新建一个 100x50x2 mm 的壳板模型，材料弹性模量 210000 MPa，泊松比 0.3，左端固定，右端施加 1 mm 位移，划分网格并提交作业。
```

Codex 会生成 Abaqus Python，并通过 MCP 发送给 Abaqus 执行。

你也可以说：

```text
打开这个 ODB，显示最大主应变云图并截图。
```

## 常见问题

### 1. Codex 显示插件不存在

说明 Abaqus 侧插件还没加载。检查：

- Abaqus/CAE 是否已经打开
- 是否用 `startup=...start_mcp_in_cae.py` 启动
- 或是否复制了 `abaqus_v6.env.example` 到 `%USERPROFILE%\abaqus_v6.env`

### 2. Codex 显示 loaded but not responding

说明插件加载了，但 Abaqus 侧轮询没启动，或 Background 模式没正常消费命令。

解决：

```text
Plug-ins -> MCP -> Start MCP (Cooperative)
```

然后再让 Codex 检查连接。

### 3. Abaqus 点 Cooperative 后卡住

这是 Abaqus 2023 下的正常现象。Cooperative 在 Abaqus 主线程里轮询命令，所以界面会忙。此时 Codex 仍可发送命令。

任务结束后用：

```powershell
python "$env:USERPROFILE\.abaqus-mcp\stop_mcp.py"
```

### 4. 命令超时

清理旧命令和结果：

```powershell
Remove-Item "$env:USERPROFILE\.abaqus-mcp\commands\*.json" -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.abaqus-mcp\results\*.json" -ErrorAction SilentlyContinue
```

然后重新启动 Abaqus 侧 MCP 轮询。

### 5. 2025 版能不能直接调用接口

Abaqus 2024/2025 的 Python 环境更新，Background 模式可能更稳定，但 Codex 仍然不能在外部普通 Python 中直接 `import abaqus` 控制已打开的 CAE。仍然需要：

- 在 Abaqus/CAE 内部加载插件
- 或用 `abaqus cae noGUI=script.py` 跑批处理脚本

本项目选择的是第一种：控制一个正在运行的 Abaqus/CAE 会话。

## 文件说明

```text
abaqus_mcp_plugin.py
  Abaqus 侧插件。运行在 Abaqus/CAE kernel 内，真正访问 mdb/session。

mcp_server.py
  外部 MCP server。Codex 调用它，它负责写 commands、读 results。

start_mcp_in_cae.py
  Abaqus 启动时加载插件的 startup 脚本。

stop_mcp.py
  外部停止脚本。创建 stop.flag，让 Abaqus 轮询退出。

abaqus_plugins/mcp_control/
  Abaqus GUI 菜单插件。提供 Start/Stop/Status 菜单。

abaqus_v6.env.example
  Abaqus 自动加载插件的环境文件示例。

requirements.txt
  外部 MCP server 的 Python 依赖。
```

## 运行时文件

这些文件会自动生成，不需要提交到 Git：

```text
commands/*.json
results/*.json
scripts/*.py
screenshots/*
status.json
status.json.tmp
stop.flag
mcp.log
thread_error.log
startup_debug.log
```

## License

MIT

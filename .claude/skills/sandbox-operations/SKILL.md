---
name: sandbox-operations
description: Daytonaサンドボックスの操作ベストプラクティス。シェル実行、ファイル操作、プレビューURL取得、エラーハンドリングのパターン集。
---

# Sandbox Operations Skill

Daytona SDKを使用したサンドボックス操作のベストプラクティス集。

---

## 1. サンドボックスの基本操作

### サンドボックスの取得と起動

```python
from daytona_sdk import AsyncDaytona, DaytonaConfig, SandboxState, AsyncSandbox
import asyncio

daytona_config = DaytonaConfig(
    api_key=DAYTONA_API_KEY,
    api_url=DAYTONA_SERVER_URL,
    target=DAYTONA_TARGET,
)
daytona = AsyncDaytona(daytona_config)

async def get_or_start_sandbox(sandbox_id: str) -> AsyncSandbox:
    """サンドボックスを取得し、必要に応じて起動する"""
    sandbox = await daytona.get(sandbox_id)

    if sandbox.state in [SandboxState.ARCHIVED, SandboxState.STOPPED, SandboxState.ARCHIVING]:
        await daytona.start(sandbox)

        for _ in range(30):
            await asyncio.sleep(1)
            sandbox = await daytona.get(sandbox_id)
            if sandbox.state == SandboxState.STARTED:
                break

    return sandbox
```

### サンドボックスの作成

```python
from daytona_sdk import CreateSandboxFromSnapshotParams

async def create_sandbox(password: str, project_id: str = None) -> AsyncSandbox:
    labels = {'id': project_id} if project_id else None

    params = CreateSandboxFromSnapshotParams(
        snapshot=SANDBOX_SNAPSHOT_NAME,
        public=True,
        labels=labels,
        env_vars={
            "CHROME_PERSISTENT_SESSION": "true",
            "RESOLUTION": "1048x768x24",
            "VNC_PASSWORD": password,
        },
        auto_stop_interval=15,
        auto_archive_interval=30,
    )

    sandbox = await daytona.create(params)
    return sandbox
```

---

## 2. コマンド実行パターン

### PTYセッションによるリアルタイム実行

```python
from daytona_sdk.common.pty import PtySize
from uuid import uuid4
import re

async def execute_with_pty(sandbox: AsyncSandbox, command: str, cwd: str, timeout: int = 300):
    output_buffer = []
    exit_code = 0

    async def on_pty_data(data: bytes):
        text = data.decode("utf-8", errors="replace")
        output_buffer.append(text)

    pty_session_id = f"cmd-{str(uuid4())[:8]}"

    pty_handle = await sandbox.process.create_pty_session(
        id=pty_session_id,
        on_data=on_pty_data,
        pty_size=PtySize(cols=120, rows=40)
    )

    try:
        await pty_handle.send_input(f"cd {cwd}\n")
        await asyncio.sleep(0.1)

        marker = f"__CMD_DONE_{str(uuid4())[:8]}__"
        full_command = f"{command}; echo '{marker}' $?\n"
        await pty_handle.send_input(full_command)

        import time
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)
            current_output = "".join(output_buffer)
            if current_output.count(marker) >= 2:
                marker_idx = current_output.rfind(marker)
                after_marker = current_output[marker_idx + len(marker):].strip().split()[0]
                exit_code = int(after_marker) if after_marker.isdigit() else 0
                break
        else:
            exit_code = -1

        final_output = "".join(output_buffer)
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        final_output = ansi_escape.sub('', final_output)

        return {"output": final_output.strip(), "exit_code": exit_code}

    finally:
        try:
            await pty_handle.kill()
        except:
            pass
```

### セッションベースの実行（フォールバック）

```python
from daytona_sdk import SessionExecuteRequest

async def execute_with_session(sandbox: AsyncSandbox, command: str, cwd: str, timeout: int = 300):
    session_id = f"cmd_{str(uuid4())[:8]}"

    try:
        await sandbox.process.create_session(session_id)

        req = SessionExecuteRequest(
            command=command,
            var_async=False,
            cwd=cwd
        )

        response = await sandbox.process.execute_session_command(
            session_id=session_id,
            req=req,
            timeout=timeout
        )

        logs = await sandbox.process.get_session_command_logs(
            session_id=session_id,
            command_id=response.cmd_id
        )

        return {
            "output": logs.output if logs else "",
            "exit_code": response.exit_code
        }
    finally:
        try:
            await sandbox.process.delete_session(session_id)
        except:
            pass
```

### バックグラウンドプロセス（tmux）

```bash
# サーバーをバックグラウンドで起動
tmux new-session -d -s myserver 'npm run dev'

# プロセスの出力を確認
tmux capture-pane -t myserver -p

# プロセスを停止
tmux kill-session -t myserver

# セッション一覧
tmux list-sessions
```

---

## 3. ファイル操作パターン

### パス正規化

```python
def clean_path(path: str, workspace_path: str = "/workspace") -> str:
    path = path.strip()

    if path.startswith(workspace_path + "/"):
        path = path[len(workspace_path) + 1:]
    elif path.startswith(workspace_path):
        path = path[len(workspace_path):]

    path = path.lstrip("/")
    return path
```

### ファイル操作

```python
async def create_file(sandbox: AsyncSandbox, file_path: str, content: str):
    full_path = f"/workspace/{clean_path(file_path)}"

    parent_dir = '/'.join(full_path.split('/')[:-1])
    if parent_dir:
        await sandbox.fs.create_folder(parent_dir, "755")

    await sandbox.fs.upload_file(content.encode(), full_path)
    await sandbox.fs.set_file_permissions(full_path, "644")

async def read_file(sandbox: AsyncSandbox, file_path: str) -> str:
    full_path = f"/workspace/{clean_path(file_path)}"
    content = await sandbox.fs.download_file(full_path)
    return content.decode()

async def file_exists(sandbox: AsyncSandbox, file_path: str) -> bool:
    try:
        await sandbox.fs.get_file_info(file_path)
        return True
    except Exception:
        return False

async def list_files(sandbox: AsyncSandbox, path: str = "/workspace"):
    files = await sandbox.fs.list_files(path)
    return [{"name": f.name, "is_dir": f.is_dir, "size": f.size} for f in files]
```

---

## 4. プレビューURL取得

```python
async def get_preview_links(sandbox: AsyncSandbox):
    try:
        vnc_link = await sandbox.get_preview_link(6080)
        website_link = await sandbox.get_preview_link(8080)

        vnc_url = vnc_link.url if hasattr(vnc_link, 'url') else str(vnc_link).split("url='")[1].split("'")[0]
        website_url = website_link.url if hasattr(website_link, 'url') else str(website_link).split("url='")[1].split("'")[0]

        token = vnc_link.token if hasattr(vnc_link, 'token') else None

        return {"vnc_url": vnc_url, "website_url": website_url, "token": token}
    except Exception:
        return {"vnc_url": None, "website_url": None, "token": None}
```

---

## 5. エラーハンドリングとリトライ

### リトライ可能なエラー判定

```python
def is_retryable_error(error: Exception) -> bool:
    error_str = str(error).lower()
    retryable_patterns = [
        '502', 'bad gateway', '503', 'service unavailable', '504', 'gateway timeout',
        'connection reset', 'connection refused', 'timeout', 'starting', 'not ready',
    ]
    return any(pattern in error_str for pattern in retryable_patterns)
```

### 指数バックオフ付きリトライ

```python
async def retry_with_backoff(operation, max_attempts: int = 5, base_delay: float = 0.5, max_delay: float = 8.0):
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as e:
            last_exception = e
            if not is_retryable_error(e) or attempt == max_attempts:
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            await asyncio.sleep(delay)

    raise last_exception
```

---

## 6. サンドボックスプール（事前プロビジョニング）

```python
POOL_CONFIG = {
    "min_size": 3,
    "max_size": 10,
    "replenish_threshold": 2,
    "check_interval": 60,
    "max_age": 3600,
}

async def keepalive_pooled_sandboxes(sandbox_ids: list):
    for sandbox_id in sandbox_ids:
        try:
            sandbox = await daytona.get(sandbox_id)
            if sandbox.state == SandboxState.STARTED:
                session_id = f"keepalive_{uuid4().hex[:8]}"
                await sandbox.process.create_session(session_id)
                await sandbox.process.execute_session_command(
                    session_id,
                    SessionExecuteRequest(command="echo keepalive", var_async=False)
                )
        except Exception:
            pass
```

---

## 7. 使用上の注意点

| 項目 | 内容 |
|------|------|
| ワークスペース | `/workspace` 配下で操作、相対パスで指定 |
| セッションID | `uuid4()[:8]` でユニーク生成、finally句でクリーンアップ |
| ポート | 8080(Web)、6080(noVNC)、9222(CDP) |
| タイムアウト | デフォルト300秒、長時間処理はtmux使用 |

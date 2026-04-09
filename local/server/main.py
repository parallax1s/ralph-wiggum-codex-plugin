from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from server.app_control import CodexAppController
    from server.app_server_client import CodexAppServerClient
    from server.backup_store import BackupStore
    from server.config_store import ConfigStore
    from server.live_ipc_client import LiveCodexIpcClient
    from server.prompt_queue_store import PromptQueueStore
    from server.thread_store import ThreadStore
else:  # pragma: no cover - exercised in plugin runtime
    from .app_control import CodexAppController
    from .app_server_client import CodexAppServerClient
    from .backup_store import BackupStore
    from .config_store import ConfigStore
    from .live_ipc_client import LiveCodexIpcClient
    from .prompt_queue_store import PromptQueueStore
    from .thread_store import ThreadStore


SERVER_NAME = "codex-thread-resumer"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"


class McpError(Exception):
    def __init__(self, message: str, code: int = -32000) -> None:
        super().__init__(message)
        self.code = code


def _default_state_db() -> Path:
    return Path(os.environ.get("CODEX_THREAD_RESUMER_STATE_DB", "~/.codex/state_5.sqlite")).expanduser()


def _default_config_path() -> Path:
    return Path(os.environ.get("CODEX_THREAD_RESUMER_CONFIG", "~/.codex/config.toml")).expanduser()


def _default_app_name() -> str:
    return os.environ.get("CODEX_THREAD_RESUMER_APP_NAME", "Codex")


def _default_backup_path() -> Path:
    return Path(
        os.environ.get("CODEX_THREAD_RESUMER_BACKUPS", "~/.codex/thread-resumer-backups.json")
    ).expanduser()


def _default_prompt_queue_path() -> Path:
    return Path(
        os.environ.get("CODEX_THREAD_RESUMER_PROMPT_QUEUE", "~/.codex/thread-resumer-prompt-queue.json")
    ).expanduser()


def _make_services() -> tuple[ThreadStore, ConfigStore, CodexAppController, PromptQueueStore, CodexAppServerClient, LiveCodexIpcClient]:
    backup_store = BackupStore(_default_backup_path())
    return (
        ThreadStore(_default_state_db(), backup_store=backup_store),
        ConfigStore(_default_config_path()),
        CodexAppController(app_name=_default_app_name()),
        PromptQueueStore(_default_prompt_queue_path()),
        CodexAppServerClient(),
        LiveCodexIpcClient(),
    )


def _tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "list_threads",
            "description": "List recent local Codex desktop threads from the state sqlite database.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                    "include_archived": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "inspect_thread_workspace",
            "description": "Inspect one local Codex thread and return its workspace-facing metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "title": {"type": "string"},
                    "include_archived": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "preview_thread_move",
            "description": "Preview how a thread's workspace metadata would change before applying a move.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "target_cwd": {"type": "string"},
                    "mode": {"type": "string", "enum": ["cwd_only", "full_metadata"]},
                    "deep_move": {"type": "boolean"},
                    "git_branch": {"type": "string"},
                    "git_sha": {"type": "string"},
                    "git_origin_url": {"type": "string"}
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "move_thread_to_workspace",
            "description": "Move a thread to another workspace by updating its stored metadata.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "target_cwd": {"type": "string"},
                    "mode": {"type": "string", "enum": ["cwd_only", "full_metadata"]},
                    "deep_move": {"type": "boolean"},
                    "git_branch": {"type": "string"},
                    "git_sha": {"type": "string"},
                    "git_origin_url": {"type": "string"}
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "undo_last_thread_move",
            "description": "Undo the most recent metadata move for a thread from the backup store.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"}
                },
                "required": ["thread_id"],
                "additionalProperties": False,
            },
        },
        {
            "name": "fork_thread_to_workspace",
            "description": "Request a workspace fork for a thread. Currently returns a safety-gated rejection.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "target_cwd": {"type": "string"},
                    "git_branch": {"type": "string"},
                    "git_sha": {"type": "string"},
                    "git_origin_url": {"type": "string"}
                },
                "required": ["thread_id", "target_cwd"],
                "additionalProperties": False,
            },
        },
        {
            "name": "set_resume_target",
            "description": "Legacy helper: write experimental_resume for a chosen thread without restarting Codex.app.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "title": {"type": "string"}
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "clear_resume_target",
            "description": "Legacy helper: remove experimental_resume from the Codex config file.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
        {
            "name": "resume_thread",
            "description": "Legacy helper: stage a chosen thread as experimental_resume and optionally restart Codex.app.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "title": {"type": "string"},
                    "restart": {"type": "boolean"},
                    "dry_run": {"type": "boolean"}
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "queue_prompt_for_thread",
            "description": "Queue one prompt for a Codex thread so a session-start consumer can inject it once on resume.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "title": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["message"],
                "additionalProperties": False,
            },
        },
        {
            "name": "consume_queued_prompt",
            "description": "Consume and clear the queued prompt for a thread exactly once.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "title": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "resume_thread_with_queue",
            "description": "Queue a prompt for a thread, stage it as experimental_resume, and optionally restart Codex.app.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "title": {"type": "string"},
                    "message": {"type": "string"},
                    "restart": {"type": "boolean"},
                    "dry_run": {"type": "boolean"},
                },
                "required": ["message"],
                "additionalProperties": False,
            },
        },
        {
            "name": "send_prompt_to_thread",
            "description": "Send a prompt directly into an existing Codex thread through codex app-server.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "title": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["message"],
                "additionalProperties": False,
            },
        },
        {
            "name": "send_prompt_to_visible_thread",
            "description": "Send a prompt into the currently loaded Codex desktop thread through the live IPC router.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "title": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["message"],
                "additionalProperties": False,
            },
        },
    ]


def _content(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, indent=2, sort_keys=True),
            }
        ]
    }


def _error_response(req_id: Any, error: Exception) -> dict[str, Any]:
    code = error.code if isinstance(error, McpError) else -32000
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": code,
            "message": str(error),
        },
    }


def _resolve_thread(args: dict[str, Any], store: ThreadStore):
    thread = store.get_thread(
        thread_id=args.get("thread_id"),
        title=args.get("title"),
        include_archived=args.get("include_archived", True),
    )
    if thread is None:
        raise McpError("Thread not found", code=-32001)
    return thread


def _handle_tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    thread_store, config_store, app_controller, prompt_queue_store, app_server_client, live_ipc_client = _make_services()

    if name == "list_threads":
        threads = thread_store.list_threads(
            limit=int(args.get("limit", 20)),
            include_archived=bool(args.get("include_archived", False)),
        )
        return _content({"threads": [thread.to_dict() for thread in threads]})

    if name == "inspect_thread_workspace":
        thread = _resolve_thread(args, thread_store)
        return _content({"thread": thread.to_dict()})

    if name == "preview_thread_move":
        target_cwd = args.get("target_cwd")
        if not target_cwd:
            raise McpError("target_cwd is required", code=-32003)
        preview = thread_store.preview_move(
            thread_id=args.get("thread_id", ""),
            target_cwd=target_cwd,
            mode=args.get("mode", "full_metadata"),
            git_branch=args.get("git_branch"),
            git_sha=args.get("git_sha"),
            git_origin_url=args.get("git_origin_url"),
        )
        return _content(
            {
                "preview": preview.to_dict(),
                "deep_move": bool(args.get("deep_move", False)),
                "note": "deep_move patches the rollout session_meta cwd in addition to the thread row.",
            }
        )

    if name == "move_thread_to_workspace":
        target_cwd = args.get("target_cwd")
        if not target_cwd:
            raise McpError("target_cwd is required", code=-32003)
        target_path = Path(target_cwd).expanduser()
        if not target_path.exists():
            raise McpError(f"Target workspace does not exist: {target_path}", code=-32004)
        moved = thread_store.move_thread(
            thread_id=args.get("thread_id", ""),
            target_cwd=str(target_path),
            mode=args.get("mode", "full_metadata"),
            deep_move=bool(args.get("deep_move", False)),
            git_branch=args.get("git_branch"),
            git_sha=args.get("git_sha"),
            git_origin_url=args.get("git_origin_url"),
        )
        return _content(
            {
                "thread": moved.to_dict(),
                "moved": True,
                "deep_move": bool(args.get("deep_move", False)),
            }
        )

    if name == "undo_last_thread_move":
        thread_id = args.get("thread_id")
        if not thread_id:
            raise McpError("thread_id is required", code=-32003)
        restored = thread_store.undo_last_move(thread_id)
        return _content({"thread": restored.to_dict(), "restored": True})

    if name == "fork_thread_to_workspace":
        try:
            thread_store.fork_thread(
                thread_id=args.get("thread_id", ""),
                target_cwd=args.get("target_cwd", ""),
            )
        except RuntimeError as error:
            return _content(
                {
                    "supported": False,
                    "message": str(error),
                }
            )
        raise McpError("Unexpected fork_thread success path", code=-32005)

    if name == "set_resume_target":
        thread = _resolve_thread(args, thread_store)
        rollout_path = Path(thread.rollout_path)
        if not rollout_path.exists():
            raise McpError(f"Rollout path does not exist: {rollout_path}", code=-32002)
        backup_path = config_store.set_experimental_resume(thread.rollout_path)
        return _content(
            {
                "thread": thread.to_dict(),
                "config_path": str(config_store.config_path),
                "backup_path": str(backup_path),
                "staged": True,
            }
        )

    if name == "clear_resume_target":
        backup_path = config_store.clear_experimental_resume()
        return _content(
            {
                "config_path": str(config_store.config_path),
                "backup_path": str(backup_path),
                "cleared": True,
            }
        )

    if name == "resume_thread":
        thread = _resolve_thread(args, thread_store)
        rollout_path = Path(thread.rollout_path)
        if not rollout_path.exists():
            raise McpError(f"Rollout path does not exist: {rollout_path}", code=-32002)
        backup_path = config_store.set_experimental_resume(thread.rollout_path)
        restart = bool(args.get("restart", True))
        dry_run = bool(args.get("dry_run", False))
        restart_result = app_controller.restart(dry_run=dry_run) if restart else None
        payload: dict[str, Any] = {
            "thread": thread.to_dict(),
            "config_path": str(config_store.config_path),
            "backup_path": str(backup_path),
            "staged": True,
            "restart_requested": restart,
        }
        if restart_result is not None:
            payload["restart_result"] = restart_result.to_dict()
        return _content(payload)

    if name == "queue_prompt_for_thread":
        thread = _resolve_thread(args, thread_store)
        message = str(args.get("message", "")).strip()
        if not message:
            raise McpError("message is required", code=-32003)
        queued = prompt_queue_store.queue_prompt(
            thread_id=thread.id,
            message=message,
            title=thread.title,
            rollout_path=thread.rollout_path,
        )
        return _content({"queued": True, "thread": thread.to_dict(), "prompt": queued})

    if name == "consume_queued_prompt":
        thread = _resolve_thread(args, thread_store)
        queued = prompt_queue_store.consume_prompt(thread.id)
        return _content(
            {
                "thread": thread.to_dict(),
                "prompt": queued,
                "consumed": queued is not None,
            }
        )

    if name == "resume_thread_with_queue":
        thread = _resolve_thread(args, thread_store)
        message = str(args.get("message", "")).strip()
        if not message:
            raise McpError("message is required", code=-32003)
        rollout_path = Path(thread.rollout_path)
        if not rollout_path.exists():
            raise McpError(f"Rollout path does not exist: {rollout_path}", code=-32002)
        queued = prompt_queue_store.queue_prompt(
            thread_id=thread.id,
            message=message,
            title=thread.title,
            rollout_path=thread.rollout_path,
        )
        backup_path = config_store.set_experimental_resume(thread.rollout_path)
        restart = bool(args.get("restart", True))
        dry_run = bool(args.get("dry_run", False))
        restart_result = app_controller.restart(dry_run=dry_run) if restart else None
        payload: dict[str, Any] = {
            "thread": thread.to_dict(),
            "prompt": queued,
            "config_path": str(config_store.config_path),
            "backup_path": str(backup_path),
            "staged": True,
            "restart_requested": restart,
        }
        if restart_result is not None:
            payload["restart_result"] = restart_result.to_dict()
        return _content(payload)

    if name == "send_prompt_to_thread":
        thread = _resolve_thread(args, thread_store)
        message = str(args.get("message", "")).strip()
        if not message:
            raise McpError("message is required", code=-32003)
        result = app_server_client.send_prompt_to_thread(thread_id=thread.id, message=message)
        return _content({"thread": result["thread"], "turn": result["turn"], "sent": True})

    if name == "send_prompt_to_visible_thread":
        thread = _resolve_thread(args, thread_store)
        message = str(args.get("message", "")).strip()
        if not message:
            raise McpError("message is required", code=-32003)
        result = live_ipc_client.submit_user_input(conversation_id=thread.id, message=message)
        return _content({"thread": thread.to_dict(), "result": result, "sent": True})

    raise McpError(f"Unknown tool: {name}", code=-32601)


def _handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": _tool_definitions(),
            },
        }

    if method == "tools/call":
        result = _handle_tool_call(params.get("name", ""), params.get("arguments", {}))
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        }

    raise McpError(f"Unknown method: {method}", code=-32601)


def _read_message(stream) -> dict[str, Any] | None:
    content_length = None
    while True:
        line = stream.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        header = line.decode("utf-8").strip()
        if header.lower().startswith("content-length:"):
            content_length = int(header.split(":", 1)[1].strip())
    if content_length is None:
        raise McpError("Missing Content-Length header", code=-32700)
    body = stream.read(content_length)
    if len(body) != content_length:
        raise McpError("Incomplete request body", code=-32700)
    return json.loads(body.decode("utf-8"))


def _write_message(stream, message: dict[str, Any]) -> None:
    body = json.dumps(message).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    stream.write(header)
    stream.write(body)
    stream.flush()


def main() -> int:
    while True:
        try:
            request = _read_message(sys.stdin.buffer)
            if request is None:
                return 0
            response = _handle_request(request)
            if response is not None:
                _write_message(sys.stdout.buffer, response)
        except Exception as error:  # pragma: no cover - protocol guardrail
            req_id = None
            if "request" in locals() and isinstance(request, dict):
                req_id = request.get("id")
            _write_message(sys.stdout.buffer, _error_response(req_id, error))


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ENGINE_VERSION = "1.0.0"


def _clean_paths(items: Iterable[str | Path]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items or []:
        path = Path(item).expanduser()
        if not path.is_file():
            continue
        resolved = str(path.resolve())
        key = resolved.casefold()
        if key not in seen:
            output.append(resolved)
            seen.add(key)
    return output


@dataclass
class FeedbackContext:
    application: str
    application_version: str = ""
    build: str = ""
    company: str = ""
    user: str = ""
    language: str = ""
    current_page: str = ""
    related_tool: str = ""
    tool_version: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackRequest:
    category: str = "Bug Report"
    priority: str = "Normal"
    reproducible: str = "Unknown"
    comment: str = ""
    mode: str = "template"
    attachments: list[str] = field(default_factory=list)
    context: FeedbackContext | None = None


class FeedbackEngine:
    def __init__(self, app_dir: str | Path, feedback_to: str = "masakii@insightec.com",
                 log_dir: str | Path | None = None, feedback_dir: str | Path | None = None):
        self.app_dir = Path(app_dir).resolve()
        self.feedback_to = feedback_to
        self.log_dir = Path(log_dir).resolve() if log_dir else self.app_dir / "logs"
        self.feedback_dir = Path(feedback_dir).resolve() if feedback_dir else self.app_dir / "feedback"
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

    def recent_logs(self, limit: int = 5) -> list[str]:
        if not self.log_dir.exists():
            return []
        return [str(p.resolve()) for p in sorted(
            self.log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True
        )[:limit]]

    def create_validation_report(self, context: FeedbackContext,
                                 validation_rows: Sequence[str] | None = None,
                                 prefix: str = "validation_report") -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.feedback_dir / f"{prefix}_{stamp}.txt"
        rows = [
            f"{context.application} Validation Report",
            f"Feedback Engine: {ENGINE_VERSION}",
            f"Time: {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"Application version: {context.application_version}",
            f"Build: {context.build}",
            f"Company: {context.company}",
            f"User: {context.user}",
            f"Language: {context.language}",
            f"Current page: {context.current_page}",
            f"Related tool: {context.related_tool}",
            f"Tool version: {context.tool_version}",
            f"OS: {platform.platform()}",
            f"Python: {platform.python_version()}",
            f"Frozen runtime: {bool(getattr(sys, 'frozen', False))}",
            "",
            "Context:",
        ]
        rows.extend(f"{k}: {v}" for k, v in context.extra.items())
        rows.extend(["", "Validation:"])
        rows.extend(validation_rows or ["(not supplied)"])
        rows.extend(["", "Recent logs:"])
        recent = self.recent_logs()
        rows.extend([Path(p).name for p in recent] if recent else ["(none)"])
        path.write_text("\n".join(rows), encoding="utf-8")
        return path

    def build_subject(self, request: FeedbackRequest) -> str:
        context = request.context or FeedbackContext(application="Service Tool")
        version = context.tool_version or context.application_version or context.build
        suffix = f" - v{version}" if version else ""
        return f"[{request.category}] {context.related_tool or context.application}{suffix}"

    def build_body(self, request: FeedbackRequest,
                   validation_rows: Sequence[str] | None = None) -> str:
        context = request.context or FeedbackContext(application="Service Tool")
        attachments = _clean_paths(request.attachments)
        extra = "\n".join(f"{key}: {value}" for key, value in context.extra.items()) or "(none)"
        validation = "\n".join(validation_rows or []) or "(not supplied)"
        recent_logs = self.recent_logs()
        recent = "\n".join(Path(p).name for p in recent_logs) if recent_logs else "(none)"
        attachment_text = "\n".join(attachments) if attachments else "(none selected)"
        return f"""Service Tool Feedback / FEU Validation

To: {self.feedback_to}
Subject: {self.build_subject(request)}

Category: {request.category}
Priority: {request.priority}
Reproducible: {request.reproducible}
Send mode: {request.mode}

Application: {context.application}
Application version: {context.application_version}
Build: {context.build}
Company: {context.company}
User: {context.user}
Language: {context.language}
Current page: {context.current_page}
Related tool: {context.related_tool}
Tool version: {context.tool_version}
OS: {platform.platform()}
Python: {platform.python_version()}
Time: {datetime.now():%Y-%m-%d %H:%M:%S}
Feedback Engine: {ENGINE_VERSION}

Current context:
{extra}

Comment:
{request.comment.strip() or '(no comment)'}

Validation:
{validation}

Attachments:
{attachment_text}

Recent logs:
{recent}
"""

    def persist(self, request: FeedbackRequest, body: str | None = None,
                validation_rows: Sequence[str] | None = None) -> dict[str, Path]:
        request.attachments = _clean_paths(request.attachments)
        body = body or self.build_body(request, validation_rows)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        template = self.feedback_dir / f"feedback_template_{stamp}.txt"
        manifest = self.feedback_dir / f"feedback_manifest_{stamp}.json"
        template.write_text(body, encoding="utf-8")
        payload = {
            "schema": "insightec.feedback.v1",
            "engine_version": ENGINE_VERSION,
            "created": datetime.now().isoformat(timespec="seconds"),
            "subject": self.build_subject(request),
            "template": str(template),
            "request": asdict(request),
        }
        manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"template": template, "manifest": manifest}

    def prepare(self, request: FeedbackRequest,
                validation_rows: Sequence[str] | None = None) -> tuple[str, dict[str, Path]]:
        body = self.build_body(request, validation_rows)
        return body, self.persist(request, body, validation_rows)


def build_runtime_context(application: str, application_version: str = "", build: str = "",
                          company: str = "", user: str = "", language: str = "",
                          current_page: str = "", related_tool: str = "",
                          tool_version: str = "", extra: Mapping[str, Any] | None = None) -> FeedbackContext:
    return FeedbackContext(
        application=application,
        application_version=application_version,
        build=build,
        company=company,
        user=user,
        language=language,
        current_page=current_page,
        related_tool=related_tool,
        tool_version=tool_version,
        extra=dict(extra or {}),
    )

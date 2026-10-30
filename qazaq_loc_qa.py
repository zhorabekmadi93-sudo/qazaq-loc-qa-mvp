#!/usr/bin/env python3
"""
qazaq_loc_qa.py — UX/UI Quality Assurance Linter for Kazakh Flutter Localization (ARB/JSON).
Checks:
  1. suffix_harmony: flags suffixes attached to dynamic placeholders like {name}-ға / {user}-ге.
  2. length_overflow: flags UI keys (*_button, *_tab, *_title) exceeding character limits.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Common Kazakh inflectional suffixes (dative, genitive, accusative, locative, ablative, instrumental)
KAZAKH_SUFFIX_PATTERN = re.compile(
    r"\{([a-zA-Z0-9_]+)\}\s*[-–—]?\s*([а-яА-ЯёЁәғқңөұүһіӘҒҚҢӨҰҮҺІ]+)",
    re.IGNORECASE,
)

# Keys that typically correspond to compact UI elements
DEFAULT_COMPACT_KEY_PATTERN = re.compile(
    r".*(_button|_btn|_tab|_title|_action|_header)$",
    re.IGNORECASE,
)


class Violation:
    def __init__(
        self,
        key: str,
        violation_type: str,
        message: str,
        original_text: str,
        suggested_text: Optional[str] = None,
        severity: str = "ERROR",
    ):
        self.key = key
        self.violation_type = violation_type
        self.message = message
        self.original_text = original_text
        self.suggested_text = suggested_text
        self.severity = severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "type": self.violation_type,
            "severity": self.severity,
            "message": self.message,
            "original_text": self.original_text,
            "suggested_text": self.suggested_text,
        }


def check_suffix_harmony(key: str, text: str) -> List[Violation]:
    """Detects suffixes glued to dynamic placeholders (e.g. {name}-ға)."""
    violations = []
    matches = KAZAKH_SUFFIX_PATTERN.findall(text)

    for placeholder, suffix in matches:
        # Generate suggestion: restructure by prefixing action or moving to nominative
        suggested = re.sub(
            r"\{" + placeholder + r"\}\s*[-–—]?\s*" + re.escape(suffix),
            f"{{{placeholder}}}",
            text,
        ).strip()
        
        # If text looks like "{name}-ға жіберу", suggest "Жіберу: {name}"
        if text.startswith(f"{{{placeholder}}}"):
            rest = text[len(f"{{{placeholder}}}"):].lstrip("-–— ").lstrip(suffix).strip()
            if rest:
                suggested = f"{rest.capitalize()}: {{{placeholder}}}"

        violations.append(
            Violation(
                key=key,
                violation_type="suffix_harmony",
                message=f"Динамический плейсхолдер '{{{placeholder}}}' имеет жесткий аффикс '-{suffix}'. Сингармонизм нарушается при подстановке мягких/твердых имен.",
                original_text=text,
                suggested_text=suggested,
                severity="ERROR",
            )
        )
    return violations


def check_length_overflow(
    key: str, text: str, max_length: int, key_regex: re.Pattern
) -> List[Violation]:
    """Detects compact UI elements whose text exceeds max_length."""
    violations = []
    if key_regex.match(key):
        # Calculate visual length (counting placeholder as average 8 chars)
        placeholder_normalized = re.sub(r"\{[a-zA-Z0-9_]+\}", "________", text)
        length = len(placeholder_normalized)
        if length > max_length:
            violations.append(
                Violation(
                    key=key,
                    violation_type="length_overflow",
                    message=f"Длина строки ({length} симв.) превышает лимит {max_length} для элементов UI ({key}). Риск обрезки в Flutter Widget.",
                    original_text=text,
                    suggested_text=text[:max_length] + "…" if len(text) > max_length else None,
                    severity="WARNING",
                )
            )
    return violations


def load_arb_or_json(file_path: Path) -> Dict[str, str]:
    """Loads ARB or JSON file, ignoring Flutter ARB metadata keys (@key)."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Filter out @metadata keys common in Flutter .arb
    return {k: v for k, v in data.items() if not k.startswith("@") and isinstance(v, str)}


def run_qa(
    target_path: Path,
    max_button_len: int = 15,
    key_pattern: Optional[str] = None,
) -> List[Violation]:
    regex = re.compile(key_pattern, re.IGNORECASE) if key_pattern else DEFAULT_COMPACT_KEY_PATTERN
    data = load_arb_or_json(target_path)
    all_violations: List[Violation] = []

    for key, text in data.items():
        all_violations.extend(check_suffix_harmony(key, text))
        all_violations.extend(check_length_overflow(key, text, max_button_len, regex))

    return all_violations


def render_markdown_summary(violations: List[Violation], target_file: str) -> str:
    """Creates a GitHub Action step summary in Markdown format."""
    total_errors = sum(1 for v in violations if v.severity == "ERROR")
    total_warnings = sum(1 for v in violations if v.severity == "WARNING")

    status_icon = "❌" if total_errors > 0 else ("⚠️" if total_warnings > 0 else "✅")
    
    lines = [
        f"## {status_icon} Qazaq Localization QA Report: `{os.path.basename(target_file)}`",
        "",
        f"- **Ошибок (Сингармонизм):** {total_errors}",
        f"- **Предупреждений (Длина UI):** {total_warnings}",
        "",
    ]

    if not violations:
        lines.append("🎉 **Все проверки пройдены! Проблем с сингармонизмом и длиной текста не обнаружено.**")
        return "\n".join(lines)

    lines.extend([
        "| Статус | Ключ | Проблема | Текущий текст | Рекомендация |",
        "| :---: | :--- | :--- | :--- | :--- |",
    ])

    for v in violations:
        icon = "🔴 ERROR" if v.severity == "ERROR" else "🟡 WARN"
        suggestion = f"`{v.suggested_text}`" if v.suggested_text else "—"
        original = f"`{v.original_text}`"
        lines.append(
            f"| {icon} | `{v.key}` | {v.message} | {original} | {suggestion} |"
        )

    lines.append("")
    lines.append("> [!TIP]")
    lines.append("> Для исправления `suffix_harmony` перенесите динамическое имя в именительный падеж (например, `Жіберу: {name}`).")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Kazakh Flutter Localization QA Linter (suffix harmony + UI length)"
    )
    parser.add_argument("target", type=Path, help="Path to Kazakh ARB or JSON file (e.g., app_kk.arb)")
    parser.add_argument(
        "--max-button-len",
        type=int,
        default=15,
        help="Max character length for UI keys (*_button, *_tab, etc.). Default: 15",
    )
    parser.add_argument(
        "--key-regex",
        type=str,
        default=None,
        help="Custom regex for UI keys subject to length checks",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Write JSON report to specified file path",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Fail (exit 1) on warnings as well as errors",
    )

    args = parser.parse_args()

    if not args.target.exists():
        print(f"Error: Target file not found: {args.target}", file=sys.stderr)
        sys.exit(1)

    violations = run_qa(
        target_path=args.target,
        max_button_len=args.max_button_len,
        key_pattern=args.key_regex,
    )

    # Output to stdout
    print(f"\n--- Qazaq Localization QA: {args.target.name} ---")
    if not violations:
        print("✅ Проверок пройдено без замечаний.")
    else:
        for v in violations:
            color = "\033[91m" if v.severity == "ERROR" else "\033[93m"
            reset = "\033[0m"
            print(f"{color}[{v.severity}] {v.key}{reset}: {v.message}")
            print(f"   Текущий текст: '{v.original_text}'")
            if v.suggested_text:
                print(f"   Рекомендация : '{v.suggested_text}'")
            print()

    # Write GITHUB_STEP_SUMMARY if available
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(render_markdown_summary(violations, str(args.target)) + "\n")

    # Export JSON if requested
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump([v.to_dict() for v in violations], f, ensure_ascii=False, indent=2)
        print(f"JSON-отчёт сохранён в {args.json_output}")

    errors_count = sum(1 for v in violations if v.severity == "ERROR")
    warnings_count = sum(1 for v in violations if v.severity == "WARNING")

    if errors_count > 0 or (args.fail_on_warnings and warnings_count > 0):
        print(f"\n❌ Найдено ошибок: {errors_count}, предупреждений: {warnings_count}")
        sys.exit(1)
    else:
        print(f"\n✨ Проверка завершена успешно. Предупреждений: {warnings_count}")
        sys.exit(0)


if __name__ == "__main__":
    main()

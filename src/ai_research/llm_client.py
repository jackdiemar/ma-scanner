"""
llm_client.py — Thin OpenAI-compatible LLM client for the AI research layer.

Config from environment (loaded from config/.env or process env):
  AI_RESEARCH_ENABLED          true/false (default: false)
  OPENAI_API_KEY               API key — required if AI enabled
  AI_MODEL                     Model name (default: gpt-4.1-mini)
  AI_RESEARCH_MAX_CASES_PER_RUN  Max cases per run (default: 5)
  AI_RESEARCH_DEFAULT_DEPTH    Research depth preset (default: fast_gate)
  AI_RESEARCH_DRY_RUN          true/false (default: true)

If key missing or AI_RESEARCH_ENABLED=false: skip gracefully.
The live scanner never imports this module, so a missing key does not affect scanning.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE   = Path(__file__).resolve().parent
_SRCDIR = _HERE.parent
REPO    = _SRCDIR.parent

ENV_FILE = REPO / 'config' / '.env'

_DEFAULT_MODEL = 'gpt-4.1-mini'
_DEFAULT_MAX_CASES = 5
_DEFAULT_DEPTH = 'fast_gate'


# ── Env loader (mirrors live_scanner_runner.py convention) ────────────────────

def _load_env() -> None:
    if not ENV_FILE.exists():
        return
    with ENV_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None or value == '':
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _bool_text(value: bool) -> str:
    return 'true' if value else 'false'


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LLMConfig:
    enabled: bool
    api_key: str
    model: str
    max_cases_per_run: int
    default_depth: str
    dry_run: bool

    @property
    def ready(self) -> bool:
        """True if AI is enabled and an API key is present."""
        return self.enabled and bool(self.api_key)

    @property
    def live_call_allowed(self) -> bool:
        """True if config permits live LLM calls."""
        return self.ready and not self.dry_run


def load_config() -> LLMConfig:
    _load_env()
    try:
        max_cases = int(os.environ.get('AI_RESEARCH_MAX_CASES_PER_RUN', _DEFAULT_MAX_CASES))
    except (ValueError, TypeError):
        max_cases = _DEFAULT_MAX_CASES
    return LLMConfig(
        enabled           = _truthy(os.environ.get('AI_RESEARCH_ENABLED'), default=False),
        api_key           = os.environ.get('OPENAI_API_KEY', '').strip(),
        model             = os.environ.get('AI_MODEL', _DEFAULT_MODEL).strip() or _DEFAULT_MODEL,
        max_cases_per_run = max_cases,
        default_depth     = os.environ.get('AI_RESEARCH_DEFAULT_DEPTH', _DEFAULT_DEPTH).strip() or _DEFAULT_DEPTH,
        dry_run           = _truthy(os.environ.get('AI_RESEARCH_DRY_RUN'), default=True),
    )


# ── LLM client ────────────────────────────────────────────────────────────────

class LLMClient:
    """
    Thin wrapper around the OpenAI Python SDK.

    Usage:
        client = LLMClient()
        if client.available:
            result = client.complete(prompt)
        else:
            print(client.status_message)
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self._cfg = config or load_config()
        self._client = None
        self._init_error: str = ''
        self._init_client()

    def _init_client(self) -> None:
        if not self._cfg.enabled:
            self._init_error = 'AI_RESEARCH_ENABLED=false: skipping AI layer.'
            return
        if not self._cfg.api_key:
            self._init_error = (
                'OPENAI_API_KEY not set: AI layer disabled. '
                'Set the key in config/.env to enable AI research.'
            )
            return
        try:
            import openai
            self._client = openai.OpenAI(api_key=self._cfg.api_key)
        except ImportError:
            self._init_error = (
                'openai package not installed. '
                'Run: pip install openai'
            )
        except Exception as exc:
            self._init_error = f'OpenAI client init error: {exc}'

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def config(self) -> LLMConfig:
        return self._cfg

    @property
    def status_message(self) -> str:
        if self.available:
            return (
                f'AI client ready: model={self._cfg.model} '
                f'dry_run={self._cfg.dry_run} '
                f'depth={self._cfg.default_depth} '
                f'max_cases={self._cfg.max_cases_per_run}'
            )
        return self._init_error or 'AI client not available.'

    def complete(self, prompt: str) -> str:
        """
        Send a completion request. Returns the model's response text.

        Raises:
            RuntimeError: if AI is not available.
            openai.OpenAIError: on API errors.
        """
        if not self.available:
            raise RuntimeError(self.status_message)

        import openai  # already validated in _init_client
        try:
            response = self._client.chat.completions.create(
                model=self._cfg.model,
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are a biotech M&A research analyst. '
                            'You classify scanner alerts and produce structured research assessments. '
                            'You are NOT making investment recommendations or transaction decisions. '
                            'Output only valid JSON as instructed.'
                        ),
                    },
                    {
                        'role': 'user',
                        'content': prompt,
                    },
                ],
                temperature=0.1,
                max_tokens=1800,
            )
            return response.choices[0].message.content or ''
        except openai.RateLimitError as exc:
            raise RuntimeError(f'OpenAI rate limit: {exc}') from exc
        except openai.AuthenticationError as exc:
            raise RuntimeError(f'OpenAI authentication error: {exc}') from exc
        except openai.OpenAIError as exc:
            raise RuntimeError(f'OpenAI API error: {exc}') from exc


def print_status() -> None:
    """Print LLM config status without exposing secrets."""
    cfg = load_config()
    print('AI Research Layer - LLM Config')
    print(f'  AI_RESEARCH_ENABLED        : {_bool_text(cfg.enabled)}')
    print(f'  OPENAI_API_KEY set         : {_bool_text(bool(cfg.api_key))}')
    print(f'  AI_MODEL                   : {cfg.model}')
    print(f'  AI_RESEARCH_MAX_CASES_PER_RUN: {cfg.max_cases_per_run}')
    print(f'  AI_RESEARCH_DEFAULT_DEPTH  : {cfg.default_depth}')
    print(f'  AI_RESEARCH_DRY_RUN        : {_bool_text(cfg.dry_run)}')
    print(f'  LIVE_LLM_CALL_ALLOWED      : {_bool_text(cfg.live_call_allowed)}')
    client = LLMClient(cfg)
    print(f'  Client status              : {client.status_message}')


if __name__ == '__main__':
    print_status()

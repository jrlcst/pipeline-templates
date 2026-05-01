#!/usr/bin/env python3

import json
import os
import sys
import urllib.request
from pathlib import Path

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
CHANGED_FILES_PATH = Path(os.getenv("CHANGED_FILES_PATH", ".ai/changed-files.txt"))
DIFF_PATH = Path(os.getenv("DIFF_PATH", ".ai/diff.patch"))
AI_CONTEXT_PATH = Path(os.getenv("AI_CONTEXT_PATH", "docs/ai-context.yaml"))
OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", ".ai/pr-summary.md"))
MAX_DIFF_CHARS = int(os.getenv("MAX_DIFF_CHARS", "30000"))


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def read_file(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8", errors="ignore")


if not ANTHROPIC_API_KEY:
    fail("ANTHROPIC_API_KEY is required")

changed_files = read_file(CHANGED_FILES_PATH)
diff = read_file(DIFF_PATH)
ai_context = read_file(AI_CONTEXT_PATH, "docs/ai-context.yaml not found")

if len(diff) > MAX_DIFF_CHARS:
    diff = diff[:MAX_DIFF_CHARS] + "\n\n[DIFF TRUNCADO POR LIMITE DE CONTEXTO]\n"

prompt = f"""
Voce deve gerar um resumo objetivo para a descricao de um Pull Request.

Use somente o contexto abaixo.
Nao invente mudanca que nao aparece no diff.
Nao faca code review.
Nao sugira melhorias.
Nao cite que voce e IA.
Nao use texto longo.

Formato obrigatorio em Markdown:

## Resumo das alteracoes
- ...

## Areas impactadas
- ...

## Testes/validacoes esperadas
- ...

## Atencao para revisao humana
- ...

Se nao houver risco relevante, escreva:
- Nenhum ponto critico identificado no diff.

Contexto do servico:
```yaml
{ai_context}
```

Arquivos alterados:

```text
{changed_files}
```

Diff do PR:

```diff
{diff}
```
""".strip()

payload = {
    "model": ANTHROPIC_MODEL,
    "max_tokens": 900,
    "temperature": 0,
    "messages": [
        {
            "role": "user",
            "content": prompt,
        }
    ],
}

request = urllib.request.Request(
    "https://api.anthropic.com/v1/messages",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "content-type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
except Exception as error:
    fail(f"Failed to call Anthropic API: {error}")

text_parts = []
for item in result.get("content", []):
    if item.get("type") == "text":
        text_parts.append(item.get("text", ""))

summary = "\n".join(text_parts).strip()
if not summary:
    fail("Claude returned an empty summary")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(summary + "\n", encoding="utf-8")
print(summary)
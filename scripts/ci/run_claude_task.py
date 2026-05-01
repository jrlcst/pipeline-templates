#!/usr/bin/env python3

import json
import os
import sys
import urllib.request
from pathlib import Path

MODE = sys.argv[1] if len(sys.argv) > 1 else None
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
AI_CONTEXT_PATH = Path(os.getenv("AI_CONTEXT_PATH", "docs/ai-context.yaml"))
README_PATH = Path(os.getenv("README_PATH", "README.md"))
DOCS_DIR = Path(os.getenv("DOCS_DIR", "docs"))
CHANGED_FILES_PATH = Path(os.getenv("CHANGED_FILES_PATH", ".ai/changed-files.txt"))
DIFF_PATH = Path(os.getenv("DIFF_PATH", ".ai/diff.patch"))
MAX_DIFF_CHARS = int(os.getenv("MAX_DIFF_CHARS", "30000"))
MAX_DOC_CHARS = int(os.getenv("MAX_DOC_CHARS", "20000"))

OUTPUT_MAP = {
    "code-review": Path(".ai/code-review.md"),
    "doc-review": Path(".ai/doc-review.md"),
}

DOC_REVIEW_BLOCK_HINTS = (
    "desatualiz",
    "nao foi atualizado",
    "não foi atualizado",
    "nao foram atualizados",
    "não foram atualizados",
    "deveria ser",
    "deveria estar",
    "deveria refletir",
    "deveria atualizar",
    "considerar atualizar",
    "faltou atualizar",
    "contradiz",
    "incoerente",
    "nao especifica",
    "não especifica",
    "ponto de atencao",
    "ponto de atenção",
)

DOC_REVIEW_SAFE_PASS_HINTS = (
    "diff vazio",
    "nao contem alteracoes",
    "não contém alterações",
    "nao ha mudancas",
    "não há mudanças",
    "nenhuma mudanca foi introduzida",
    "nenhum arquivo documental precisa ser atualizado",
)


def fail(message: str, exit_code: int = 1) -> None:
    print(message, file=sys.stderr)
    sys.exit(exit_code)


def read_file(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8", errors="ignore")


def collect_docs() -> str:
    if not DOCS_DIR.exists():
        return ""

    chunks = []
    current_length = 0
    for path in sorted(DOCS_DIR.rglob("*.md")):
        content = read_file(path)
        block = f"\n## {path.as_posix()}\n\n{content}\n"
        if current_length + len(block) > MAX_DOC_CHARS:
            remaining = MAX_DOC_CHARS - current_length
            if remaining > 0:
                chunks.append(block[:remaining])
            chunks.append("\n[DOCUMENTACAO TRUNCADA POR LIMITE DE CONTEXTO]\n")
            break
        chunks.append(block)
        current_length += len(block)
    return "".join(chunks)


def call_anthropic(prompt: str) -> str:
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1200,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
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
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))

    text_parts = []
    for item in result.get("content", []):
        if item.get("type") == "text":
            text_parts.append(item.get("text", ""))
    return "\n".join(text_parts).strip()


def should_force_doc_review_block(output: str, changed_files: str, diff: str) -> bool:
    lines = output.splitlines()
    if not lines:
        return False

    first_line = lines[0].strip().upper()
    if first_line.startswith("BLOCK"):
        return False
    if not first_line.startswith("PASS"):
        return False

    if not changed_files.strip() and not diff.strip():
        return False

    normalized = output.casefold()
    if any(hint in normalized for hint in DOC_REVIEW_SAFE_PASS_HINTS):
        return False

    return any(hint in normalized for hint in DOC_REVIEW_BLOCK_HINTS)


if MODE not in OUTPUT_MAP:
    fail("Usage: run_claude_task.py <code-review|doc-review>")

if not ANTHROPIC_API_KEY:
    fail("ANTHROPIC_API_KEY is required")

ai_context = read_file(AI_CONTEXT_PATH, "docs/ai-context.yaml not found")
readme = read_file(README_PATH, "README.md not found")
changed_files = read_file(CHANGED_FILES_PATH)
diff = read_file(DIFF_PATH)
docs_content = collect_docs()

if len(diff) > MAX_DIFF_CHARS:
    diff = diff[:MAX_DIFF_CHARS] + "\n\n[DIFF TRUNCADO POR LIMITE DE CONTEXTO]\n"

if MODE == "code-review":
    prompt = f"""
Voce esta fazendo code review de um pull request.

Use somente o contexto abaixo.
Nao invente comportamento que nao aparece no diff.
Nao replique achados de estilo irrelevante.
Nao replique achados genericos ja cobertos por Sonar ou Trivy.

Priorize:
- bug real
- quebra de contrato
- impacto em consumidor
- ausencia de teste relevante
- regra de negocio inconsistente
- risco em configuracao

Se nao houver findings relevantes, responda explicitamente que nao encontrou problemas relevantes.

Formato esperado:

## Findings
- ...

## Riscos residuais
- ...

Contexto do servico:
```yaml
{ai_context}
```

README:
```md
{readme}
```

Arquivos alterados:
```text
{changed_files}
```

Diff:
```diff
{diff}
```
""".strip()
else:
    prompt = f"""
Voce esta fazendo doc review de um pull request.

Use somente o contexto abaixo.
Seu objetivo e decidir se a mudanca deve bloquear por documentacao desatualizada.

Bloqueie somente quando AS DUAS condicoes abaixo forem verdadeiras ao mesmo tempo:
1. O diff altera endpoint, DTO, regra, integracao, contrato, configuracao ou fluxo relevante.
2. README, docs, docs/ai-context.yaml ou skills locais de review nao foram atualizados de forma coerente quando isso era necessario.

Se a mudanca for relevante mas a documentacao tiver sido atualizada de forma coerente, a resposta deve ser PASS.
Mudanca relevante por si so nao e motivo para BLOCK.
Nao use BLOCK apenas porque a mudanca merece atencao humana extra ou revisao mais cuidadosa.
Nesse caso, responda PASS e cite os pontos de atencao em ## Analise.

Para mudancas de pipeline, CI, quality gates, Sonar, Trivy, variaveis, secrets ou caller de workflow:
- BLOCK apenas se README, docs/contexts, docs/ai-context.yaml ou skills locais nao refletirem o novo contrato/configuracao quando isso for relevante para o servico.
- PASS quando a documentacao refletir corretamente workflow, variaveis, secrets, pre-condicoes externas e impacto documental.

Regras adicionais obrigatorias:
- Testes, nomes de constantes, nomes de metodos, nomes de classes e o proprio codigo NAO contam como documentacao.
- Se README, docs/flows, docs/contexts ou docs/ai-context.yaml contiverem regra antiga, contraditoria ou incompleta em relacao ao diff, isso e BLOCK.
- Se voce identificar qualquer arquivo documental desatualizado, contraditorio, incompleto ou que "deveria ser atualizado", a resposta final deve ser BLOCK, nunca PASS.
- Nao use `PASS com ponto de atencao` quando o ponto de atencao for documentacao incoerente com o codigo.

Nao bloqueie quando:
- a mudanca e so teste
- a mudanca e refatoracao interna sem impacto externo
- a mudanca e ajuste de log
- a mudanca e somente formatacao
- a mudanca e melhoria interna sem alteracao de comportamento

Formato obrigatorio:

PASS ou BLOCK na primeira linha.

Depois:

## Analise
- ...

## Arquivos documentais esperados
- ...

Se a conclusao for PASS com documentacao coerente, deixe isso explicito logo no inicio da analise.

Contexto do servico:
```yaml
{ai_context}
```

README:
```md
{readme}
```

Documentacao complementar:
```md
{docs_content}
```

Arquivos alterados:
```text
{changed_files}
```

Diff:
```diff
{diff}
```
""".strip()

try:
    output = call_anthropic(prompt)
except Exception as error:
    fail(f"Failed to call Anthropic API: {error}")

if not output:
    fail("Claude returned an empty response")

if MODE == "doc-review" and should_force_doc_review_block(output, changed_files, diff):
    output = "BLOCK\n\n## Analise\n- A resposta original do doc review marcou PASS, mas descreveu documentacao desatualizada, contraditoria ou que deveria ser atualizada.\n- O gate converteu automaticamente para BLOCK para manter a regra: mudanca relevante com documentacao incoerente deve bloquear.\n\n## Arquivos documentais esperados\n- Revise README.md, docs/**, docs/ai-context.yaml e skills locais conforme os pontos descritos na propria analise gerada.\n\n## Resposta original do modelo\n" + output

output_path = OUTPUT_MAP[MODE]
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(output + "\n", encoding="utf-8")
print(output)

if MODE == "doc-review":
    first_line = output.splitlines()[0].strip().upper()
    if first_line.startswith("BLOCK"):
        sys.exit(2)
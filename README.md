# pipeline-templates

Repositório template para workflows reutilizáveis do GitHub Actions usados na POC de quality gates, AI review, resumo automático de PR e notificação em Slack.

## Conteúdo

- `.github/workflows/reusable-pr-quality.yml`
- `scripts/ci/collect-pr-context.sh`
- `scripts/ci/generate-pr-summary.py`
- `scripts/ci/run_claude_task.py`

## Secrets esperados no GitHub

Estes secrets devem ser configurados no repositório consumidor e repassados ao workflow reutilizável:

- `ANTHROPIC_API_KEY`
- `SONAR_TOKEN`
- `SLACK_WEBHOOK_URL`

## Exemplo de uso no repositório consumidor

```yaml
name: PR Quality

on:
  pull_request:
    types:
      - opened
      - synchronize
      - reopened

jobs:
  pr-quality:
    uses: your-org/pipeline-templates/.github/workflows/reusable-pr-quality.yml@main
    with:
      template-repository: your-org/pipeline-templates
      template-ref: main
      language: java
      java-version: '21'
      working-directory: .
      build-test-command: ./mvnw -B test
      sonar-command: ./mvnw -B verify sonar:sonar -DskipTests=false -Dsonar.projectKey=checkout-api
      ai-context-path: docs/ai-context.yaml
    secrets: inherit
```

## Observações

- O workflow reutilizável foi desenhado para Java e Kotlin no ecossistema JVM, com parâmetros por projeto.
- A step `update-pr-summary` é não bloqueante e atualiza apenas um bloco delimitado na descrição do PR.
- A step `doc-review` é bloqueante.
- A step `code-review-ai` é não bloqueante.
- O Slack só é enviado depois que os gates bloqueantes passam.# pipeline-templates

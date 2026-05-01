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

## Variáveis e secrets para criar no GitHub

Voce precisa criar estes valores em cada repo consumidor.

`Repository variable`:

- `SONAR_HOST_URL`: URL base do seu SonarQube, por exemplo `https://sonarqube.suaempresa.com`.
- `SONAR_ORGANIZATION`: organization key do SonarCloud ou do ambiente Sonar usado pelo projeto.
- `SONAR_PROJECT_KEY`: project key exato configurado no Sonar para aquele repositório.

`Repository secrets`:

- `ANTHROPIC_API_KEY`: token usado nas steps `doc-review`, `update-pr-summary` e `code-review-ai`.
- `SONAR_TOKEN`: token usado na step de analise do SonarQube.
- `SLACK_WEBHOOK_URL`: webhook usado na notificacao final de Slack depois dos gates bloqueantes.

Se algum desses secrets nao existir:

- `ANTHROPIC_API_KEY`: bloqueia `doc-review` e faz as steps nao bloqueantes de IA serem puladas.
- `SONAR_TOKEN`: bloqueia a execucao da step de Sonar quando `enable-sonar: true`.
- `SLACK_WEBHOOK_URL`: nao bloqueia o pipeline, apenas pula a notificacao de Slack.

Se `SONAR_HOST_URL` nao existir, a step de Sonar falha cedo com mensagem explicita. Sem essa configuracao, o scanner tende a assumir `http://localhost:9000`.
Se `SONAR_ORGANIZATION` ou `SONAR_PROJECT_KEY` nao existirem, a step de Sonar tambem falha cedo com mensagem explicita.

Para SonarCloud, voce normalmente encontra esses valores em `Project Information`:

- `SONAR_HOST_URL`: `https://sonarcloud.io`
- `SONAR_ORGANIZATION`: valor exibido como `Organization Key`
- `SONAR_PROJECT_KEY`: valor exibido como `Project Key`

No exemplo do seu `checkout-api`, pela tela enviada:

- `SONAR_HOST_URL=https://sonarcloud.io`
- `SONAR_ORGANIZATION=jeffersonpersonalsonar`
- `SONAR_PROJECT_KEY=jrlcst_checkout-api`

Referencia fixa do template usada nos repositórios consumidores:

- Repositório: `jrlcst/pipeline-templates`
- Workflow: `jrlcst/pipeline-templates/.github/workflows/reusable-pr-quality.yml@main`

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
    uses: jrlcst/pipeline-templates/.github/workflows/reusable-pr-quality.yml@main
    with:
      template-repository: jrlcst/pipeline-templates
      template-ref: main
      language: java
      java-version: '21'
      working-directory: .
      build-test-command: ./mvnw -B test
      sonar-command: ./mvnw -B verify sonar:sonar -DskipTests=false
      sonar-host-url: ${{ vars.SONAR_HOST_URL }}
      sonar-organization: ${{ vars.SONAR_ORGANIZATION }}
      sonar-project-key: ${{ vars.SONAR_PROJECT_KEY }}
      ai-context-path: docs/ai-context.yaml
    secrets: inherit
```

## Observações

- O workflow reutilizável foi desenhado para Java e Kotlin no ecossistema JVM, com parâmetros por projeto.
- A step `update-pr-summary` é não bloqueante e atualiza apenas um bloco delimitado na descrição do PR.
- A step `doc-review` é bloqueante.
- A step `code-review-ai` é não bloqueante.
- O Slack só é enviado depois que os gates bloqueantes passam.

<p align="center">
  <img src="assets/banner.png" alt="Lucifexia Banner" width="100%">
</p>

# ⛧ Lucifexia ☤

<p align="center">
  <a href="https://github.com/Gabrie-yx/lucifexia"><img src="https://img.shields.io/badge/GitHub-Gabrie--yx%2Flucifexia-FFD700?style=for-the-badge&logo=github" alt="GitHub Repository"></a>
  <a href="https://github.com/Gabrie-yx/lucifexia/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Version-v0.20.3-red?style=for-the-badge" alt="Version 0.20.3">
  <img src="https://img.shields.io/badge/OS-Windows%20%7C%20Linux%20%7C%20macOS-blue?style=for-the-badge" alt="Cross-Platform">
</p>

**Lucifexia** é um sistema operacional de IA pessoal autossuficiente, altamente adaptativo e extensível, projetado para rodar nativamente em **Interface Desktop (Electron), TUI Interativa no Terminal, CLI de Alta Performance e Gateway de Mensageria Multicanal**.

O Lucifexia é o único agente de IA com um **loop de aprendizado fechado e autônomo**: ele acumula experiências entre sessões, gera automaticamente novas habilidades (*skills*), aperfeiçoa suas ferramentas durante a utilização, realiza pesquisas textuais de alta velocidade FTS5 no histórico de conversas e constrói um perfil em constante evolução sobre o usuário.

---

## 📋 Sumário
1. [Funcionalidades & Capacidades Detalhadas](#-funcionalidades--capacidades-detalhadas)
2. [Catálogo Completo de Habilidades (Skills)](#-catálogo-completo-de-habilidades-skills)
   - [Engenharia de Software & Desenvolvimento](#1-engenharia-de-software--desenvolvimento)
   - [Criação Visual, Mídia & Design](#2-criação-visual-mídia--design)
   - [Produtividade, Notas & Organização](#3-produtividade-notas--organização)
   - [Pesquisa, Ciência de Dados & MLOps](#4-pesquisa-ciência-de-dados--mlops)
   - [DevOps, Nuvem & Segurança](#5-devops-nuvem--segurança)
   - [Integrações Apple & Smart Home](#6-integrações-apple--smart-home)
3. [Guia Completo de Comandos (CLI & Slash Commands)](#-guia-completo-de-comandos)
4. [Instalação & Configuração Passo a Passo](#-instalação--configuração-passo-a-passo)
5. [Migração Automática do OpenClaw](#-migração-automática-do-openclaw)
6. [Créditos & Atribuição](#-créditos--atribuição)
7. [Licença](#-licença)

---

## 🚀 Funcionalidades & Capacidades Detalhadas

### 🧠 1. Loop de Aprendizado Autônomo e Memória
* **Memória Procedural & Curadoria Automática**: O agente gerencia autonomamente os arquivos `MEMORY.md` e `USER.md`, registrando fatos cruciais, preferências e instruções técnicas aprendidas ao longo das interações.
* **Auto-Criação de Habilidades (Skills)**: Após concluir tarefas complexas ou solucionar bugs desafiadores, o agente sintetiza o procedimento criando novas *skills* reusáveis no diretório `~/.lucifex/skills/`.
* **Auto-Aperfeiçoamento**: Durante a utilização de uma habilidade existente, o agente identifica falhas ou atualizações de comandos e refina o código das *skills* automaticamente.
* **Busca Textual FTS5 & Sumarização**: Histórico persistente em banco SQLite com motor de busca FTS5 (Full-Text Search) e sumarização via LLM para recall instantâneo de contextos de sessões anteriores.
* **Modelagem Dialética de Usuário (Honcho)**: Integração para construir um perfil cognitivo profundo das necessidades e preferências do usuário.
* **Compatibilidade com o Padrão Abeto**: Suporte completo ao padrão [agentskills.io](https://agentskills.io).

### 🖥️ 2. Interface Desktop Nativa (Electron)
* **Design Futurista Obsidian/Red**: Tema elegante em modo escuro profundo com detalhes luminosos em vermelho e preto, raio de borda responsivo e animações suaves.
* **Modo de Voz (Voice Mode)**: Suporte completo à entrada por microfone e resposta por áudio utilizando sintetização fluida (ElevenLabs / Whisper / TTS nativo).
* **Companion Virtual (Pet Component)**: Assistente visual integrado no desktop com animações de estado.
* **Overlay de Estado e Conexão**: Monitoramento gráfico em tempo real do status do gateway, carga de contexto, tokens consumidos e inicialização do agente.

### ⌨️ 3. TUI & CLI de Alto Desempenho
* **Interface TUI Rica**: Construída com `Rich` e `prompt_toolkit`, trazendo suporte a edição multilinha, autocompletar inteligente com tecla `Tab`, histórico de sessões e visualização de diffs.
* **Personalidades Dinâmicas**: Troque instantaneamente a personalidade de resposta do agente via `/personality` (técnica, concisa, kawaii, pirata, noir, filósofo, hype, shakespeare, catgirl, entre outras).
* **6 Backends de Terminal Isolados**: Execute comandos de terminal em ambientes isolados:
  1. **Local**: Terminal local seguro.
  2. **Docker**: Contêineres isolados para testes em sandbox.
  3. **SSH**: Servidores e máquinas remotas.
  4. **Singularity**: Ambientes HPC de alta performance.
  5. **Modal**: Servidores em nuvem serverless sob demanda.
  6. **Daytona**: Ambientes de desenvolvimento serverless que hibernam quando ociosos, reduzindo os custos de infraestrutura a quase zero.

### 🌐 4. Gateway de Mensageria Multicanal (20+ Plataformas)
Execute um único processo de gateway (`lucifex gateway start`) e comunique-se com seu agente através do seu mensageiro favorito com continuidade de conversa entre plataformas:
* **Mensageiros Principais**: Telegram, Discord, Slack, WhatsApp (Cloud API e Web), Signal, Matrix, Mattermost.
* **Comunicação Direta**: Email (SMTP/IMAP), SMS (via Twilio/Twitch).
* **Plataformas Corporativas**: Feishu, DingTalk, WeCom, QQBot, BlueBubbles (iMessage).
* **Integrações de Automação**: Webhooks de entrada/saída e Servidor de API HTTP REST/WebSocket.
* **Transcrição de Voz**: Envie mensagens de áudio pelo WhatsApp ou Telegram e o agente irá transcrever e responder automaticamente.

### ⏰ 5. Automações & Agendamento Cron
* **Cron Agendado em Linguagem Natural**: Agende tarefas recorrentes como *"Envie-me um resumo diário das notícias às 08:00 no Telegram"* ou *"Faça um backup do banco de dados toda sexta-feira às 23:00"*.
* **Entrega Confiável**: O agendador roda em segundo plano e entrega o resultado diretamente no mensageiro ou canal configurado.

### 🔀 6. Subagentes Paralelos & Execução RPC
* **Delegação de Subagentes**: O agente principal pode instanciar subagentes isolados para executar pesquisas longas ou compilações paralelas sem poluir o histórico principal.
* **Execução via Script RPC**: Escreva scripts em Python que chamam ferramentas via RPC, agrupando fluxos de trabalho de múltiplos passos em uma única rodada sem custo de contexto.

### 🏠 7. Suporte Amplificado a Provedores de IA
Troque de modelo instantaneamente usando `lucifex model`:
* **Provedor Local (Ollama)**: Execute modelos locais (como Llama 3, Qwen 2.5, DeepSeek R1 local) com total privacidade e custo zero.
* **Provedores de Nuvem**: OpenRouter, OpenAI (GPT-4o, o1, o3-mini), Anthropic (Claude 3.5 Sonnet, Claude 3.7 Sonnet), Google Gemini (Gemini 2.0 Flash / Pro), DeepSeek (R1, V3), Groq, Mistral, Together AI, Fireworks e Endpoints compatíveis com a API da OpenAI.

### 🔌 8. Protocolo MCP (Model Context Protocol)
* **Cliente MCP Nativo**: Conecte servidores MCP locais ou remotos (por exemplo, ferramentas de navegação web, ferramentas do Obsidian, utilitários do sistema) para expandir instantaneamente o repertório de ferramentas do agente sem modificar o núcleo.

---

## 📚 Catálogo Completo de Habilidades (Skills)

O Lucifexia vem equipado com um ecossistema nativo de **Habilidades Reusáveis** em `skills/` e `optional-skills/`. As habilidades são carregadas sob demanda e instruem o agente a utilizar ferramentas com precisão profissional.

### 1. Engenharia de Software & Desenvolvimento
* **`systematic-debugging` & `autonomous-self-debugging`**: Diagnóstico sistemático de causa raiz em erros de compilação ou execução, isolando logs e aplicando correções sem suprimir exceções.
* **`test-driven-development` (TDD)**: Ciclo de desenvolvimento guiado por testes unitários e de integração (Red-Green-Refactor).
* **`plan`, `spike`, `sdd-skill`**: Elaboração de planos de implementação detalhados, picos de prototipagem rápida e desenvolvimento orientado a especificações técnicas.
* **`codebase-inspection` & `simplify-code`**: Inspeção profunda da arquitetura do repositório, remoção de redundâncias e refatoração limpa.
* **`github-pr-workflow`, `github-issues`, `github-repo-management`**: Fluxo completo de automação no GitHub: criação e revisão de Pull Requests, gerência de repositórios, triagem de issues e releases.
* **`subagent-driven-development`**: Coordenação avançada de múltiplos subagentes trabalhando em paralelo para grandes refatorações.

### 2. Criação Visual, Mídia & Design
* **`baoyu-infographic` & `baoyu-article-illustrator`**: Geração de infográficos visuais e ilustrações estilizadas para artigos e documentações.
* **`manim-video` & `ascii-video`**: Criação de vídeos explicativos com a biblioteca Manim e renderização de vídeos em ASCII art.
* **`p5js` & `pretext`**: Criação de telas interativas com p5.js e visualização gráfica de leiautes.
* **`comfyui`, `blender-mcp`, `unreal-mcp`**: Controle e integração de fluxos de renderização em ComfyUI, Blender e Unreal Engine via MCP.
* **`popular-web-designs` & `claude-design`**: Criação de interfaces web modernas com HSL tailoring, micro-animações e componentes reutilizáveis.

### 3. Produtividade, Notas & Organização
* **`obsidian`**: Conexão total com o cofre Obsidian — leitura, criação e atualização de notas, gerenciamento de tags, projetos e diários.
* **`google-workspace`, `notion`, `airtable`**: Leitura e manipulação de documentos, planilhas, bases de dados Notion e tabelas Airtable.
* **`ocr-and-documents` & `nano-pdf`**: Reconhecimento óptico de caracteres em imagens e extração/estruturação de documentos PDF.
* **`petdex`**: Acompanhamento e gerenciamento do estado dos assistentes virtuais (pets) no app Desktop.

### 4. Pesquisa, Ciência de Dados & MLOps
* **`arxiv` & `research-paper-writing`**: Pesquisa bibliográfica de artigos científicos no ArXiv e redação formatada em LaTeX.
* **`jupyter-live-kernel`**: Execução de código e análise de dados em tempo real em kernels do Jupyter Notebook.
* **`huggingface-hub`, `vllm`, `llama-cpp`**: Download e gerenciamento de modelos do Hugging Face, inferência de altíssima velocidade com vLLM e llama.cpp.
* **`unsloth` & `axolotl`**: Fine-tuning e treinamento otimizado de modelos de linguagem de grande porte.
* **`osint-investigation` & `blogwatcher`**: Investigação OSINT de fontes abertas e monitoramento de atualizações em blogs.

### 5. DevOps, Nuvem & Segurança
* **`docker-management`**: Criação, inicialização e gerenciamento de contêineres e redes Docker.
* **`lucifex-s6-container-supervision`**: Gerenciamento e supervisão de processos contínuos via S6 supervisor em contêineres.
* **`web-pentest` & `oss-forensics`**: Testes de penetração em aplicações web e análise forense em código aberto.
* **`openclaw-migration`**: Migração interativa assistida de memórias e configurações do OpenClaw.

### 6. Integrações Apple & Smart Home
* **`apple-notes`, `apple-reminders`, `imessage`, `findmy`**: Ações diretas no macOS/iOS para notas, lembretes, iMessage e busca de dispositivos.
* **`openhue`**: Controle inteligente de lâmpadas e autômatos residenciais via Philips Hue API.

---

## 🛠️ Guia Completo de Comandos

### Comandos da CLI (`lucifex <subcomando>`)

| Comando | Descrição |
| :--- | :--- |
| `lucifex` | Inicia o chat interativo no terminal (TUI) |
| `lucifex model` | Abre o menu interativo para escolher o provedor e modelo de IA |
| `lucifex tools` | Habilita ou desabilita ferramentas do agente |
| `lucifex setup` | Assistente interativo de configuração inicial |
| `lucifex status` | Exibe o relatório de status de todos os componentes |
| `lucifex gateway start` | Inicia o gateway de mensageria em segundo plano |
| `lucifex gateway stop` | Interrompe o gateway de mensageria |
| `lucifex cron` | Gerencia os agendamentos de tarefas recorrentes |
| `lucifex update` | Atualiza o Lucifexia diretamente do repositório GitHub |
| `lucifex doctor` | Diagnostica problemas de instalação, chaves e dependências |
| `lucifex logs` | Exibe e acompanha em tempo real os logs de execução |

### Comandos de Barra (Slash Commands no Chat)

| Slash Command | Função |
| :--- | :--- |
| `/new` ou `/reset` | Inicia uma nova conversa limpa descartando o contexto atual |
| `/model [provedor:modelo]` | Altera o modelo de linguagem da sessão ativa |
| `/personality [nome]` | Altera a personalidade de resposta (ex: `kawaii`, `noir`, `technical`) |
| `/skills` | Exibe as habilidades ativas e permite invocar uma skill diretamente |
| `/retry` | Tenta gerar novamente a última resposta do assistente |
| `/undo` | Desfaz a última mensagem trocada |
| `/compress` | Resume o histórico de contexto mantendo os pontos técnicos vitais |
| `/usage` | Exibe os tokens consumidos e custos acumulados na sessão |
| `/insights [dias]` | Gera um relatório de insights sobre seu uso recente do agente |
| `/stop` | Interrompe imediatamente qualquer execução de ferramenta em andamento |
| `/platforms` | Exibe o status das conexões ativas do gateway |

---

## 📦 Instalação & Configuração Passo a Passo

### Windows (Nativo via PowerShell)
Execute o instalador automático no PowerShell:

```powershell
iex (irm https://raw.githubusercontent.com/Gabrie-yx/lucifexia/main/scripts/install.ps1)
```

### Linux, macOS, WSL2 & Termux
Execute o instalador em ambiente Bash:

```bash
curl -fsSL https://raw.githubusercontent.com/Gabrie-yx/lucifexia/main/scripts/install.sh | bash
```

*O instalador configura o ambiente virtual Python, instala o `uv`, Node.js, `ripgrep`, `ffmpeg` e todas as dependências necessárias de forma isolada em `~/.lucifex/`.*

---

## 🔄 Migração Automática do OpenClaw

Se você utilizava o OpenClaw anteriormente, o Lucifexia realiza a migração automática de todas as suas configurações, arquivos de persona, histórico e chaves API.

```bash
lucifex claw migrate              # Migração interativa completa
lucifex claw migrate --dry-run    # Simulação para visualizar o que será migrado
lucifex claw migrate --overwrite  # Migra sobrescrevendo conflitos
```

---

## 📜 Créditos & Atribuição

O **Lucifexia** foi desenvolvido a partir da arquitetura de agente criada pela equipe da **Nous Research** no projeto open-source **Hermes Agent** (disponibilizado sob a licença **MIT**).

Desejamos registrar nossa profunda admiração e agradecimento à **Nous Research** e a toda a comunidade de código aberto por desenvolverem o núcleo do agente sobre o qual expandimos a identidade visual, a aplicação Desktop Electron, os ajustes de interface e as customizações do **Lucifexia**.

---

## 📄 Licença

Distribuído sob a Licença **MIT** — consulte o arquivo [LICENSE](LICENSE) para obter mais informações.

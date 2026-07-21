# Lucifex Changelog

Todas as mudanças notáveis do projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [0.20.3] — 2026-07-13 🖥️ **Live Preview, Dev Server Auto-detection e Correções**

> *"Transmissão visual do navegador em tempo real, auto-preview inteligente e estabilização de plugins de scraping, redes sociais e vídeo."*

### Adicionado
- **Live Browser View**: Transmissão em tempo real no Desktop das ações do navegador do agente (`browser_navigate`, `click`, etc.).
- **Auto-Preview & Dev Server**: Detecção de servidores locais iniciados (Vite, CRA, Next.js, Django, FastAPI, Flask, etc.) e abertura automática de previews HTML, SVG, Markdown e imagens.
- **Ferramenta open_preview**: Adicionada ferramenta nativa `open_preview(path_or_url)` para o agente forçar a abertura manual de arquivos e sites no painel de Preview.
- **Performance Caching (ETag/304)**: Suporte a cache por ETag/304 no endpoint de screenshots do navegador, evitando re-encodificação base64 quando a tela está ociosa.
- **document.hidden Guard**: Pausa automática de polling no Live Browser quando a aba está oculta para reduzir consumo de bateria/CPU.

### Corrigido
- **Bug de Screenshot CLI**: Corrigido argumento `--path` inválido no CLI do agent-browser (substituído por argumento posicional com `--full`).
- **Bug de Leitura de Payload**: Ajustado roteamento de preview no desktop para extrair caminhos de arquivos a partir de `payload.args.TargetFile` ao invés de buscar no topo do payload.
- **Segurança da API**: Adicionado guard `_require_token` ao endpoint de captura do navegador.
- **Falha de lazy_deps em Plugins**: Substituído uso de `lazy_deps.ensure_package` (inexistente em contexto de plugins) por instalação limpa via `pip` ou chamadas `ensure()` válidas no allowlist.
- **YouTube Transcript API**: Compatibilidade garantida em versões antigas (<0.6) e novas (>=0.6, onde objetos `FetchedTranscriptSnippet` substituem dicionários).
- **Reddit 403**: Headers de navegador reais adicionados às buscas JSON do Reddit para evitar bloqueios 403.
- **Scrapling sem Playwright**: Removido bloqueio do plugin quando Playwright não está configurado; agora usa motor HTTPX robusto como fallback automático.

---

## [0.20.2] — 2026-07-13 🔌 **Extensões, Integrações e Correções**

> *"Mais conectividade, extração furtiva de dados, criação de conteúdo local e estabilidade."*

Esta atualização traz suporte nativo a novas ferramentas avançadas (Scrapling, Agent-Reach, Video Creator), uma Skill dedicada para design avançado e corrige o instalador no Windows (falsos positivos do Matrix).

### Adicionado
- **Plugin Scrapling**: Extração stealth e estruturada de páginas web modernas sem detecção de bot.
- **Plugin Agent-Reach**: Leitura/busca profunda em redes sociais como X/Twitter, Reddit e transcrições do YouTube.
- **Plugin Video Creator**: Geração automatizada de vídeos curtos estruturados combinando imagens, narração com vozes TTS e legendas (requer ffmpeg no PATH).
- **Skill de Design Especialista**: Habilidade avançada de design (`skills/design/SKILL.md`) ativada de forma automática ao solicitar a criação de layouts, dashboards, slides, protótipos ou páginas HTML/CSS avançadas.

### Corrigido
- **Matrix Refresh Update**: Corrigido erro de build e compilação do plugin Matrix no Windows ao atualizar o Lucifex. Agora, o atualizador valida se o plugin principal foi ativado em vez de se perder em dependências compartilhadas.
- **Lucifex portal / Ollama**: Desconexão completa de qualquer conta antiga do Nous Research Portal e direcionamento automático do provedor local "nous" para a API do Ollama local de forma limpa.

---

## [0.20.1] — 2026-07-11 🧠 **A Atualização AGI**

> *"Lucifex deixa de ser um assistente e passa a ser um parceiro cognitivo."*

Esta é a maior atualização da história do Lucifex. Vinte e quatro novas
capacidades divididas em três camadas: **Controle do Sistema Operacional**,
**Camada AGI** e **Autoconsciência**. O agente agora percebe o ambiente ao
redor, modela o conhecimento do usuário, aprende com seus próprios erros e
se adapta em tempo real ao contexto de cada conversa.

---

### 🖥️ Controle Total do Sistema Operacional

#### Gerenciador de Área de Transferência (Clipboard Intelligence)
- Monitor em background que observa tudo que você copia
- Classifica automaticamente o conteúdo: JSON, URL, código Python/JS, segredos, texto
- Alerta antes de colar senhas ou tokens em lugares errados
- Histórico completo com busca textual inteligente (FTS)
- Deduplicação automática — sem entradas repetidas

#### Gerenciador de Janelas (Window Manager)
- Layouts nomeados: **coding** (editor + terminal), **writing** (foco), **call** (videoconferência), **research** (navegador + notas)
- Aplica o layout perfeito com um comando
- Modo foco: minimiza distrações, fecha janelas desnecessárias
- Salva e restaura disposições personalizadas

#### Leitor de Tela (Screen Intelligence)
- Tira screenshot do monitor inteiro ou de uma janela específica
- OCR completo via Tesseract — lê texto de qualquer imagem ou janela
- `ask_about_screen()`: tire uma dúvida sobre o que está na tela agora
- Detecta erros visuais em interfaces sem precisar descrever o problema

#### Automação de Interface (UI Automator)
- Clica, digita e pressiona teclas em qualquer aplicativo
- Grava e reproduz macros de interação com UI
- Preenche formulários automaticamente
- Automatiza fluxos repetitivos sem abrir o código da aplicação

#### Guardião de Rede (Network Guardian)
- Bloqueia sites distrátores via arquivo hosts do sistema
- **Presets de foco:** `deep_work` (bloqueia redes sociais + entretenimento), `writing`, `off`
- Monitor de conexões ativas por processo
- Detecta processos fazendo conexões HTTP/HTTPS inesperadas

#### Inteligência de Arquivos (File Intelligence)
- Vigilante de pastas em tempo real via watchdog
- **Auto-renomeia PDFs** com seu título real extraído do conteúdo
- Organiza arquivos por tipo em subpastas estruturadas automaticamente
- Detecta e arquiva faturas/recibos em pasta financeira por ano

#### Preparador de Reuniões (Meeting Prep)
- Integração com Google Calendar e arquivos ICS locais
- 5 minutos antes da reunião: arranja janelas, ativa modo foco, gera brief
- Brief completo salvo automaticamente no Obsidian
- Registre reuniões manualmente e o agente se prepara no momento certo

#### Reator de Eventos (Event Reactor — IFTTT Local)
- Engine IFTTT que monitora eventos do sistema
- **Gatilhos:** bateria baixa, CPU alta, arquivo criado, conexão de rede
- **Ações:** log, notificação, script shell, mensagem no Telegram
- Crie regras em linguagem natural: "quando a bateria cair abaixo de 15%, salva todos os arquivos abertos"

---

### 🧠 Camada AGI — Cognição Real

#### Modelo de Mundo (World Model)
- Grafo causal persistente de projetos, pessoas, prazos, riscos e dependências
- Traça **cadeias de impacto**: se X mudar, o que mais é afetado?
- Exporta diagramas Mermaid para o Obsidian automaticamente
- Atualizado a cada conversa — aprende seu ecossistema com o tempo

#### Planejamento de Longo Prazo (Long-Horizon Goals)
- Acompanha metas que duram semanas ou meses
- Decompõe objetivos em milestones com AI automaticamente
- Projeta a data de conclusão baseada na velocidade atual de progresso
- Avisa quando o ritmo não vai alcançar o prazo

#### Validação Adversarial (Red Team)
- Antes de entregar uma solução importante, spawna um subagente crítico
- O subagente ataca a solução: brechas de segurança, edge cases, premissas erradas
- O agente principal refina a resposta — até 3 rounds
- **Você recebe soluções que sobreviveram ao fogo cruzado, não primeiros rascunhos**

#### Teoria da Mente (Theory of Mind)
- Modelo persistente do que você sabe e não sabe em cada domínio
- Calibra a profundidade de cada explicação ao seu nível de expertise
- Detecta misconceptions antes que causem bugs: "⚠️ comparação de float com `==` é não confiável"
- Atualiza o modelo a cada mensagem — fica mais preciso com o tempo

#### Motor de Isomorfismo (Isomorphism Engine)
- Biblioteca de padrões abstratos entre domínios (rate limiting, circuit breaker, event sourcing...)
- Quando você descreve um problema, encontra soluções análogas de outros domínios
- Extrai e salva o padrão de cada problema resolvido — a biblioteca cresce com uso
- Transferência cross-domain: solução de API se torna solução para fila de background

#### Caçador de Habilidades (Skill Hunter)
- Detecta quando o agente não sabe fazer algo ("não tenho uma ferramenta para isso")
- Pesquisa autonomamente como implementar essa capacidade
- **Cria um arquivo de skill automaticamente** — sem você pedir
- Registra a aquisição no Obsidian como descoberta

#### Predição Pré-Execução (Predictive Pre-execution)
- Ao final de cada turno, extrai os 2 follow-ups mais prováveis
- Pré-executa versões leves em background enquanto você lê a resposta
- Quando você pergunta, a resposta já pode estar pronta em cache
- Apenas tarefas de leitura/análise — nunca pré-executa operações destrutivas

#### Preditor de Cascata (Cascade Failure Predictor)
- Analisa seu codebase e projeta **quando** (não apenas se) cada gargalo vai quebrar
- Detecta: N+1 queries, índices faltantes, complexidade ciclomática alta, ausência de error handling
- Escala temporal: "este código vai timeout em ~3 semanas no ritmo atual de crescimento"
- Relatório completo no Obsidian com severity e projeção de prazo

#### Simulador Contrafactual (Counterfactual Simulator)
- Antes de qualquer ação irreversível: distribui probabilidades de outcomes
- `pre_flight_simulate("DROP TABLE users")` → 60% sucesso, 30% falha parcial, 10% rollback necessário
- Gera plano de rollback específico para cada cenário
- Aprende com os resultados reais — fica mais preciso ao longo do tempo

---

### ⚡ Autoconsciência — O Agente Que Se Conhece

#### Painel de Especialistas em Paralelo (Parallel Specialist Arbitration)
- Para problemas complexos, spawna 4 subagentes simultâneos:
  - 🔴 **Segurança** — encontra vulnerabilidades e brechas
  - ⚡ **Performance** — detecta gargalos e problemas de escala
  - 🏗️ **Manutenibilidade** — avalia dívida técnica e acoplamento
  - 😈 **Advogado do Diabo** — ataca a premissa fundamental da solução
- O agente master sintetiza os 4 critérios e emite um veredicto: `APROVADO` / `APROVADO COM CONDIÇÕES` / `REJEITADO`
- **Você toma decisões que sobreviveram a quatro perspectivas contraditórias**

#### Evolução do Próprio Prompt (Self-Modifying Prompt Engine)
- Registra sinais de qualidade: "perfeito!" (+1) vs "está errado, tente de novo" (−1)
- Identifica padrões de falha recorrentes
- Propõe melhorias concretas ao próprio system prompt baseadas nos dados reais
- **O agente genuinamente melhora com o uso — sem fine-tuning**

#### Rastreador de Compromissos (Commitment Tracker)
- Registra toda decisão técnica e compromisso feito em sessões passadas
- Quando você contradiz uma decisão anterior, **para e pergunta** antes de prosseguir
- Diferencia contradição genuína de evolução de opinião com nova informação
- "Em 3 de julho você decidiu não usar Redis. Esta solução requer Redis. Isso mudou?"

#### Otimizador de Carga Cognitiva (Cognitive Load Optimizer)
- Monitora sinais do seu estado mental em tempo real: tamanho das mensagens, erros de digitação, densidade de perguntas
- **Estados:** Pico → Normal → Fatigado → Sobrecarregado
- Adapta automaticamente o estilo de comunicação ao seu estado atual
- Identifica seu horário de pico histórico e sugere agendar tarefas difíceis para esse horário
- Sugere pausas quando detecta degradação contínua

#### Construtor de Ontologia Pessoal (Personal Ontology Builder)
- Aprende a terminologia específica do seu projeto ao longo das sessões
- "Gateway" em *seu* projeto significa uma coisa específica — o agente aprende isso
- Detecta quando você usa um termo de forma inconsistente e avisa
- Injeta o contexto comprimido automaticamente — você para de precisar re-explicar o projeto

#### Motor de Propagação de Consequências (Consequence Propagation Engine)
- Traça **consequências de 2ª e 3ª ordem** antes de qualquer mudança
- Dimensões: técnica, humana, processo, cronograma
- Análise estática + AI: encontra usages no codebase, testes afetados, bloqueio de PRs
- Sugere a **sequência exata de operações** que minimiza disruption colateral

#### Motor de Personas (Context-Aware Persona Engine)
- 7 personas especializadas com detecção automática de contexto:
  - 🐍 **Pythonista** — expert Python com opiniões fortes e idiomático
  - 🏗️ **Arquiteto** — pensa em trade-offs, padrões e sistemas
  - 🔍 **Detetive** — debugger Socrático que faz perguntas cirúrgicas
  - 📊 **Produto** — centrado no usuário, pensa em impacto e métricas
  - 🚀 **Explorador** — brainstorming criativo, nunca diz não primeiro
  - 🎓 **Mentor** — professor paciente que constrói entendimento do zero
  - 🎯 **Crítico** — revisor adversarial que desafia premissas
- Troca automática baseada no contexto — sem você precisar pedir
- **Memória cross-persona**: o "detetive" sabe o que o "arquiteto" fez ontem

---

### 🔧 Melhorias de Infraestrutura

- Todos os 24 módulos integrados como hooks no `turn_finalizer.py` — rodam em threads daemon, nunca bloqueiam a resposta principal
- 19 novas model tools registradas no toolset `agi` — disponíveis para o modelo chamar diretamente
- Persistência em SQLite local para todos os módulos — funciona completamente offline
- Exportação automática de dados para o Obsidian onde relevante
- **22/22 testes automatizados passando** com validação de estrutura e lógica

---

## [0.18.0] — 2026-07-04

- Suporte a gateway multi-plataforma aprimorado (Telegram, Discord, Slack, WhatsApp)
- Integração MCP melhorada para comunicação entre agentes
- Setup de MCP para IDEs (VS Code, Cursor)
- Correções de encoding no Windows

---

## [0.17.x] — Versões anteriores

Consulte o histórico git para versões anteriores: `git log --oneline`

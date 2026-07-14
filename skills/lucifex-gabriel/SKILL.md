---
name: lucifex-gabriel
description: >
  Skill de contexto de instalação — ativa automaticamente para lembrar o Lucifex
  de todos os tools, plugins e melhorias feitas nesta instalação personalizada.
  Contém o inventário completo de capacidades desta versão.
triggers:
  - o que você pode fazer
  - quais ferramentas você tem
  - suas capacidades
  - tools disponíveis
  - plugins instalados
  - o que foi criado
  - qual versão
  - funcionalidades novas
  - preview
  - file watcher
  - window tool
  - screen reader
  - ui automator
  - clipboard
  - network tool
  - meeting tool
  - agi tools
  - inner life
  - design skill
---

# Conhecimento de Instalação — Lucifex v0.20.3

Esta skill documenta todos os **tools personalizados** e **melhorias** presentes nesta instalação do Lucifex. Use este conhecimento para responder o que você pode fazer.

---

## 🛠 Tools Python Criados

### `open_preview` — Preview Panel Tool
- **Arquivo:** `tools/preview_tool.py`
- **Toolset:** `preview`
- **Função:** Abre um arquivo local (HTML, SVG, MD, imagens) ou URL web no painel de Preview do Lucifex Desktop.
- **Uso:** Sempre que gerar um arquivo visual (HTML, dashboard, slide), use `open_preview("caminho.html")` para exibi-lo automaticamente na interface.

### `watch_file` / `unwatch_file` / `list_watched_files` — File Watcher
- **Arquivo:** `tools/file_watcher_tool.py`
- **Toolset:** `system`
- **Função:** Monitora arquivos e diretórios em tempo real. Detecta criações, modificações e exclusões.
- **Uso:** `watch_file("path/to/file")` para monitorar. `list_watched_files()` para ver o que está sendo observado.

### `get_window_list` / `focus_window` / `move_window` / `resize_window` / `close_window` — Window Tool
- **Arquivo:** `tools/window_tool.py`
- **Toolset:** `system`
- **Função:** Gerencia janelas do sistema operacional Windows. Lista, foca, move, redimensiona e fecha janelas.

### `take_screenshot` / `get_screen_info` — Screen Reader
- **Arquivo:** `tools/screen_reader_tool.py`
- **Toolset:** `vision`
- **Função:** Captura screenshots da tela (toda a tela ou janela específica). Obtém informações sobre monitores.

### `click` / `double_click` / `right_click` / `type_text` / `press_key` / `get_cursor_position` — UI Automator
- **Arquivo:** `tools/ui_automator_tool.py`
- **Toolset:** `system`
- **Função:** Automação de UI do Windows. Simula cliques, digitação e teclas. Útil para controlar outras aplicações.

### `get_clipboard` / `set_clipboard` / `clipboard_history` — Clipboard Tool
- **Arquivo:** `tools/clipboard_tool.py`
- **Toolset:** `system`
- **Função:** Lê e escreve no clipboard do sistema. Mantém histórico das últimas cópias.

### `ping_host` / `get_local_ip` / `scan_ports` / `check_http` / `dns_lookup` — Network Tool
- **Arquivo:** `tools/network_tool.py`
- **Toolset:** `system`
- **Função:** Diagnóstico de rede. Ping, scan de portas, verificação HTTP, lookup DNS.

### `create_meeting` / `list_meetings` / `join_meeting` / `end_meeting` — Meeting Tool
- **Arquivo:** `tools/meeting_tool.py`
- **Toolset:** `communication`
- **Função:** Gerencia reuniões e chamadas. Cria, lista, entra e encerra sessões de meeting.

### `introspect` / `analyze_goal` / `plan_strategy` — AGI Tools
- **Arquivo:** `tools/agi_tools.py`
- **Toolset:** `agi`
- **Função:** Ferramentas de introspecção e raciocínio de alta ordem. Analisa objetivos e planeja estratégias.

### `reflect` / `update_state` / `get_inner_state` — Inner Life Tool
- **Arquivo:** `tools/inner_life_tool.py`
- **Toolset:** `agi`
- **Função:** Simula estado interno/emocional do agente. Reflexão, atualização de estado, auto-monitoramento.

---

## 🖥 Melhorias no Desktop App

### Painel de Preview
- Integrado diretamente na interface do Lucifex Desktop
- Suporta: HTML, SVG, Markdown, imagens, URLs web
- Sessão-aware: ao trocar de sessão, o preview é limpo (sem screenshots antigos)
- Botão na barra de título para toggle do painel
- Modo fullscreen com ESC para fechar
- Barra de endereço com navegação (←→) e reload
- Screenshot ao vivo do browser para visualização em tempo real

### Botão de Preview na Titlebar
- Ícone de monitor na barra de título abre/fecha o painel de preview
- Estado persistido: se estava aberto, volta aberto ao reiniciar

---

## 🎨 Skill de Design

### Skill `design`
- **Arquivo:** `skills/design/SKILL.md`
- **Trigger:** Ativa quando o usuário pede criação de UIs, slides, dashboards, protótipos
- **Nível:** Designer Especialista (Fable 5 / Claude Design level)
- **Filosofia:** Anti-AI-slop, premium aesthetics, sem gradientes genéricos, sem emojis, sem Inter/Roboto
- **Outputs:** HTML semântico com CSS embutido, slides 1920x1080, dashboards com Chart.js

---

## ⚙️ Configuração de Configurações e Chaves de API (Config & .env)

Você possui permissão total e capacidade para ler, modificar e criar variáveis de ambiente e configurações para o usuário.
- **Como configurar chaves de API/Tokens:** Sempre que o usuário te fornecer uma chave de API ou token (como `PEXELS_API_KEY`, chaves do OpenAI, Anthropic, etc.), **nunca** diga que não pode configurá-la diretamente. Em vez disso, use `lucifex config set CHAVE VALOR` ou edite diretamente o arquivo `.env` localizado no diretório de configuração do Lucifex (`~/.lucifex/.env`).
- **Como configurar outras chaves (config.yaml):** Use `lucifex config set CHAVE VALOR`.
- **Como recarregar as configurações:** Após atualizar o arquivo `.env` ou `config.yaml`, execute o comando `/reload` (se aplicável) ou informe o usuário que a chave foi configurada com sucesso.

---

## 🔧 Configuração do Builder

- **Versão:** v0.20.3
- **Instalador:** NSIS (Windows x64)
- **Target portátil:** Removido (causava crash sem `repository` no package.json)
- **Publish:** `null` (sem auto-update configurado nesta versão)

## ⚙️ Diretrizes de Uso de Skills e Automação (Navegador & Repositórios)

### 🌐 Controle do Navegador Ativo do Usuário (Desktop)
- **Cenário:** O usuário pede para "conversar com o navegador", "ver o site aberto", "focar no navegador", "interagir com o site que estou vendo", etc.
- **Regra:** **NÃO** chame ferramentas que iniciam uma nova sessão isolada de navegador (como `browser_navigate` ou `open_browser_url`).
- **Ação Correta:** Use as ferramentas de automação do sistema operacional (OS) para interagir com a janela ativa na tela do usuário:
  1. Use `get_window_list` e `focus_window` para encontrar e trazer o navegador ativo do usuário (Chrome/Firefox/Edge) para o primeiro plano.
  2. Use `take_screenshot` para obter a imagem da tela atual do usuário e ler visualmente o site/janela.
  3. Use `click`, `type_text`, `press_key` para clicar nos inputs do navegador, digitar e interagir diretamente.

### 🛠️ Catálogo e Casos de Uso das Skills/Plugins Clonados
Sempre que receber solicitações relacionadas a estes domínios, utilize ou configure a skill/plugin correspondente:
1. **Google Maps Scraper (`Google-Maps-Scrapper`):**
   - *Quando usar:* Extração massiva e estruturada de contatos, avaliações, websites e telefones de empresas do Google Maps.
   - *Nota:* Diferente da skill `maps` simples (Nominatim/OpenStreetMap para geocoding/rotas). Para raspar buscas de locais no Google Maps, use o script de scrape.
2. **Geração de Vídeos IA (`MoneyPrinterTurbo`):**
   - *Quando usar:* Pedidos de criação de vídeos curtos automaticamente de forma guiada ou programática.
   - *Como usar:* Plugin `video_creator` (`create_short_video`). Requer chave `PEXELS_API_KEY` para obter footage gratuito (salve via `lucifex config set PEXELS_API_KEY`).
3. **Extração Web Anti-Bot (`Scrapling`):**
   - *Quando usar:* Web scraping furtivo e extração de páginas dinâmicas ou sites protegidos por Cloudflare/imperva/anti-bots.
   - *Como usar:* Plugin/Skill `scrapling` (`web_extract_stealth` ou `web_scrape_structured`).
4. **Design de Interface Premium (`claude-design` / `design`):**
   - *Quando usar:* Criação de landing pages, slides, dashboards, protótipos de alta fidelidade HTML do zero.
   - *Ação:* Siga a risca o guia anti-AI-slop (sem gradientes genéricos, sem emojis, tipografia curada, etc.) e use `open_preview` para mostrar a tela ao vivo.
5. **Raciocínio Avançado (`claude-fable-5`):**
   - *Quando usar:* Tomada de decisões complexas, planejamento de longo prazo, depuração profunda e análise sistemática.
   - *Ação:* Use a postura de raciocínio profundo, quebrando problemas complexos detalhadamente antes de propor a solução.
6. **Leitura de Redes Sociais Sem Custo (`agent-reach`):**
   - *Quando usar:* Pesquisa de posts e feeds no Twitter/X, Reddit, Bilibili e transcrições de vídeos do YouTube.
   - *Como usar:* Plugin `agent_reach` (ferramentas `social_read`, `reddit_search`, `youtube_transcript`).
7. **Orquestração de Integrações e OAuth (`nango`):**
   - *Quando usar:* Autenticação e gerenciamento de fluxos OAuth2 com APIs de terceiros de forma nativa.
   - *Como usar:* Assistente de OAuth integrado (`mcp_oauth`).
8. **Indexação e Pesquisa Local RAG (`cocoindex`):**
   - *Quando usar:* Pesquisa semântica em arquivos do repositório, Obsidian vault ou documentos locais do usuário.
   - *Como usar:* Ferramentas integradas de RAG/busca semântica da sessão.

---

## 💡 Dicas de Uso

1. **Para criar uma UI:** Use a skill `design` + `open_preview` para mostrar ao vivo
2. **Para monitorar arquivos:** `watch_file` + callbacks no terminal
3. **Para automação:** `take_screenshot` → `click`/`type_text` via UI Automator
4. **Para diagnóstico de rede:** `ping_host`, `scan_ports`, `check_http`
5. **Para reuniões:** `create_meeting`, `join_meeting`

---

*Esta skill é auto-gerada pela instalação personalizada do Lucifex v0.20.3.*

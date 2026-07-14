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

## 🔧 Configuração do Builder

- **Versão:** v0.20.3
- **Instalador:** NSIS (Windows x64)
- **Target portátil:** Removido (causava crash sem `repository` no package.json)
- **Publish:** `null` (sem auto-update configurado nesta versão)

---

## 💡 Dicas de Uso

1. **Para criar uma UI:** Use a skill `design` + `open_preview` para mostrar ao vivo
2. **Para monitorar arquivos:** `watch_file` + callbacks no terminal
3. **Para automação:** `take_screenshot` → `click`/`type_text` via UI Automator
4. **Para diagnóstico de rede:** `ping_host`, `scan_ports`, `check_http`
5. **Para reuniões:** `create_meeting`, `join_meeting`

---

*Esta skill é auto-gerada pela instalação personalizada do Lucifex v0.20.3.*

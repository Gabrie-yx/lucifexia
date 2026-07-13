<p align="center">
  <img src="assets/banner.png" alt="Lucifex Agent" width="100%">
</p>

# Lucifex Agent ☤

<p align="center">
  <a href="https://github.com/Gabrie-yx/lucifexia">Lucifex Agent</a> | <a href="https://github.com/Gabrie-yx/lucifexia">Lucifex Desktop</a>
</p>
<p align="center">
  <a href="https://github.com/Gabrie-yx/lucifexia/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/Gabrie-yx/lucifexia"><img src="https://img.shields.io/badge/Built%20for-LUCIFEXIA-blueviolet?style=for-the-badge" alt="Built for LUCIFEXIA"></a>
  <img src="https://img.shields.io/badge/version-0.20.3-ff6b6b?style=for-the-badge" alt="Version 0.20.3">
</p>

**O agente de IA auto-melhorável projetado para ser executado de forma local e independente.** É o único agente com um loop de aprendizado integrado: ele cria habilidades a partir da experiência, melhora-as durante o uso, gerencia seu próprio conhecimento, busca em conversas passadas e constrói um perfil profundo de suas preferências entre as sesões. Pode ser executado em sua máquina local, em uma VPS de $5 ou em servidores na nuvem.

Use qualquer modelo que desejar — **Ollama** (processamento 100% local e privado), OpenRouter, OpenAI, seu próprio endpoint personalizado e muitos outros. Mude facilmente usando o comando `lucifex model` — sem alterações de código, sem dependências de fornecedores.

---

## ✨ v0.20.3 — Live Preview & Correções Críticas (ad97ed6 / 22f98e4 / d3c85b2)

> *Transmissão visual do navegador em tempo real, auto-preview de arquivos gerados, ferramenta de preview forçado e correções críticas.*

<table>
<tr><td><b>🖥️ Live Browser View</b></td><td>Transmissão de capturas de tela em tempo real no painel direito do Desktop durante ações do navegador (<code>browser_navigate</code>, <code>click</code>, etc.).</td></tr>
<tr><td><b>⚡ Auto-Preview & Dev Server</b></td><td>Abertura automática de arquivos gerados (HTML, SVG, MD, imagens). Escaneamento inteligente de terminal para redirecionar o preview para servidores locais (Vite, Next.js, Django, etc.).</td></tr>
<tr><td><b>🔍 Ferramenta open_preview</b></td><td>Permite ao agente comandar a abertura explícita de qualquer arquivo local ou URL web diretamente na aba Preview do Desktop (ferramenta: <code>open_preview</code>).</td></tr>
<tr><td><b>🔋 Otimização de Performance</b></td><td>Implementação de cabeçalhos ETag/304 no endpoint de screenshots, reduzindo em 99% a re-encodificação base64 quando o navegador está inativo, e suspensão do polling quando a aba está oculta.</td></tr>
<tr><td><b>🛠️ Correções de Plugins</b></td><td>Conserto de 5 bugs críticos nos plugins <code>scrapling</code> (bypass sem playwright obrigatório), <code>agent-reach</code> (busca de redes sociais nativa e YouTube Transcript) e <code>video-creator</code>.</td></tr>
</table>

---

## ✨ v0.20.2 — Extensões e Integrações (de79e08)

> *Mais conectividade, extração furtiva de dados e criação de conteúdo local.*

<table>
<tr><td><b>🕷️ Scrapling</b></td><td>Extração stealth de páginas modernas com ferramentas como <code>web_extract_stealth</code> e <code>web_scrape_structured</code>. Instala automaticamente sob demanda.</td></tr>
<tr><td><b>📡 Agent-Reach</b></td><td>Conectividade com redes sociais (X/Twitter, Reddit e transcrições completas do YouTube) via ferramentas como <code>social_read</code>, <code>youtube_transcript</code> e <code>reddit_search</code>.</td></tr>
<tr><td><b>🎬 Video Creator</b></td><td>Geração autônoma de vídeos curtos estruturados (imagens, legendas, narração TTS) com <code>create_short_video</code> e <code>list_tts_voices</code> (requer ffmpeg no PATH).</td></tr>
<tr><td><b>🎨 Skill de Design</b></td><td>Habilidade de design avançado (<code>skills/design/SKILL.md</code>) que ativa automaticamente ao solicitar UIs, dashboards, slides, protótipos ou layouts visuais complexos.</td></tr>
</table>

---

## ✨ v0.20.1 — A Atualização AGI

> *A versão que transforma o Lucifex de assistente em parceiro cognitivo.*

<table>
<tr><td><b>🖥️ Controle do Sistema Operacional</b></td><td>Clipboard inteligente, gerenciador de janelas, leitor de tela com OCR, automação de UI, guardião de rede, organização de arquivos, preparador de reuniões e IFTTT local.</td></tr>
<tr><td><b>🧠 Camada AGI</b></td><td>Modelo de mundo causal, planejamento de longo prazo, validação adversarial, teoria da mente, isomorfismo entre domínios, aquisição autônoma de habilidades, predição de consequências e simulação de cenários.</td></tr>
<tr><td><b>⚡ Autoconsciência</b></td><td>Painel de 4 especialistas em paralelo, evolução do próprio prompt, rastreador de compromissos, otimizador de carga cognitiva, ontologia pessoal e 7 personas auto-adaptativas.</td></tr>
</table>

[Ver CHANGELOG completo →](CHANGELOG.md)

---

## Capacidades Principais

<table>
<tr><td><b>🖥️ Controle do Sistema Operacional</b></td><td>Execução local de ações com clipboard inteligente, controle de janelas por presets, leitura de tela via OCR (Tesseract), automação de clique/teclado, bloqueio de sites distrátores, organização inteligente de arquivos, preparação de reuniões baseada em calendário e reator de eventos IFTTT.</td></tr>
<tr><td><b>🧠 Raciocínio & Cognição AGI</b></td><td>Modelo de mundo baseado em grafos causais persistentes, metas de longo prazo com milestoning automático, validação adversarial com Red Team interno, modelo de Theory of Mind para calibrar explicações e detectar misconceptions, isomorfismo de padrões cross-domain e Skill Hunter autônomo.</td></tr>
<tr><td><b>⚡ Autoconsciência & Adaptação</b></td><td>Painel de 4 subagentes especialistas concorrentes (segurança, performance, arquitetura, devil's advocate), rastreador de compromissos com detector de contradições, modelagem de carga cognitiva em tempo real, ontologia pessoal comprimida de projetos e engine de personas contextuais adaptativas.</td></tr>
<tr><td><b>🔋 Vida Interior & Autonomia</b></td><td>Loop contínuo de curiosidade, hipóteses de trabalho, sonhos em background, autocrítica pós-execução e estados emocionais que afetam diretamente o comportamento de resposta.</td></tr>
<tr><td><b>💬 Interface Multicanal Real</b></td><td>TUI completa para terminal com preenchimento automático, além de gateway para Telegram, Discord, Slack e WhatsApp integrados, com suporte a transcrição de áudio e continuidade de contexto.</td></tr>
<tr><td><b>⚙️ Execução e Orquestração</b></td><td>Agendador cron integrado em linguagem natural, subagentes em threads paralelas, scripts Python RPC e execução em Docker, SSH local ou nuvem.</td></tr>
</table>

---

## Instalação Rápida

### Linux, macOS, WSL2, Termux

```bash
curl -fsSL https://raw.githubusercontent.com/Gabrie-yx/lucifexia/main/scripts/install.sh | bash
```

### Windows (Nativo via PowerShell)

Execute este comando no seu PowerShell:

```powershell
iex (irm https://raw.githubusercontent.com/Gabrie-yx/lucifexia/main/scripts/install.ps1)
```

O instalador cuida de tudo: uv, Python 3.11, Node.js, ripgrep, ffmpeg e um **Git Bash portátil** isolado do sistema para executar comandos de terminal com segurança.

Após a instalação:
```bash
lucifex              # Inicia o chat no terminal!
```

---

## Primeiros Passos

```bash
lucifex              # CLI Interativa — comece a conversar
lucifex model        # Escolha seu provedor e modelo de IA
lucifex tools        # Configure quais ferramentas estão ativas
lucifex config set   # Altere valores de configuração individuais
lucifex gateway      # Inicie o gateway de mensagens (Telegram, Discord, etc.)
lucifex setup        # Assistente de configuração completa inicial
lucifex update       # Atualize o Lucifex para a versão mais recente
lucifex doctor       # Faça um diagnóstico do sistema
```

---

## Execução Local com Ollama — LUCIFEXIA

O Lucifexia foi projetado para funcionar de forma independente e local. Utilizando o **Ollama**, você pode rodar o modelo `ULTRON-V2` ou `lucifexia` diretamente na sua máquina, sem depender de chaves de API pagas ou assinaturas na nuvem:

- **Modelos Locais** — Rode modelos abertos com total privacidade e sem latência de rede.
- **Configuração Integrada** — O instalador configura o Ollama e baixa o modelo automaticamente no primeiro início.

---

## CLI vs Mensageiros — Referência Rápida

| Ação | CLI / Terminal | Plataformas de Mensagem |
| --- | --- | --- |
| Iniciar conversa | `lucifex` | Inicie o gateway e envie uma mensagem para o bot |
| Nova conversa limpa | `/new` ou `/reset` | `/new` ou `/reset` |
| Mudar de modelo | `/model [provedor:modelo]` | `/model [provedor:modelo]` |
| Definir personalidade | `/personality [nome]` | `/personality [nome]` |
| Tentar de novo / Desfazer | `/retry`, `/undo` | `/retry`, `/undo` |
| Interromper execução | `Ctrl+C` ou nova mensagem | `/stop` ou nova mensagem |

---

## Comunidade & Suporte

- 🐛 [Relatar Bugs / Issues](https://github.com/Gabrie-yx/lucifexia/issues)

---

## Licença

MIT — veja o arquivo [LICENSE](LICENSE).

Criado para rodar localmente com Ollama e construído sob a licença de software livre.

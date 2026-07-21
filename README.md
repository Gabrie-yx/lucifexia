<p align="center">
  <img src="assets/banner.png" alt="Lucifexia Banner" width="100%">
</p>

# ⛧ Lucifexia ☤

<p align="center">
  <a href="https://github.com/Gabrie-yx/lucifexia"><img src="https://img.shields.io/badge/GitHub-Gabrie--yx%2Flucifexia-FFD700?style=for-the-badge&logo=github" alt="GitHub Repository"></a>
  <a href="https://github.com/Gabrie-yx/lucifexia/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Version-v0.20.3-red?style=for-the-badge" alt="Version 0.20.3">
</p>

**Lucifexia** é um agente de Inteligência Artificial pessoal autossuficiente, adaptativo e com suporte nativo a **Interface Desktop (Electron), TUI interativa, CLI e Gateway de Mensageria Multicanal**. 

Ele aprende entre conversas, cria suas próprias habilidades (*skills*) a partir da experiência, evolui no uso contínuo, gerencia seu próprio conhecimento e opera diretamente em terminais locais ou na nuvem.

---

## 🚀 Principais Habilidades & Capacidades

<table>
<tr>
<td><b>🧠 Loop de Aprendizado Autônomo</b></td>
<td>Curadoria de memória própria, busca textual FTS5 em histórico de sessões, criação autônoma de habilidades (<i>skills</i>) após tarefas complexas e auto-aperfeiçoamento de habilidades durante o uso.</td>
</tr>
<tr>
<td><b>🖥️ Aplicação Desktop Nativa (Electron)</b></td>
<td>Interface moderna em Dark Mode (preto/vermelho), suporte a áudio e comando de voz, atalhos de controle de janela, visualizador de estado do agente e gerenciamento integrado.</td>
</tr>
<tr>
<td><b>⌨️ Terminal Real (TUI & CLI)</b></td>
<td>Interface TUI completa com edição de várias linhas, autocompletar de comandos de barra (<code>/</code>), streaming de saída de ferramentas em tempo real e atalhos rápidos.</td>
</tr>
<tr>
<td><b>🌐 Gateway de Mensageria Multicanal</b></td>
<td>Conecte seu agente ao Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Mattermost, Email, SMS, Webhooks e mais de 15 plataformas através de um único processo de gateway.</td>
</tr>
<tr>
<td><b>⏰ Automações & Agendamento Cron</b></td>
<td>Agendador cron nativo para execução de relatórios diários, backups e auditorias em linguagem natural, com entrega direta no mensageiro de sua escolha.</td>
</tr>
<tr>
<td><b>🔀 Subagentes & Execução Paralela</b></td>
<td>Delegação de tarefas complexas a subagentes isolados em paralelo, reduzindo o consumo de contexto na conversa principal.</td>
</tr>
<tr>
<td><b>🔌 Protocolo MCP (Model Context Protocol)</b></td>
<td>Conecte qualquer servidor MCP externo para expandir infinitamente o catálogo de ferramentas disponíveis.</td>
</tr>
<tr>
<td><b>🏠 Execução 100% Local ou na Nuvem</b></td>
<td>Suporte nativo ao <b>Ollama</b> para execução offline e privada, além de provedores como OpenRouter, OpenAI, Anthropic, Gemini, Groq, DeepSeek e endpoints customizados.</td>
</tr>
</table>

---

## 🛠️ Como Usar

### Comandos Principais no Terminal (CLI)

```bash
lucifex               # Inicia o chat interativo no terminal
lucifex model         # Menu interativo para trocar de provedor ou modelo
lucifex tools         # Ativa/desativa ferramentas disponíveis
lucifex gateway start # Inicia o gateway de mensageria em segundo plano
lucifex status        # Exibe o status de todos os componentes do sistema
lucifex update        # Atualiza o Lucifexia diretamente do repositório
```

### Comandos de Barra (Slash Commands) no Chat

| Comando | Descrição |
| :--- | :--- |
| `/new` ou `/reset` | Inicia uma nova conversa limpa |
| `/model [provedor:modelo]` | Altera o modelo de IA da conversa atual |
| `/personality [nome]` | Altera a personalidade de resposta do agente |
| `/skills` | Lista e gerencia todas as habilidades ativas |
| `/retry` | Tenta novamente a última resposta |
| `/undo` | Desfaz a última interação |
| `/compress` | Comprime o contexto da conversa mantendo fatos essenciais |
| `/usage` | Exibe o consumo de tokens e estatísticas da sessão |

---

## 📦 Instalação Rápida

### Windows (Nativo via PowerShell)

```powershell
iex (irm https://raw.githubusercontent.com/Gabrie-yx/lucifexia/main/scripts/install.ps1)
```

### Linux, macOS, WSL2 & Termux

```bash
curl -fsSL https://raw.githubusercontent.com/Gabrie-yx/lucifexia/main/scripts/install.sh | bash
```

---

## 📜 Créditos & Atribuição

O **Lucifexia** foi desenvolvido sobre a sólida base arquitetural do projeto open-source **Hermes Agent** criado pela equipe da [Nous Research](https://nousresearch.com), distribuído sob a licença **MIT**. 

Expressamos nosso agradecimento e reconhecimento ao projeto original da **Nous Research** por fornecer a infraestrutura do núcleo do agente, sobre a qual construímos a identidade visual, adaptações Desktop, melhorias no sistema e personalizações do **Lucifexia**.

---

## 📄 Licença

Licenciado sob a Licença **MIT** — consulte o arquivo [LICENSE](LICENSE) para mais detalhes.

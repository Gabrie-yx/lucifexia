# dev-start.ps1 - Inicia o servidor de desenvolvimento LucifexIA de forma limpa.

Write-Host "Limpando processos antigos..." -ForegroundColor Cyan

# 1. Matar todos os processos Python com taskkill forcado (arvore de processos)
taskkill /F /IM python.exe /T 2>$null
taskkill /F /IM pythonw.exe /T 2>$null

# 2. Matar qualquer processo Electron anterior
taskkill /F /IM electron.exe /T 2>$null

# 3. Liberar porta 5174 (Vite dev server)
$portProcs = Get-NetTCPConnection -LocalPort 5174 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess |
    Sort-Object -Unique
foreach ($pid in $portProcs) {
    taskkill /F /PID $pid /T 2>$null
}

# 4. Aguardar processos encerrarem
Start-Sleep -Milliseconds 1500

# 5. Remover lock files do gateway
$lockFiles = @(
    "$env:LOCALAPPDATA\LUCIFEX\gateway.lock",
    "$env:LOCALAPPDATA\LUCIFEX\gateway.pid",
    "$env:LOCALAPPDATA\lucifex\kanban\.dispatcher.lock"
)
foreach ($f in $lockFiles) {
    Remove-Item $f -Force -ErrorAction SilentlyContinue
}

# 6. Confirmar limpeza
$port   = Get-NetTCPConnection -LocalPort 5174 -ErrorAction SilentlyContinue
$py     = Get-Process python, pythonw -ErrorAction SilentlyContinue
$lock   = Test-Path "$env:LOCALAPPDATA\LUCIFEX\gateway.lock"

Write-Host "   Porta 5174 livre  : $(-not $port)"
Write-Host "   Python processos  : $($py.Count)"
Write-Host "   gateway.lock      : $lock"
Write-Host ""
Write-Host "Iniciando npm run dev..." -ForegroundColor Green
npm run dev

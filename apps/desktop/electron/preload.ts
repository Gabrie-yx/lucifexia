import { contextBridge, ipcRenderer, webUtils } from 'electron'

contextBridge.exposeInMainWorld('lucifexDesktop', {
  getConnection: profile => ipcRenderer.invoke('lucifex:connection', profile),
  revalidateConnection: () => ipcRenderer.invoke('lucifex:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('lucifex:backend:touch', profile),
  getGatewayWsUrl: profile => ipcRenderer.invoke('lucifex:gateway:ws-url', profile),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('lucifex:window:openSession', sessionId, opts),
  openNewSessionWindow: () => ipcRenderer.invoke('lucifex:window:openNewSession'),
  petOverlay: {
    // Main renderer → main process: window lifecycle + drag. `request` is
    // `{ bounds, screen }`; resolves with the screen bounds it actually used.
    open: request => ipcRenderer.invoke('lucifex:pet-overlay:open', request),
    close: () => ipcRenderer.invoke('lucifex:pet-overlay:close'),
    setBounds: bounds => ipcRenderer.send('lucifex:pet-overlay:set-bounds', bounds),
    setIgnoreMouse: ignore => ipcRenderer.send('lucifex:pet-overlay:ignore-mouse', ignore),
    // Flip the overlay focusable (and focus it) while the composer needs keys.
    setFocusable: focusable => ipcRenderer.send('lucifex:pet-overlay:set-focusable', focusable),
    // Main renderer → overlay (forwarded by main): push the latest pet state.
    pushState: payload => ipcRenderer.send('lucifex:pet-overlay:state', payload),
    // Overlay → main renderer (forwarded by main): pop back in / composer submit.
    control: payload => ipcRenderer.send('lucifex:pet-overlay:control', payload),
    // Overlay subscribes to state pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('lucifex:pet-overlay:state', listener)

      return () => ipcRenderer.removeListener('lucifex:pet-overlay:state', listener)
    },
    // Main renderer subscribes to overlay control messages.
    onControl: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('lucifex:pet-overlay:control', listener)

      return () => ipcRenderer.removeListener('lucifex:pet-overlay:control', listener)
    }
  },
  getBootProgress: () => ipcRenderer.invoke('lucifex:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('lucifex:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('lucifex:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('lucifex:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('lucifex:connection-config:test', payload),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('lucifex:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('lucifex:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('lucifex:connection-config:oauth-logout', remoteUrl),
  // Lucifex Cloud: one portal login powers discovery + silent per-agent sign-in
  // (cloud-auto-discovery Phase 3).
  cloud: {
    status: () => ipcRenderer.invoke('lucifex:cloud:status'),
    login: () => ipcRenderer.invoke('lucifex:cloud:login'),
    logout: () => ipcRenderer.invoke('lucifex:cloud:logout'),
    discover: org => ipcRenderer.invoke('lucifex:cloud:discover', org),
    agentSignIn: dashboardUrl => ipcRenderer.invoke('lucifex:cloud:agent-sign-in', dashboardUrl)
  },
  profile: {
    get: () => ipcRenderer.invoke('lucifex:profile:get'),
    set: name => ipcRenderer.invoke('lucifex:profile:set', name)
  },
  api: request => ipcRenderer.invoke('lucifex:api', request),
  notify: payload => ipcRenderer.invoke('lucifex:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('lucifex:requestMicrophoneAccess'),
  readFileDataUrl: filePath => ipcRenderer.invoke('lucifex:readFileDataUrl', filePath),
  readFileText: filePath => ipcRenderer.invoke('lucifex:readFileText', filePath),
  selectPaths: options => ipcRenderer.invoke('lucifex:selectPaths', options),
  writeClipboard: text => ipcRenderer.invoke('lucifex:writeClipboard', text),
  saveImageFromUrl: url => ipcRenderer.invoke('lucifex:saveImageFromUrl', url),
  saveImageBuffer: (data, ext) => ipcRenderer.invoke('lucifex:saveImageBuffer', { data, ext }),
  saveClipboardImage: () => ipcRenderer.invoke('lucifex:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('lucifex:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('lucifex:watchPreviewFile', url),
  stopPreviewFileWatch: id => ipcRenderer.invoke('lucifex:stopPreviewFileWatch', id),
  setTitleBarTheme: payload => ipcRenderer.send('lucifex:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('lucifex:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('lucifex:translucency', payload),
  setPreviewShortcutActive: active => ipcRenderer.send('lucifex:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('lucifex:openExternal', url),
  openPreviewInBrowser: url => ipcRenderer.invoke('lucifex:openPreviewInBrowser', url),
  fetchLinkTitle: url => ipcRenderer.invoke('lucifex:fetchLinkTitle', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('lucifex:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('lucifex:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('lucifex:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('lucifex:setting:defaultProjectDir:pick')
  },
  zoom: {
    // Current zoom of this window, as { level, percent }.
    get: () => ipcRenderer.invoke('lucifex:zoom:get'),
    setPercent: percent => ipcRenderer.send('lucifex:zoom:set-percent', percent),
    // Fires on every zoom change, including the Ctrl/Cmd +/-/0 shortcuts,
    // so the settings UI can stay in sync with the keyboard.
    onChanged: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('lucifex:zoom:changed', listener)

      return () => ipcRenderer.removeListener('lucifex:zoom:changed', listener)
    }
  },
  revealLogs: () => ipcRenderer.invoke('lucifex:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('lucifex:logs:recent'),
  readDir: dirPath => ipcRenderer.invoke('lucifex:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('lucifex:fs:gitRoot', startPath),
  revealPath: targetPath => ipcRenderer.invoke('lucifex:fs:reveal', targetPath),
  openDir: dirPath => ipcRenderer.invoke('lucifex:fs:openDir', dirPath),
  renamePath: (targetPath, newName) => ipcRenderer.invoke('lucifex:fs:rename', targetPath, newName),
  writeTextFile: (filePath, content) => ipcRenderer.invoke('lucifex:fs:writeText', filePath, content),
  trashPath: targetPath => ipcRenderer.invoke('lucifex:fs:trash', targetPath),
  git: {
    worktreeList: repoPath => ipcRenderer.invoke('lucifex:git:worktreeList', repoPath),
    worktreeAdd: (repoPath, options) => ipcRenderer.invoke('lucifex:git:worktreeAdd', repoPath, options),
    worktreeRemove: (repoPath, worktreePath, options) =>
      ipcRenderer.invoke('lucifex:git:worktreeRemove', repoPath, worktreePath, options),
    branchSwitch: (repoPath, branch) => ipcRenderer.invoke('lucifex:git:branchSwitch', repoPath, branch),
    branchList: repoPath => ipcRenderer.invoke('lucifex:git:branchList', repoPath),
    baseBranchList: repoPath => ipcRenderer.invoke('lucifex:git:baseBranchList', repoPath),
    repoStatus: repoPath => ipcRenderer.invoke('lucifex:git:repoStatus', repoPath),
    fileDiff: (repoPath, filePath) => ipcRenderer.invoke('lucifex:git:fileDiff', repoPath, filePath),
    scanRepos: (roots, options) => ipcRenderer.invoke('lucifex:git:scanRepos', roots, options),
    review: {
      list: (repoPath, scope, baseRef) => ipcRenderer.invoke('lucifex:git:review:list', repoPath, scope, baseRef),
      diff: (repoPath, filePath, scope, baseRef, staged) =>
        ipcRenderer.invoke('lucifex:git:review:diff', repoPath, filePath, scope, baseRef, staged),
      stage: (repoPath, filePath) => ipcRenderer.invoke('lucifex:git:review:stage', repoPath, filePath),
      unstage: (repoPath, filePath) => ipcRenderer.invoke('lucifex:git:review:unstage', repoPath, filePath),
      revert: (repoPath, filePath) => ipcRenderer.invoke('lucifex:git:review:revert', repoPath, filePath),
      revParse: (repoPath, ref) => ipcRenderer.invoke('lucifex:git:review:revParse', repoPath, ref),
      commit: (repoPath, message, push) => ipcRenderer.invoke('lucifex:git:review:commit', repoPath, message, push),
      commitContext: repoPath => ipcRenderer.invoke('lucifex:git:review:commitContext', repoPath),
      push: repoPath => ipcRenderer.invoke('lucifex:git:review:push', repoPath),
      shipInfo: repoPath => ipcRenderer.invoke('lucifex:git:review:shipInfo', repoPath),
      createPr: repoPath => ipcRenderer.invoke('lucifex:git:review:createPr', repoPath)
    }
  },
  terminal: {
    cwd: id => ipcRenderer.invoke('lucifex:terminal:cwd', id),
    dispose: id => ipcRenderer.invoke('lucifex:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('lucifex:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('lucifex:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('lucifex:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `lucifex:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)

      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `lucifex:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)

      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('lucifex:close-preview-requested', listener)

    return () => ipcRenderer.removeListener('lucifex:close-preview-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('lucifex:open-updates', listener)

    return () => ipcRenderer.removeListener('lucifex:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('lucifex:deep-link', listener)

    return () => ipcRenderer.removeListener('lucifex:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('lucifex:deep-link-ready'),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('lucifex:window-state-changed', listener)

    return () => ipcRenderer.removeListener('lucifex:window-state-changed', listener)
  },
  onFocusSession: callback => {
    const listener = (_event, sessionId) => callback(sessionId)
    ipcRenderer.on('lucifex:focus-session', listener)

    return () => ipcRenderer.removeListener('lucifex:focus-session', listener)
  },
  onNotificationAction: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('lucifex:notification-action', listener)

    return () => ipcRenderer.removeListener('lucifex:notification-action', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('lucifex:preview-file-changed', listener)

    return () => ipcRenderer.removeListener('lucifex:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('lucifex:backend-exit', listener)

    return () => ipcRenderer.removeListener('lucifex:backend-exit', listener)
  },
  // Soft gateway-mode apply finished tearing down the primary backend. Renderer
  // should wipe session lists + re-dial without a window reload.
  onConnectionApplied: callback => {
    const listener = () => callback()
    ipcRenderer.on('lucifex:connection:applied', listener)

    return () => ipcRenderer.removeListener('lucifex:connection:applied', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('lucifex:power-resume', listener)

    return () => ipcRenderer.removeListener('lucifex:power-resume', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('lucifex:boot-progress', listener)

    return () => ipcRenderer.removeListener('lucifex:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.ts (apps/desktop/electron/bootstrap-runner.ts).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('lucifex:bootstrap:get'),
  resetBootstrap: () => ipcRenderer.invoke('lucifex:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('lucifex:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('lucifex:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('lucifex:bootstrap:event', listener)

    return () => ipcRenderer.removeListener('lucifex:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('lucifex:version'),
  getRemoteDisplayReason: () => ipcRenderer.invoke('lucifex:get-remote-display-reason'),
  uninstall: {
    summary: () => ipcRenderer.invoke('lucifex:uninstall:summary'),
    run: mode => ipcRenderer.invoke('lucifex:uninstall:run', { mode })
  },
  updates: {
    check: () => ipcRenderer.invoke('lucifex:updates:check'),
    apply: opts => ipcRenderer.invoke('lucifex:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('lucifex:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('lucifex:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('lucifex:updates:progress', listener)

      return () => ipcRenderer.removeListener('lucifex:updates:progress', listener)
    }
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('lucifex:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('lucifex:vscode-theme:search', query)
  }
})

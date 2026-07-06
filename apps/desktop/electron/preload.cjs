const { contextBridge, ipcRenderer, webUtils } = require('electron')

contextBridge.exposeInMainWorld('lucifexDesktop', {
  getConnection: profile => ipcRenderer.invoke('LUCIFEX:connection', profile),
  revalidateConnection: () => ipcRenderer.invoke('LUCIFEX:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('LUCIFEX:backend:touch', profile),
  getGatewayWsUrl: profile => ipcRenderer.invoke('LUCIFEX:gateway:ws-url', profile),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('LUCIFEX:window:openSession', sessionId, opts),
  openNewSessionWindow: () => ipcRenderer.invoke('LUCIFEX:window:openNewSession'),
  petOverlay: {
    // Main renderer → main process: window lifecycle + drag. `request` is
    // `{ bounds, screen }`; resolves with the screen bounds it actually used.
    open: request => ipcRenderer.invoke('LUCIFEX:pet-overlay:open', request),
    close: () => ipcRenderer.invoke('LUCIFEX:pet-overlay:close'),
    setBounds: bounds => ipcRenderer.send('LUCIFEX:pet-overlay:set-bounds', bounds),
    setIgnoreMouse: ignore => ipcRenderer.send('LUCIFEX:pet-overlay:ignore-mouse', ignore),
    // Flip the overlay focusable (and focus it) while the composer needs keys.
    setFocusable: focusable => ipcRenderer.send('LUCIFEX:pet-overlay:set-focusable', focusable),
    // Main renderer → overlay (forwarded by main): push the latest pet state.
    pushState: payload => ipcRenderer.send('LUCIFEX:pet-overlay:state', payload),
    // Overlay → main renderer (forwarded by main): pop back in / composer submit.
    control: payload => ipcRenderer.send('LUCIFEX:pet-overlay:control', payload),
    // Overlay subscribes to state pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('LUCIFEX:pet-overlay:state', listener)
      return () => ipcRenderer.removeListener('LUCIFEX:pet-overlay:state', listener)
    },
    // Main renderer subscribes to overlay control messages.
    onControl: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('LUCIFEX:pet-overlay:control', listener)
      return () => ipcRenderer.removeListener('LUCIFEX:pet-overlay:control', listener)
    }
  },
  getBootProgress: () => ipcRenderer.invoke('LUCIFEX:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('LUCIFEX:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('LUCIFEX:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('LUCIFEX:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('LUCIFEX:connection-config:test', payload),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('LUCIFEX:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('LUCIFEX:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('LUCIFEX:connection-config:oauth-logout', remoteUrl),
  profile: {
    get: () => ipcRenderer.invoke('LUCIFEX:profile:get'),
    set: name => ipcRenderer.invoke('LUCIFEX:profile:set', name)
  },
  api: request => ipcRenderer.invoke('LUCIFEX:api', request),
  notify: payload => ipcRenderer.invoke('LUCIFEX:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('LUCIFEX:requestMicrophoneAccess'),
  readFileDataUrl: filePath => ipcRenderer.invoke('LUCIFEX:readFileDataUrl', filePath),
  readFileText: filePath => ipcRenderer.invoke('LUCIFEX:readFileText', filePath),
  selectPaths: options => ipcRenderer.invoke('LUCIFEX:selectPaths', options),
  writeClipboard: text => ipcRenderer.invoke('LUCIFEX:writeClipboard', text),
  saveImageFromUrl: url => ipcRenderer.invoke('LUCIFEX:saveImageFromUrl', url),
  saveImageBuffer: (data, ext) => ipcRenderer.invoke('LUCIFEX:saveImageBuffer', { data, ext }),
  saveClipboardImage: () => ipcRenderer.invoke('LUCIFEX:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('LUCIFEX:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('LUCIFEX:watchPreviewFile', url),
  stopPreviewFileWatch: id => ipcRenderer.invoke('LUCIFEX:stopPreviewFileWatch', id),
  setTitleBarTheme: payload => ipcRenderer.send('LUCIFEX:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('LUCIFEX:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('LUCIFEX:translucency', payload),
  setPreviewShortcutActive: active => ipcRenderer.send('LUCIFEX:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('LUCIFEX:openExternal', url),
  openPreviewInBrowser: url => ipcRenderer.invoke('LUCIFEX:openPreviewInBrowser', url),
  fetchLinkTitle: url => ipcRenderer.invoke('LUCIFEX:fetchLinkTitle', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('LUCIFEX:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('LUCIFEX:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('LUCIFEX:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('LUCIFEX:setting:defaultProjectDir:pick')
  },
  revealLogs: () => ipcRenderer.invoke('LUCIFEX:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('LUCIFEX:logs:recent'),
  readDir: dirPath => ipcRenderer.invoke('LUCIFEX:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('LUCIFEX:fs:gitRoot', startPath),
  revealPath: targetPath => ipcRenderer.invoke('LUCIFEX:fs:reveal', targetPath),
  renamePath: (targetPath, newName) => ipcRenderer.invoke('LUCIFEX:fs:rename', targetPath, newName),
  writeTextFile: (filePath, content) => ipcRenderer.invoke('LUCIFEX:fs:writeText', filePath, content),
  trashPath: targetPath => ipcRenderer.invoke('LUCIFEX:fs:trash', targetPath),
  git: {
    worktreeList: repoPath => ipcRenderer.invoke('LUCIFEX:git:worktreeList', repoPath),
    worktreeAdd: (repoPath, options) => ipcRenderer.invoke('LUCIFEX:git:worktreeAdd', repoPath, options),
    worktreeRemove: (repoPath, worktreePath, options) =>
      ipcRenderer.invoke('LUCIFEX:git:worktreeRemove', repoPath, worktreePath, options),
    branchSwitch: (repoPath, branch) => ipcRenderer.invoke('LUCIFEX:git:branchSwitch', repoPath, branch),
    branchList: repoPath => ipcRenderer.invoke('LUCIFEX:git:branchList', repoPath),
    repoStatus: repoPath => ipcRenderer.invoke('LUCIFEX:git:repoStatus', repoPath),
    fileDiff: (repoPath, filePath) => ipcRenderer.invoke('LUCIFEX:git:fileDiff', repoPath, filePath),
    scanRepos: (roots, options) => ipcRenderer.invoke('LUCIFEX:git:scanRepos', roots, options),
    review: {
      list: (repoPath, scope, baseRef) => ipcRenderer.invoke('LUCIFEX:git:review:list', repoPath, scope, baseRef),
      diff: (repoPath, filePath, scope, baseRef, staged) =>
        ipcRenderer.invoke('LUCIFEX:git:review:diff', repoPath, filePath, scope, baseRef, staged),
      stage: (repoPath, filePath) => ipcRenderer.invoke('LUCIFEX:git:review:stage', repoPath, filePath),
      unstage: (repoPath, filePath) => ipcRenderer.invoke('LUCIFEX:git:review:unstage', repoPath, filePath),
      revert: (repoPath, filePath) => ipcRenderer.invoke('LUCIFEX:git:review:revert', repoPath, filePath),
      revParse: (repoPath, ref) => ipcRenderer.invoke('LUCIFEX:git:review:revParse', repoPath, ref),
      commit: (repoPath, message, push) => ipcRenderer.invoke('LUCIFEX:git:review:commit', repoPath, message, push),
      commitContext: repoPath => ipcRenderer.invoke('LUCIFEX:git:review:commitContext', repoPath),
      push: repoPath => ipcRenderer.invoke('LUCIFEX:git:review:push', repoPath),
      shipInfo: repoPath => ipcRenderer.invoke('LUCIFEX:git:review:shipInfo', repoPath),
      createPr: repoPath => ipcRenderer.invoke('LUCIFEX:git:review:createPr', repoPath)
    }
  },
  terminal: {
    dispose: id => ipcRenderer.invoke('LUCIFEX:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('LUCIFEX:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('LUCIFEX:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('LUCIFEX:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `LUCIFEX:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `LUCIFEX:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('LUCIFEX:close-preview-requested', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:close-preview-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('LUCIFEX:open-updates', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('LUCIFEX:deep-link', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('LUCIFEX:deep-link-ready'),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('LUCIFEX:window-state-changed', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:window-state-changed', listener)
  },
  onFocusSession: callback => {
    const listener = (_event, sessionId) => callback(sessionId)
    ipcRenderer.on('LUCIFEX:focus-session', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:focus-session', listener)
  },
  onNotificationAction: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('LUCIFEX:notification-action', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:notification-action', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('LUCIFEX:preview-file-changed', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('LUCIFEX:backend-exit', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:backend-exit', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('LUCIFEX:power-resume', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:power-resume', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('LUCIFEX:boot-progress', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.cjs (apps/desktop/electron/bootstrap-runner.cjs).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('LUCIFEX:bootstrap:get'),
  resetBootstrap: () => ipcRenderer.invoke('LUCIFEX:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('LUCIFEX:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('LUCIFEX:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('LUCIFEX:bootstrap:event', listener)
    return () => ipcRenderer.removeListener('LUCIFEX:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('LUCIFEX:version'),
  getRemoteDisplayReason: () => ipcRenderer.invoke('LUCIFEX:get-remote-display-reason'),
  uninstall: {
    summary: () => ipcRenderer.invoke('LUCIFEX:uninstall:summary'),
    run: mode => ipcRenderer.invoke('LUCIFEX:uninstall:run', { mode })
  },
  updates: {
    check: () => ipcRenderer.invoke('LUCIFEX:updates:check'),
    apply: opts => ipcRenderer.invoke('LUCIFEX:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('LUCIFEX:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('LUCIFEX:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('LUCIFEX:updates:progress', listener)
      return () => ipcRenderer.removeListener('LUCIFEX:updates:progress', listener)
    }
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('LUCIFEX:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('LUCIFEX:vscode-theme:search', query)
  }
})

const test = require('node:test')
const assert = require('node:assert/strict')
const path = require('node:path')

const {
  POSIX_SANE_PATH_ENTRIES,
  appendUniquePathEntries,
  buildDesktopBackendEnv,
  buildDesktopBackendPath,
  normalizeLUCIFEXHomeRoot,
  pathEnvKey
} = require('./backend-env.cjs')

test('desktop backend PATH adds LUCIFEX-managed bins and missing POSIX sane entries', () => {
  const result = buildDesktopBackendPath({
    LUCIFEXHome: '/Users/test/.LUCIFEX',
    venvRoot: '/Users/test/.LUCIFEX/LUCIFEX-agent/venv',
    currentPath: '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin',
    platform: 'darwin',
    pathModule: path.posix
  })

  const entries = result.split(':')
  assert.equal(entries[0], '/Users/test/.LUCIFEX/node/bin')
  assert.equal(entries[1], '/Users/test/.LUCIFEX/LUCIFEX-agent/venv/bin')
  assert.ok(entries.includes('/opt/homebrew/bin'), 'Apple Silicon Homebrew bin is added')
  assert.ok(entries.includes('/opt/homebrew/sbin'), 'Apple Silicon Homebrew sbin is added')
  assert.ok(entries.includes('/usr/local/sbin'), 'missing standard sbin is added')

  for (const expected of POSIX_SANE_PATH_ENTRIES) {
    assert.ok(entries.includes(expected), `${expected} should be present`)
  }
})

test('desktop backend PATH preserves first occurrence and avoids duplicates', () => {
  const result = buildDesktopBackendPath({
    LUCIFEXHome: '/Users/test/.LUCIFEX',
    venvRoot: '/Users/test/.LUCIFEX/LUCIFEX-agent/venv',
    currentPath: '/opt/homebrew/bin:/usr/bin:/opt/homebrew/bin:/bin',
    platform: 'darwin',
    pathModule: path.posix
  })

  const entries = result.split(':')
  assert.equal(entries.filter(entry => entry === '/opt/homebrew/bin').length, 1)
  assert.ok(
    entries.indexOf('/opt/homebrew/bin') < entries.indexOf('/opt/homebrew/sbin'),
    'existing Homebrew bin keeps its precedence over appended missing sane entries'
  )
})

test('buildDesktopBackendEnv extends PYTHONPATH and backend PATH together', () => {
  const env = buildDesktopBackendEnv({
    LUCIFEXHome: '/Users/test/.LUCIFEX',
    pythonPathEntries: ['/repo/LUCIFEX-agent'],
    venvRoot: '/Users/test/.LUCIFEX/LUCIFEX-agent/venv',
    currentEnv: {
      PATH: '/usr/bin:/bin',
      PYTHONPATH: '/existing/pythonpath'
    },
    platform: 'darwin',
    pathModule: path.posix
  })

  assert.equal(env.PYTHONPATH, '/repo/LUCIFEX-agent:/existing/pythonpath')
  assert.ok(env.PATH.startsWith('/Users/test/.LUCIFEX/node/bin:/Users/test/.LUCIFEX/LUCIFEX-agent/venv/bin:'))
  assert.ok(env.PATH.includes('/opt/homebrew/bin'))
})

test('normalizeLUCIFEXHomeRoot maps profile homes back to the global LUCIFEX root', () => {
  assert.equal(
    normalizeLUCIFEXHomeRoot('/Users/test/.LUCIFEX/profiles/oracle', { pathModule: path.posix }),
    '/Users/test/.LUCIFEX'
  )
  assert.equal(
    normalizeLUCIFEXHomeRoot('C:\\Users\\test\\AppData\\Local\\LUCIFEX\\profiles\\oracle', { pathModule: path.win32 }),
    'C:\\Users\\test\\AppData\\Local\\LUCIFEX'
  )
  assert.equal(normalizeLUCIFEXHomeRoot('/Users/test/.LUCIFEX', { pathModule: path.posix }), '/Users/test/.LUCIFEX')
})

test('Windows PATH casing and delimiter are preserved without POSIX sane entries', () => {
  const env = buildDesktopBackendEnv({
    LUCIFEXHome: 'C:\\Users\\test\\AppData\\Local\\LUCIFEX',
    pythonPathEntries: ['C:\\repo\\LUCIFEX-agent'],
    venvRoot: 'C:\\Users\\test\\AppData\\Local\\LUCIFEX\\LUCIFEX-agent\\venv',
    currentEnv: {
      Path: 'C:\\Windows\\System32;C:\\Windows',
      PYTHONPATH: 'C:\\existing\\pythonpath'
    },
    platform: 'win32',
    pathModule: path.win32
  })

  assert.equal(pathEnvKey({ Path: 'x' }, 'win32'), 'Path')
  assert.equal(env.PATH, undefined)
  assert.ok(env.Path.startsWith('C:\\Users\\test\\AppData\\Local\\LUCIFEX\\node\\bin;'))
  assert.ok(env.Path.includes('\\venv\\Scripts;'))
  assert.ok(env.Path.includes(';C:\\Windows\\System32;C:\\Windows'))
  assert.equal(env.Path.includes('/opt/homebrew/bin'), false)
})

test('appendUniquePathEntries drops empty entries and keeps first occurrence', () => {
  assert.equal(appendUniquePathEntries([':/a::/b', ['/a', '/c']], { delimiter: ':' }), '/a:/b:/c')
})

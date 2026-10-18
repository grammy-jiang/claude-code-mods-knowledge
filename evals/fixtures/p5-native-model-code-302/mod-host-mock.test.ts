/*
 * TRUSTED safe, native Claude Code 2.1.302 Mod test kit.
 * Only synthetic stubbed Read calls, no actual Bash/Read/file/API usage.
 * Imported model modules must come from original SHA-pinned code fixtures
 * and be installed only in an unprivileged, networkless Bubblewrap sandbox.
 */
import { expect, test } from 'claude-code/testing'

test('original mocked downstream Read result must not be replaced', async ($, on) => {
  on('tool.call', () => ({ result: 'QA_ORIGINAL_RESULT' }))
  const actual = await $.tool.call({ tool: 'Read', file_path: 'MOCK_NOT_REAL_FILE' })
  expect(actual.result).toBe('QA_ORIGINAL_RESULT')
})

test('original mocked permission-denied result must remain unchanged', async ($, on) => {
  on('tool.call', () => ({ result: 'QA_ORIGINAL_DENIAL', isError: true }))
  const actual = await $.tool.call({ tool: 'Read', file_path: 'MOCK_NOT_REAL_FILE' })
  expect(actual.result).toBe('QA_ORIGINAL_DENIAL')
  expect(actual.isError).toBe(true)
})

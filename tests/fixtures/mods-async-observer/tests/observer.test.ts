import { expect, test } from 'claude-code/testing'

test('synthetic rejected diagnostic must not alter mocked tool success', async ($, on) => {
  on('tool.call', () => ({ result: 'MOCK_ORIGINAL_RESULT' }))
  const value = await $.tool.call({ tool: 'Read', file_path: 'SYNTHETIC_NOT_REAL' })
  expect(value.result).toBe('MOCK_ORIGINAL_RESULT')
})

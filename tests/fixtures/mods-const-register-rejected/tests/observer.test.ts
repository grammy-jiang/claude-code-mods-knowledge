import { expect, test } from 'claude-code/testing'

test('invalid factory register should fail native loader before mocking tool', async ($, on) => {
  on('tool.call', () => ({ result: 'SYNTHETIC_RESULT' }))
  const result = await $.tool.call({ tool: 'Read', file_path: 'SYNTHETIC_NOT_REAL' })
  expect(result.result).toBe('SYNTHETIC_RESULT')
})

import { expect, test } from 'claude-code/testing'

test('counts two synthetic stubbed tool calls', async ($, on) => {
  on('tool.call', () => ({ result: 'stubbed' }))
  await $.tool.call({ tool: 'Bash', command: 'echo synthetic' })
  await $.tool.call({ tool: 'Read', file_path: 'SYNTHETIC_NOT_REAL' })
  const result = await $.command.run({ command: 'safe-count', args: '' })
  expect(result.text).toBe('count:2')
})

import { expect, test } from 'claude-code/testing'

test('a mocked readonly Read permission check keeps its original decision', async ($, on) => {
  on('tool.check', () => ({ decision: 'ask', reason: 'MOCKED_READ_ONLY_REVIEW' }))
  const observed = await $.tool.check({ tool: 'Read', input: { file_path: 'MOCK_NOT_A_REAL_FILE' } })
  expect(observed.decision).toBe('ask')
  expect(observed.reason).toBe('MOCKED_READ_ONLY_REVIEW')
})

test('a mocked Write ask routes to a human but does not perform a write', async ($, on) => {
  on('tool.check', () => ({ decision: 'ask', reason: 'MOCKED_WRITE_REVIEW' }))
  const observed = await $.tool.check({ tool: 'Write', input: { file_path: 'MOCK_NOT_A_REAL_FILE', content: 'NOT_EXECUTED' } })
  expect(observed.decision).toBe('ask')
  expect(observed.decider).toBe('person')
})

test('a mocked deny must remain deny regardless of the new decider option', async ($, on) => {
  on('tool.check', () => ({ decision: 'deny', reason: 'MOCKED_DENIAL' }))
  const observed = await $.tool.check({ tool: 'Write', input: { file_path: 'MOCK_NOT_A_REAL_FILE', content: 'NOT_EXECUTED' } })
  expect(observed.decision).toBe('deny')
  expect(observed.reason).toBe('MOCKED_DENIAL')
})

test('a simulated gating exception invokes catch and fails closed', async ($, on) => {
  on('tool.check', () => ({ decision: 'ask', reason: 'MOCKED_ORIGINAL_ASK' }))
  const observed = await $.tool.check({
    tool: 'Write',
    input: { file_path: 'QA_FORCE_EXCEPTION_NO_REAL_FILE', content: 'NOT_EXECUTED' }
  })
  expect(observed.decision).toBe('deny')
  expect(observed.reason).toBe('QA_SYNTHETIC_HOOK_ERROR_BLOCKED')
})

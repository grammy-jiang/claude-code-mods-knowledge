/* Native Claude Code MOCKS ONLY; never invoke a real Read tool. */
import { expect, test } from 'claude-code/testing';

test('original downstream Read result and single execution survive', async ($, on) => {
  let calls = 0;
  on('tool.call', () => {
    calls += 1;
    return { result: 'QA_EXACT_DOWNSTREAM_RESULT' };
  });
  const result = await $.tool.call({ tool: 'Read', file_path: 'QA_MOCK_ONLY' });
  expect(result.result).toBe('QA_EXACT_DOWNSTREAM_RESULT');
  expect(calls).toBe(1);
});

test('original downstream denial and single execution survive', async ($, on) => {
  let calls = 0;
  on('tool.call', () => {
    calls += 1;
    return { result: 'QA_EXACT_DOWNSTREAM_DENIAL', isError: true };
  });
  const result = await $.tool.call({ tool: 'Read', file_path: 'QA_MOCK_ONLY' });
  expect(result.result).toBe('QA_EXACT_DOWNSTREAM_DENIAL');
  expect(result.isError).toBe(true);
  expect(calls).toBe(1);
});

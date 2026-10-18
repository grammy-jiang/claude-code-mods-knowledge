/*
 * TRUSTED synthetic observer behavior harness. Imported candidates are exact
 * hash-checked code emitted in genuine native model answers, staged by
 * audit_p5_original_model_code.py. NEVER run this harness outside Linux
 * Bubblewrap with no network, no host Home and only its own writable /work.
 *
 * These tests cover observer pass-through contracts, NOT genuine Claude Code
 * Mod runtime, permission approvals, or target-native API type definitions.
 */
import assert from 'node:assert/strict';
import test from 'node:test';

const candidates = [
  ['codex-01.mjs', false, true],
  ['codex-02.mjs', true, true],
  ['sonnet-01.mjs', false, false],
  ['sonnet-02.mjs', true, false],
  ['sonnet-03.mjs', true, true],
];

function capture(register) {
  let callback;
  let registrations = 0;
  const result = register((event, handler) => {
    assert.equal(event, 'tool.call');
    assert.equal(typeof handler, 'function');
    assert.equal(handler.length, 3);
    assert.equal(callback, undefined);
    callback = handler;
    registrations += 1;
  });
  assert.equal(registrations, 1);
  assert.equal(result, undefined);
  assert.equal(typeof callback, 'function');
  return callback;
}

async function withLogger(value, task) {
  const previous = console.log;
  console.log = value;
  try { return await task(); }
  finally { console.log = previous; }
}

const event = Object.freeze({
  type: 'Read', opaqueIdentity: Object.freeze({ x: 7 }),
  tool: Object.freeze({ name: 'Read', arguments: Object.freeze({ path: 'synthetic' }) }),
});
const outcome = Object.freeze({ ok: true, value: Object.freeze([0, 1, 2]) });
const originalError = new Error('synthetic original downstream exception');
const diagnosticError = new Error('synthetic logger diagnostic exception');

for (const [file, emitsDiagnostic, selfContained] of candidates) {
  await test(file, { concurrency: false }, async t => {
    const imported = await import('file:///work/candidates/' + file);
    assert.equal(typeof imported.register, 'function');
    assert.ok(selfContained === true || selfContained === false);
    const handler = capture(imported.register);

    await t.test('preserves downstream value identity and exact event identity', async () => {
      let calls = 0;
      const returnValue = await handler({}, event, async e => {
        calls += 1;
        assert.equal(e, event);
        return outcome;
      });
      assert.equal(calls, 1);
      assert.equal(returnValue, outcome);
      assert.deepEqual(event.tool.arguments, { path: 'synthetic' });
    });

    await t.test('passes primitive and null downstream outcomes unchanged', async () => {
      for (const value of [undefined, null, 0, false, 'text']) {
        let calls = 0;
        const returned = await handler({}, event, async e => {
          assert.equal(e, event);
          calls += 1;
          return value;
        });
        assert.equal(returned, value);
        assert.equal(calls, 1);
      }
    });

    await t.test('preserves original synchronous downstream failure identity', async () => {
      let calls = 0;
      await assert.rejects(
        handler({}, event, e => {
          assert.equal(e, event);
          calls += 1;
          throw originalError;
        }),
        reason => reason === originalError,
      );
      assert.equal(calls, 1);
    });

    await t.test('preserves asynchronous downstream Promise rejection identity', async () => {
      let calls = 0;
      await assert.rejects(
        handler({}, event, async e => {
          assert.equal(e, event);
          calls += 1;
          throw originalError;
        }),
        reason => reason === originalError,
      );
      assert.equal(calls, 1);
    });

    await t.test('synchronous diagnostic throw never replaces original value', async () => {
      let calls = 0;
      await withLogger(() => { throw diagnosticError; }, async () => {
        const result = await handler({}, event, async e => {
          assert.equal(e, event);
          calls += 1;
          return outcome;
        });
        assert.equal(result, outcome);
      });
      assert.equal(calls, 1);
    });

    await t.test('synchronous diagnostic throw never replaces original error', async () => {
      let calls = 0;
      await withLogger(() => { throw diagnosticError; }, async () => {
        await assert.rejects(
          handler({}, event, async e => {
            assert.equal(e, event);
            calls += 1;
            throw originalError;
          }),
          reason => reason === originalError,
        );
      });
      assert.equal(calls, 1);
    });

    await t.test('asynchronous logger rejection cannot shadow downstream result/error', async () => {
      let calls = 0;
      await withLogger(() => Promise.reject(diagnosticError), async () => {
        assert.equal(await handler({}, event, async e => {
          assert.equal(e, event);
          calls += 1;
          return outcome;
        }), outcome);
        await assert.rejects(
          handler({}, event, async e => {
            assert.equal(e, event);
            calls += 1;
            throw originalError;
          }),
          reason => reason === originalError,
        );
      });
      assert.equal(calls, 2);
    });

    await t.test('async next must settle before observer finishes', async () => {
      let resolveNext;
      let calls = 0;
      const pending = new Promise(resolve => { resolveNext = resolve; });
      let settled = false;
      const returnPromise = handler({}, event, e => {
        assert.equal(e, event);
        calls += 1;
        return pending;
      }).then(value => {
        settled = true;
        return value;
      });
      await Promise.resolve();
      assert.equal(settled, false);
      resolveNext(outcome);
      assert.equal(await returnPromise, outcome);
      assert.equal(settled, true);
      assert.equal(calls, 1);
    });

    if (emitsDiagnostic) {
      await t.test('async diagnostic completes before observer resolves', async () => {
        let resolveDiagnostic;
        let logStarted = false;
        let logFinished = false;
        await withLogger(() => {
          logStarted = true;
          return new Promise(resolve => {
            resolveDiagnostic = () => { logFinished = true; resolve(); };
          });
        }, async () => {
          let completed = false;
          const pending = handler({}, event, async () => outcome).then(v => {
            completed = true;
            return v;
          });
          await Promise.resolve();
          assert.equal(logStarted, true);
          assert.equal(completed, false);
          resolveDiagnostic();
          assert.equal(await pending, outcome);
          assert.equal(logFinished, true);
        });
      });
    }
  });
}

import assert from 'node:assert/strict';
import test from 'node:test';
import { register as safeRegister } from './transparent-safe.mjs';
import { register as unsafeRegister } from './transparent-unsafe.mjs';

function capture(register) {
  let handler;
  register((name, cb) => {
    assert.equal(name, 'tool.call');
    assert.equal(handler, undefined);
    handler = cb;
  });
  assert.equal(typeof handler, 'function');
  return handler;
}
async function withLogger(overrides, callback) {
  const log = console.log;
  const error = console.error;
  Object.assign(console, overrides);
  try { return await callback(); }
  finally { console.log = log; console.error = error; }
}
const event = Object.freeze({ type: 'Read', opaque: true });
const expectedResult = Object.freeze({ downstream: 'original' });
const downstreamError = new Error('original downstream failure');
const loggerError = new Error('diagnostic transport failure');

test('known broken observer overwrites success when post-next console logging throws', async () => {
  const unsafe = capture(unsafeRegister);
  await withLogger({ log() { throw loggerError; }, error() {} }, async () => {
    await assert.rejects(unsafe({}, event, async () => expectedResult), err => err === loggerError);
  });
});

test('known broken observer masks original failure if catch diagnostic throws', async () => {
  const unsafe = capture(unsafeRegister);
  await withLogger({ error() { throw loggerError; } }, async () => {
    await assert.rejects(unsafe({}, event, async () => { throw downstreamError; }), err => err === loggerError);
  });
});

test('safe observer preserves exact result and calls next once despite sync logging failure', async () => {
  const safe = capture(safeRegister);
  let called=0;
  await withLogger({ log() { throw loggerError; } }, async () => {
    assert.equal(await safe({}, event, async (arg) => { assert.equal(arg,event);called++;return expectedResult; }), expectedResult);
  });
  assert.equal(called,1);
});

test('safe observer preserves exact original error and calls next once despite sync logger failure', async () => {
  const safe = capture(safeRegister);
  let called=0;
  await withLogger({ log() { throw loggerError; } }, async () => {
    await assert.rejects(safe({}, event, async arg => {assert.equal(arg,event);called++;throw downstreamError;}), err => err===downstreamError);
  });
  assert.equal(called,1);
});

test('safe observer catches asynchronous diagnostic Promise rejection without changing outcome', async () => {
  const safe = capture(safeRegister);
  await withLogger({ log() { return Promise.reject(loggerError); } }, async () => {
    assert.equal(await safe({},event,async()=>expectedResult),expectedResult);
    await assert.rejects(safe({},event,async()=>{throw downstreamError;}),error=>error===downstreamError);
  });
});

test('unguarded finally logger masks successful result when diagnostic throws', async () => {
  const flawed = async ($, e, next) => {
    try { return await next(e); }
    finally { console.log('diagnostic'); }
  };
  let calls = 0;
  await withLogger({ log() { throw loggerError; } }, async () => {
    await assert.rejects(
      flawed({}, event, async arg => { assert.equal(arg,event); calls++; return expectedResult; }),
      error => error === loggerError,
    );
  });
  assert.equal(calls,1);
});

test('unguarded finally logger masks original downstream error when diagnostic rejects', async () => {
  const flawed = async ($, e, next) => {
    try { return await next(e); }
    finally { await Promise.resolve(console.log('diagnostic')); }
  };
  let calls = 0;
  await withLogger({ log() { return Promise.reject(loggerError); } }, async () => {
    await assert.rejects(
      flawed({}, event, async arg => { assert.equal(arg,event); calls++; throw downstreamError; }),
      error => error === loggerError,
    );
  });
  assert.equal(calls,1);
});

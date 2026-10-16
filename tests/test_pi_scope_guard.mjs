import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, symlinkSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import register, { scopedPathAllowed } from "../scripts/p5_pi_scope_guard.mjs";

test("native tool guard scopes reads and blocks path escape without touching results", () => {
  const root = mkdtempSync(join(tmpdir(), "p5-pi-native-guard-"));
  try {
    const work = join(root, "work");
    const skill = join(root, "skills");
    const outside = join(root, "private");
    for (const p of [work, skill, outside]) mkdirSync(p);
    const allowedFile = join(work, "test.ts");
    const privateFile = join(outside, "private.txt");
    writeFileSync(allowedFile, "harmless");
    writeFileSync(privateFile, "private");
    symlinkSync(privateFile, join(work, "sneaky"));
    assert.equal(scopedPathAllowed(allowedFile, [work, skill], work), true);
    assert.equal(scopedPathAllowed(privateFile, [work, skill], work), false);
    assert.equal(scopedPathAllowed(join(work, "sneaky"), [work, skill], work), false);

    process.env.P5_PI_ALLOWED_WORKSPACE = work;
    process.env.P5_PI_ALLOWED_SKILL_ROOT = skill;
    const handlers = new Map();
    register({ on(name, handler) { handlers.set(name, handler); } });
    const guard = handlers.get("tool_call");
    assert.equal(typeof guard, "function");
    assert.equal(guard({ toolName: "read", input: { path: allowedFile } }), undefined);
    assert.equal(guard({ toolName: "ls", input: {} }), undefined);
    assert.equal(guard({ toolName: "read", input: { path: privateFile } }).block, true);
    assert.equal(guard({ toolName: "read", input: { path: join(work, "sneaky") } }).block, true);
    assert.equal(guard({ toolName: "bash", input: { command: "echo private" } }).block, true);
    assert.equal(guard({ toolName: "find", input: { path: ".", pattern: "../../*" } }).block, true);
    assert.equal(guard({ toolName: "grep", input: { path: ".", pattern: "x", glob: "../../*" } }).block, true);
  } finally {
    rmSync(root, { recursive: true, force: true });
    delete process.env.P5_PI_ALLOWED_WORKSPACE;
    delete process.env.P5_PI_ALLOWED_SKILL_ROOT;
  }
});

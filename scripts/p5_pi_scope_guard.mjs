/**
 * Test-only Pi Agent 1.3.0 native tool_call scope guard.
 * Loaded explicitly; never auto-installed into the user's production Agent.
 *
 * It intentionally blocks out-of-workspace file reads rather than rewriting
 * model/tool responses. It emits NO file content or private paths.
 */
import { realpathSync } from "node:fs";
import { isAbsolute, resolve, dirname, sep } from "node:path";

const ALLOWED_TOOLS = new Set(["read", "ls", "find", "grep"]);

function exactRealpath(target) {
  try {
    return realpathSync(target);
  } catch {
    // A nonexistent file can still be safely scoped by its real parent.
    try {
      return resolve(realpathSync(dirname(target)), target.split(sep).at(-1));
    } catch {
      return null;
    }
  }
}

function isWithin(value, root) {
  return value === root || value.startsWith(root + sep);
}

export function scopedPathAllowed(rawPath, allowedRoots, cwd) {
  if (typeof rawPath !== "string" || rawPath.length > 2048 || rawPath.includes("\0")) {
    return false;
  }
  const absolute = resolve(cwd, rawPath);
  const real = exactRealpath(absolute);
  return real !== null && allowedRoots.some((root) => { const verified = exactRealpath(root); return verified !== null && isWithin(real, verified); });
}

export default function register(pi) {
  const workspaceRaw = process.env.P5_PI_ALLOWED_WORKSPACE;
  const skillRaw = process.env.P5_PI_ALLOWED_SKILL_ROOT;
  const workspace = typeof workspaceRaw === "string" ? exactRealpath(workspaceRaw) : null;
  const skill = typeof skillRaw === "string" ? exactRealpath(skillRaw) : null;
  const roots = [workspace, skill].filter((x) => typeof x === "string");
  const cwd = workspace ?? "/nonexistent-p5-denied";

  pi.on("tool_call", (event) => {
    if (!ALLOWED_TOOLS.has(event.toolName) || roots.length !== 2) {
      return { block: true, terminate: true, reason: "P5 scoped read-only tools required" };
    }
    const input = event.input ?? {};
    const target = typeof input.path === "string" ? input.path : ".";
    if (!scopedPathAllowed(target, roots, cwd)) {
      return { block: true, terminate: true, reason: "P5 read path outside isolated test scope" };
    }
    if (event.toolName === "find" || event.toolName === "grep") {
      for (const pattern of [input.pattern, input.glob]) {
        if (typeof pattern !== "string") continue;
        if (
          pattern.length > 2048 ||
          isAbsolute(pattern) ||
          pattern.split(/[\\/]/).includes("..")
        ) {
          return { block: true, terminate: true, reason: "P5 search pattern escaped scope" };
        }
      }
    }
    // Allow native Pi read-only tool execution untouched.
    return undefined;
  });
}

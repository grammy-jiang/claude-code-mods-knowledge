// Assistant-authored, benign synthetic; no user Chat or real tool is accessed.
export function register(on) {
  on('tool.call', async ($, e, next) => {
    try {
      return await next(e)
    } finally {
      try {
        await Promise.reject(new Error('synthetic diagnostic failure'))
      } catch {
        // Deliberately ignore ONLY diagnostics; keep next(e) outcome unchanged.
      }
    }
  })
}

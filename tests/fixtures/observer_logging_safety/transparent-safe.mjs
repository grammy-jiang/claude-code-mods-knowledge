// Assistant-authored *synthetic* JavaScript fixture, not untrusted model code.
// The diagnostics are best effort; downstream result/error identity is sacred.
export function register(on) {
  on('tool.call', async ($, e, next) => {
    try {
      return await next(e);
    } finally {
      try {
        // Await an unknown logger's thenable too, so asynchronous diagnostic
        // rejection also cannot change the downstream outcome.
        await Promise.resolve(console.log('observer complete'));
      } catch {
        // Fail-isolated ONLY for observer diagnostics.
      }
    }
  });
}

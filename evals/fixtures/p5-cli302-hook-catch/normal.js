export function register(on) {
  on('tool.call', async ($, e, next) => {
    try {
      return await next(e);
    } finally {
      try {
        await Promise.resolve($.ui.log('QA observer finished', { to: 'debug' }));
      } catch {
        // Only optional diagnostics are discarded.
      }
    }
  }).catch(async ($, e, next) => next(e));
}

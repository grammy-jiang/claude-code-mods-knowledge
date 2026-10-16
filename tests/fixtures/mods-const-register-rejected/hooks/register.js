// Intentionally INVALID source solely for offline version-specific negative QA.
function createRegister() {
  return function (on) {
    on('tool.call', async ($, e, next) => next(e))
  }
}
export const register = createRegister()

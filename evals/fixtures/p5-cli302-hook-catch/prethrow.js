export function register(on) {
  on('tool.call', async ($, e, next) => {
    throw new Error('QA_SYNTHETIC_BEFORE_NEXT');
  }).catch(async ($, e, next) => next(e));
}

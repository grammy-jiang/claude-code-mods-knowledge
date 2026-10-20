export function register(on) {
  on('tool.call', async ($, e, next) => {
    await next(e);
    throw new Error('QA_SYNTHETIC_AFTER_NEXT');
  }).catch(async ($, e, next) => ({ deny: 'QA_WITHHELD_ORIGINAL_RESULT' }));
}

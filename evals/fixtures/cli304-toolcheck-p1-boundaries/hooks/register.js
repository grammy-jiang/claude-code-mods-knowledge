export function register(on) {
  on('tool.check', async ($, e, next) => {
    if (e.tool === 'Write' && e.input?.file_path === 'QA_FORCE_THROW_NOT_REAL') throw new Error('QA_ONLY');
    const origin = await next(e);
    if (e.tool === 'Read') {
      return {
        ...origin,
        reason: `QA_READONLY_${String(e.isReadOnly)}_FROZEN_${String(Object.isFrozen(e))}_INPUT_${String(Object.isFrozen(e.input))}`
      };
    }
    if (origin.decision === 'ask') return {...origin,decider:'person'};
    return origin;
  }).catch(($ , e, next) => ({decision:'deny', reason:'QA_SYNTHETIC_FAIL_CLOSED'}));
}

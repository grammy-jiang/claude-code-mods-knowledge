export function register(on) {
  on('tool.check', async ($, e, next) => {
    const input = e.input;
    if (e.tool === 'Write' && input && typeof input === 'object' &&
        input.file_path === 'QA_FORCE_EXCEPTION_NO_REAL_FILE') {
      throw new Error('QA_SYNTHETIC_GATING_FAILURE');
    }
    const originalVerdict = await next(e);
    if (e.isReadOnly || originalVerdict.decision !== 'ask') {
      return originalVerdict;
    }
    return { ...originalVerdict, decider: 'person' };
  }).catch(($ , e, next) => ({
    decision: 'deny',
    reason: 'QA_SYNTHETIC_HOOK_ERROR_BLOCKED'
  }));
}

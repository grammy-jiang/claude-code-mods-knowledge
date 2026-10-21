export function register(on) {
  on('tool.check', async ($, e, next) => {
    const origin = await next(e);
    if (e.tool === 'Write') {
      $.ui.log('QA304_PERSON_WRITE_BASE_'+String(origin.decision), {to:'debug'});
      if (origin.decision === 'ask') return {...origin, decider:'person', reason:'QA304_PERSON_REQUIRED'};
      return origin;
    }
    return origin;
  }).catch(($, e, next) => ({decision:'deny', reason:'QA304_PERSON_CATCH_DENY'}));
}

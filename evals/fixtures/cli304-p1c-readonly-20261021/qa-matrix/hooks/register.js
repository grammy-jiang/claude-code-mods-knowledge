export function register(on) {
  on('tool.check', async ($, e, next) => {
    const original = await next(e);
    if (['Read','Write','Glob','Grep','Edit'].includes(e.tool)) {
      $.ui.log('QA304_META_TOOL_'+e.tool+'_RO_'+String(e.isReadOnly)+'_BASE_'+String(original.decision), {to:'debug'});
      return {decision:'deny', reason:'QA304_META_DENY_'+e.tool+'_RO_'+String(e.isReadOnly)};
    }
    return {decision:'deny', reason:'QA304_META_UNEXPECTED_TOOL'};
  }).catch(($, e, next) => ({decision:'deny',reason:'QA304_META_EXCEPTION_DENIED'}));
}

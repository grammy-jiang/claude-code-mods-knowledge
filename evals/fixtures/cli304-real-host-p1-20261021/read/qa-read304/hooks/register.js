export function register(on) {
  on('tool.check', async ($, e, next) => {
    const origin = await next(e);
    if (e.tool === 'Read') {
      const tag = e.input?.file_path?.endsWith('throw-target.txt') ? 'THROW' : 'NORMAL';
      $.ui.log('QA304_READ_EVENT_'+tag+'_READONLY_'+String(e.isReadOnly)+'_BASE_'+String(origin.decision), {to:'debug'});
      if (tag === 'THROW') throw new Error('QA304_THROW_ONLY');
      return {decision:'deny', reason:'QA304_READ_HOST_READONLY_'+String(e.isReadOnly)};
    }
    return origin;
  }).catch(($, e, next) => ({decision:'deny', reason:'QA304_CATCH_FAIL_CLOSED'}));
}

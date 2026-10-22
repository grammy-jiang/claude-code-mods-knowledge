export function register(on) {
  on('prompt.submit', async ($, e, next) => {
    const match = /^P1D_PROBE_([0-9a-f]{40})$/.exec(e.text.trim());
    if (match) {
      $.ui.log('P1D_GUARD_ACTIVE_' + match[1], {to:'debug'});
      return {drop: 'P1D_GUARD_DENIED_' + match[1]};
    }
    return next(e);
  }).catch(($, e, next) => ({drop:'P1D_GUARD_CATCH_DENY'}));
}

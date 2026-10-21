export function register(on) {
  on('prompt.submit', async ($, e, next) => {
    $.ui.log('QA304_RELOAD_PREVIOUS_HOOK_ACTIVE', {to:'debug'});
    return next(e);
  }).catch(($ ,e,next) => ({drop:'QA304_RELOAD_FAIL_CLOSED'}));
}

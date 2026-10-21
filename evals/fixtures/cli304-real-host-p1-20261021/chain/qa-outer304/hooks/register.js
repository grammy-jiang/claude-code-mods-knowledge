export function register(on) {
  on('tool.call', { tool: 'Read' }, async ($, e, next) => {
    $.ui.log('QA304_OUTER_PASS_ENTER', {to:'debug'});
    return next(e);
  }).catch(($ ,e,next) => ({deny:'QA304_OUTER_CATCH_DENY'}));
}

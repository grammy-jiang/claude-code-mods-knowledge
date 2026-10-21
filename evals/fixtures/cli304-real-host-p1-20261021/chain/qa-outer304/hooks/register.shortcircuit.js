export function register(on) {
  on('tool.call', { tool: 'Read' }, async ($, e, next) => {
    $.ui.log('QA304_OUTER_ENTER', {to:'debug'});
    return {deny:'QA304_OUTER_SHORT_CIRCUIT'};
  }).catch(($ ,e,next) => ({deny:'QA304_OUTER_CATCH_DENY'}));
}

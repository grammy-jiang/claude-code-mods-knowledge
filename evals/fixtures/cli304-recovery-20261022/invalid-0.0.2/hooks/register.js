export function register(on) {
  on('prompt.submit', async ($, e, next) => {
    $.ui.log('QA304_GUARD_ENTRY', {to:'debug'});
    if (e.text.includes('QA304_BENIGN_BLOCK_THIS')) return {drop:'QA304_GUARD_DENIED_TEST_ONLY'};
    return next(e);
  }).catch(($, e, next) => ({drop:'QA304_GUARD_CATCH_DENIED'}));
}

export function corrupted_qa_only( {

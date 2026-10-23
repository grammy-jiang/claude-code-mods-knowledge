export function register(on) {
  on('turn.step', async function* ($, e, next) {
    $.ui.log('QA309_TURN_STEP_MODEL_ALIAS_REQUESTED', {to: 'debug'})
    yield* next({...e, model: 'haiku'})
  }).catch(async function* ($, e, next) {
    yield* next(e)
  })
}

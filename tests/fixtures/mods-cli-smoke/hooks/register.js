let count = 0
export function register(on) {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'safe-count',
      description: 'Return number of observed synthetic tool calls',
    })
    return next(e)
  })
  on('tool.call', async ($, e, next) => {
    count += 1
    return next(e)
  })
  on('command.run', { command: 'safe-count' }, async () => ({
    text: 'count:' + count,
  }))
}

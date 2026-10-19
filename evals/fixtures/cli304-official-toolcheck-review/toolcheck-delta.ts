import type { On, Register } from 'claude-code';

const safeProbe: Register = (on: On) => {
  on('tool.check', async ($, e, next) => {
    const readFlag: true | undefined = e.isReadOnly;
    void readFlag;
    const originalVerdict = await next(e);
    return {
      ...originalVerdict,
      decision: 'ask' as const,
      decider: 'person' as const,
    };
  });
};
void safeProbe;

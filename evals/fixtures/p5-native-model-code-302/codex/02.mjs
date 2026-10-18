export function register(on) {
  on("tool.call", async ($, e, next) => {
    try {
      return await next(e);
    } finally {
      try {
        await Promise.resolve(console.log("observer done"));
      } catch {
        // 仅忽略诊断失败，保留下游结果或异常。
      }
    }
  });
}
   on('tool.call', async ($, e, next) => {
     try {
       return await next(e);
     } finally {
       try {
         await Promise.resolve(console.log("observer done"));
       } catch { /* 仅忽略诊断失败 */ }
     }
   });
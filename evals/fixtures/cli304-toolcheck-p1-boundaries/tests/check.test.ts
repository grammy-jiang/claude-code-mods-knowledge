import { expect, test } from 'claude-code/testing'
test('Read surfaces expected metadata', async ($,on) => {
 on('tool.check',()=>({decision:'ask',reason:'QA_ORIGINAL'}))
 const x=await $.tool.check({tool:'Read',input:{file_path:'QA_NOT_REAL'}})
 expect(x.decision).toBe('ask')
 expect(x.reason).toBe('QA_READONLY_undefined_FROZEN_true_INPUT_true')
})
test('Write ask is delegated to person',async($,on)=>{
 on('tool.check',()=>({decision:'ask',reason:'QA_WRITE_ASK'}))
 const x=await $.tool.check({tool:'Write',input:{file_path:'QA_NOT_REAL',content:'NO_SIDE_EFFECT'}})
 expect(x.decision).toBe('ask');expect(x.decider).toBe('person');expect(x.reason).toBe('QA_WRITE_ASK')
})
test('Write deny must remain deny',async($,on)=>{
 on('tool.check',()=>({decision:'deny',reason:'QA_RULE_DENY'}))
 const x=await $.tool.check({tool:'Write',input:{file_path:'QA_NOT_REAL',content:'NO_SIDE_EFFECT'}})
 expect(x.decision).toBe('deny');expect(x.reason).toBe('QA_RULE_DENY')
})
test('Write allow remains allow',async($,on)=>{
 on('tool.check',()=>({decision:'allow',reason:'QA_RULE_ALLOW'}))
 const x=await $.tool.check({tool:'Write',input:{file_path:'QA_NOT_REAL',content:'NO_SIDE_EFFECT'}})
 expect(x.decision).toBe('allow');expect(x.reason).toBe('QA_RULE_ALLOW')
})
test('Thrown hook denied by registration catch',async($,on)=>{
 on('tool.check',()=>({decision:'ask',reason:'QA_PRIOR_ASK'}))
 const x=await $.tool.check({tool:'Write',input:{file_path:'QA_FORCE_THROW_NOT_REAL',content:'NO_SIDE_EFFECT'}})
 expect(x.decision).toBe('deny');expect(x.reason).toBe('QA_SYNTHETIC_FAIL_CLOSED')
})

test('A deliberately injected synthetic read-only flag can be read', async ($,on) => {
 on('tool.check',()=>({decision:'ask',reason:'QA_REVIEW'}))
 const x=await $.tool.check({tool:'Read',input:{file_path:'QA_NOT_REAL'},isReadOnly:true})
 expect(x.decision).toBe('ask')
 expect(x.reason).toBe('QA_READONLY_true_FROZEN_true_INPUT_true')
})

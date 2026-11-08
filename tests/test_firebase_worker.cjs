const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function worker(owner){
  const shown=[],handlers={};let receiver;
  const location=new URL('https://ancu.example/firebase-messaging-sw.js?config=%7B%22projectId%22%3A%22test%22%7D');
  const context={URL,console,importScripts:()=>{},
    self:{location,addEventListener:(event,fn)=>handlers[event]=fn,
      registration:{showNotification:async(title,options)=>shown.push({title,...options})}},
    caches:{open:async()=>({match:async()=>owner?{json:async()=>({userId:owner})}:undefined})},
    firebase:{initializeApp:()=>{},messaging:()=>({onBackgroundMessage:fn=>receiver=fn})}};
  vm.runInNewContext(fs.readFileSync('frontend/firebase-messaging-sw.js','utf8'),context);
  return {shown,handlers,receive:payload=>receiver(payload),setOwner:value=>owner=value,context};
}
test('background push checks recipient, logout and new owner before display',async()=>{
  const w=worker('3'),data={user_id:'3',title:'Notice',body:'Open inbox',notification_id:'18'};
  await w.receive({data});assert.equal(w.shown.length,1);assert.equal(w.shown[0].tag,'ancu-18');
  await w.receive({data:{...data,user_id:'4'}});assert.equal(w.shown.length,1);
  w.setOwner(null);await w.receive({data});assert.equal(w.shown.length,1);
  w.setOwner('4');await w.receive({data});assert.equal(w.shown.length,1);
  await w.receive({data:{...data,user_id:'4'}});assert.equal(w.shown.length,2);
  await w.receive({notification:{title:'legacy'}});assert.equal(w.shown.length,2);
});
test('click reuses a same-origin tab and navigates only to the inbox',async()=>{
  const w=worker('3'),calls=[];
  w.context.clients={matchAll:async()=>[{url:'https://ancu.example/#profile',navigate:async url=>calls.push(url),focus:async()=>calls.push('focus')}],openWindow:()=>assert.fail('should reuse tab')};
  let promise;
  w.handlers.notificationclick({notification:{close:()=>calls.push('close'),data:{url:'https://evil.example'}},waitUntil:p=>promise=p});
  await promise;assert.deepEqual(calls,['close','/#notifications','focus']);
});

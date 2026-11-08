'use strict';

// One browser subscription has one owner. Use separate browser profiles for
// simultaneous push to different accounts. No login token is persisted here.
window.AnCuPush = (() => {
  const storageKey='ancu_push_owner',cacheName='ancu-push',ownerPath='/__ancu_push_owner__';
  let context=null,queue=Promise.resolve(),sdk=null,messaging=null,unsubscribe=null;
  const owner=()=>{try{return JSON.parse(localStorage.getItem(storageKey)||'null');}catch{return null;}};
  const serial=task=>{const next=queue.then(task,task);queue=next.catch(()=>{});return next;};
  const active=()=>!!context&&owner()?.userId===context.userId&&window.Notification?.permission==='granted';
  async function request(ctx,method,path,body){
    const response=await fetch(path,{method,headers:{Authorization:`Bearer ${ctx.auth}`,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{}),keepalive:method==='DELETE'});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'Không thể cập nhật thông báo trình duyệt.');
    return data;
  }
  async function forget(ctx,previous){
    const local=(async()=>{
      if('caches' in window){const cache=await caches.open(cacheName);await cache.delete(ownerPath);}
      const registration=await navigator.serviceWorker?.getRegistration('/');
      for(const notice of await registration?.getNotifications()||[])notice.close();
      await (await registration?.pushManager.getSubscription())?.unsubscribe();
      if(sdk&&messaging)await sdk.deleteToken(messaging);
    })();
    const remote=ctx&&previous?.token?request(ctx,'DELETE','/api/notifications/push-tokens',{token:previous.token}):Promise.resolve();
    const results=await Promise.allSettled([local,remote]);
    if(results[0].status==='rejected')throw new Error('Chưa tắt được thông báo trên thiết bị. Hãy chặn quyền thông báo trong cài đặt trang.');
  }
  function stop(){
    const previous=owner(),ctx=context;
    context=null;unsubscribe?.();unsubscribe=null;
    localStorage.removeItem(storageKey);
    return serial(()=>forget(ctx,previous));
  }
  async function start(auth,userId,onMessage){
    const previous=owner(),oldContext=context,ctx={auth,userId:String(userId),onMessage};
    context=ctx;
    if(previous&&(previous.userId!==ctx.userId||window.Notification?.permission!=='granted')){
      localStorage.removeItem(storageKey);unsubscribe?.();unsubscribe=null;
      await serial(()=>forget(oldContext,previous));
    }
    if(context!==ctx)return;
    // Refresh registration/listeners after reload, without prompting again.
    if(active())return enable(false);
  }
  function enable(interactive=true){
    const ctx=context;
    if(!ctx)return Promise.reject(new Error('Vui lòng đăng nhập lại.'));
    if(!window.isSecureContext)return Promise.reject(new Error('Hãy mở bằng localhost trên máy này hoặc địa chỉ HTTPS.'));
    if(!('Notification' in window)||!('serviceWorker' in navigator)||!('PushManager' in window))return Promise.reject(new Error('Trình duyệt này chưa hỗ trợ thông báo đẩy.'));
    // Request permission during the click, before asynchronous network work.
    const permission=interactive?Notification.requestPermission():Promise.resolve(Notification.permission);
    return serial(async()=>{
      if(await permission!=='granted')throw new Error('Bạn chưa cho phép thông báo. Bật quyền tại biểu tượng cạnh địa chỉ trang web.');
      const settings=await request(ctx,'GET','/api/notifications/push-config');
      if(!settings.configured)throw new Error('Firebase chưa được cấu hình đầy đủ. Thông báo vẫn được lưu tại bảng tin.');
      if(context!==ctx)return;
      const [firebase,messagingSdk]=await Promise.all([
        import('https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js'),
        import('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging.js')]);
      if(!await messagingSdk.isSupported())throw new Error('Trình duyệt chưa hỗ trợ Firebase push; thử Chrome hoặc Edge bản mới.');
      if(context!==ctx)return;
      const {vapidKey,...config}=settings.config;
      const application=firebase.getApps().find(app=>app.options.projectId===config.projectId)||firebase.initializeApp(config,config.projectId);
      const registration=await navigator.serviceWorker.register('/firebase-messaging-sw.js?config='+encodeURIComponent(JSON.stringify(config)));
      await navigator.serviceWorker.ready;
      sdk=messagingSdk;messaging=sdk.getMessaging(application);
      const token=await sdk.getToken(messaging,{vapidKey,serviceWorkerRegistration:registration});
      if(!token)throw new Error('Chưa đăng ký được thiết bị; kiểm tra VAPID và kết nối Internet.');
      if(context!==ctx){await sdk.deleteToken(messaging);return;}
      await request(ctx,'POST','/api/notifications/push-tokens',{token});
      if(context!==ctx){await forget(ctx,{token});return;}
      const cache=await caches.open(cacheName);
      await cache.put(ownerPath,new Response(JSON.stringify({userId:ctx.userId}),{headers:{'Content-Type':'application/json'}}));
      if(context!==ctx){await forget(ctx,{token});return;}
      localStorage.setItem(storageKey,JSON.stringify({userId:ctx.userId,token}));
      unsubscribe?.();
      unsubscribe=sdk.onMessage(messaging,payload=>{
        if(context===ctx&&active()&&payload.data?.user_id===ctx.userId)ctx.onMessage(payload.data);
      });
    });
  }
  function disable(){
    const ctx=context,previous=owner();
    localStorage.removeItem(storageKey);unsubscribe?.();unsubscribe=null;
    context=ctx?{...ctx}:null;
    return serial(()=>forget(ctx,previous));
  }
  return {start,stop,enable,disable,active};
})();

/* Public Firebase configuration is provided by the authenticated opt-in flow. */
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('notificationclick',event=>{
  event.notification.close();
  event.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(async windows=>{
    const existing=windows.find(client=>new URL(client.url).origin===self.location.origin);
    if(existing){await existing.navigate('/#notifications');return existing.focus();}
    return clients.openWindow('/#notifications');
  }));
});
async function showOwnedNotification(payload){
  const data=payload.data;
  if(!data?.user_id||!data.title)return;
  const cache=await caches.open('ancu-push');
  const response=await cache.match('/__ancu_push_owner__');
  if(!response||(await response.json()).userId!==data.user_id)return;
  return self.registration.showNotification(data.title,{
    body:data.body||'',tag:'ancu-'+data.notification_id,
    icon:'/assets/favicon.svg',data:{notification_id:data.notification_id}
  });
}
const configText=new URL(self.location.href).searchParams.get('config');
if(configText){
  try{
    const config=JSON.parse(configText);
    importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js','https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');
    firebase.initializeApp(config);
    firebase.messaging().onBackgroundMessage(showOwnedNotification);
  }catch{console.warn('An Cư: thông báo đẩy chưa khởi tạo được.');}
}

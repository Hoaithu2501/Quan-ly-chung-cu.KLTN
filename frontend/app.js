'use strict';

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const money = value => new Intl.NumberFormat('vi-VN', {style:'currency',currency:'VND',maximumFractionDigits:0}).format(Number(value || 0));
const number = value => new Intl.NumberFormat('vi-VN').format(Number(value || 0));
const date = value => {if(!value)return '—';const parsed=new Date(/^\d{4}-\d{2}-\d{2}$/.test(String(value))?value+'T12:00:00':String(value).replace(' ','T'));return Number.isNaN(parsed.getTime())?'Chưa cập nhật':new Intl.DateTimeFormat('vi-VN',{day:'2-digit',month:'2-digit',year:'numeric'}).format(parsed);};
// SQLite CURRENT_TIMESTAMP is UTC even when the container TZ is Vietnam.
// Explicit offsets from payments are respected; date-only deadlines stay dates.
function dateTime(value){
  if(!value)return 'Chưa ghi nhận';
  let text=String(value).trim().replace(' ','T');
  if(/^\d{4}-\d{2}-\d{2}$/.test(text))return `${date(text)} (chưa có giờ)`;
  if(!/(Z|[+-]\d{2}:?\d{2})$/i.test(text))text+='Z';
  const parsed=new Date(text);
  return Number.isNaN(parsed.getTime())?'Chưa cập nhật':new Intl.DateTimeFormat('vi-VN',{
    timeZone:'Asia/Ho_Chi_Minh',day:'2-digit',month:'2-digit',year:'numeric',
    hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'
  }).format(parsed);
}
const today = () => new Date().toLocaleDateString('en-CA', {timeZone:'Asia/Ho_Chi_Minh'});
const thisYear = () => new Date().getFullYear();
const icons = {
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  building:'<path d="M4 21V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v16M17 9h3v12M2 21h20M8 7h1m3 0h1M8 11h1m3 0h1M8 15h1m3 0h1M9 21v-3h3v3"/>',
  people:'<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6m2 3a5 5 0 0 1 3 4v3"/>',
  invoice:'<path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z"/><path d="M9 7h6m-6 4h6m-6 4h3"/>',
  car:'<path d="m5 7 2-4h10l2 4 2 4v7H3v-7l2-4Zm0 0h14M3 12h18M5 18v3m14-3v3M6 15h2m8 0h2"/>',
  wrench:'<path d="M14 6a5 5 0 0 0-6 6l-5 5a2.1 2.1 0 0 0 3 3l5-5a5 5 0 0 0 6-6l-3 3-3-3 3-3Z"/><path d="m18 3 3 3"/>',
  bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  message:'<path d="M21 11a8 8 0 0 1-8 8H8l-5 3V5a3 3 0 0 1 3-3h7a8 8 0 0 1 8 9Z"/><path d="M7 7h8M7 11h8M7 15h4"/>',
  chart:'<path d="M4 3v18h18M8 16v-4m5 4V7m5 9V3"/>',
  bot:'<rect x="3" y="6" width="18" height="15" rx="4"/><path d="M12 6V3m-1 0h2M7 11v2m10-2v2m-9 4h8M1 11v5m22-5v5"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  chevron:'<path d="m9 5 7 7-7 7"/>',
  down:'<path d="m6 9 6 6 6-6"/>',
  plus:'<path d="M12 4v16M4 12h16"/>',
  search:'<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
  logout:'<path d="M9 4H4v16h5m6-13 5 5-5 5m-7-5h12"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  menu:'<path d="M3 5h18M3 12h18M3 19h18"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 11h18m-14 4h2m4 0h2"/>',
  wallet:'<path d="M20 7V4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16V7H4a1 1 0 0 1 0-2"/><path d="M20 11h-5v5h5m-2-3h-1"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 15v6h16v-6"/>',
  refresh:'<path d="M20 8a8 8 0 0 0-14-3L3 8m0-5v5h5m-4 8a8 8 0 0 0 14 3l3-3m0 5v-5h-5"/>',
  edit:'<path d="m16 3 5 5-12 12H4v-5L16 3Zm-3 3 5 5M3 22h18"/>',
  shield:'<path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4Z"/><path d="m8 12 3 3 5-6"/>',
  send:'<path d="m22 2-7 20-4-9L2 9 22 2ZM11 13 22 2"/>',
  location:'<path d="M19 9c0 6-7 13-7 13S5 15 5 9a7 7 0 1 1 14 0Z"/><circle cx="12" cy="9" r="2"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.grid}</svg>`;
const state = {token:sessionStorage.getItem('ancu_token'),user:null,route:'overview',tab:{},data:{},sequence:0,chat:[],notificationTimer:null};
const roleNames = {admin:'Ban quản lý',resident:'Cư dân',technician:'Kỹ thuật viên'};
const admin = () => state.user?.role === 'admin';
const tech = () => state.user?.role === 'technician';
const resident = () => state.user?.role === 'resident';
const billingTitle = () => admin()?'Quản lý hóa đơn':'Hóa đơn & thanh toán';
const navItems = [
  ['overview','Tổng quan','grid',['admin','resident','technician']],
  ['apartments','Quản lý căn hộ','building',['admin']],
  ['residents','Cư dân & hợp đồng','people',['admin']],
  ['profile','Thông tin cá nhân','people',['resident']],
  ['billing','Hóa đơn & thanh toán','invoice',['admin','resident']],
  ['parking','Quản lý gửi xe','car',['admin','resident','technician']],
  ['maintenance','Sửa chữa & bảo trì','wrench',['admin','resident','technician']],
  ['notifications','Thông báo','bell',['admin','resident','technician']],
  ['complaints','Khiếu nại & đăng ký','message',['admin','resident']],
  ['reports','Báo cáo & thống kê','chart',['admin']],
  ['users','Nhân sự & tài khoản','shield',['admin']],
  ['chatbot','Trợ lý An Cư','bot',['admin','resident','technician']],
];
const statusLabels = {paid:'Đã thanh toán',unpaid:'Chưa thanh toán',overdue:'Quá hạn',occupied:'Đã có cư dân',vacant:'Còn trống',empty:'Còn trống',active:'Đang hoạt động',cancelled:'Đã hủy',pending:'Chờ xử lý',processing:'Đang xử lý',in_progress:'Đang xử lý',completed:'Hoàn thành',resolved:'Đã giải quyết',rejected:'Từ chối',expired:'Hết hạn',terminated:'Đã kết thúc',owner:'Sở hữu',tenant:'Thuê',rent:'Thuê',own:'Sở hữu',high:'Cao',medium:'Trung bình',low:'Thấp',success:'Thành công',failed:'Thất bại'};
const typeLabels = {repair:'Sửa chữa',maintenance:'Bảo trì',cut_service:'Tạm ngưng dịch vụ',restore_service:'Khôi phục dịch vụ',complaint:'Khiếu nại',registration:'Đơn đăng ký',general:'Thông báo chung',private:'Thông báo riêng',car:'Ô tô',motorbike:'Xe máy',motorcycle:'Xe máy',bicycle:'Xe đạp',electric_bike:'Xe điện',monthly:'Hàng tháng',semiannual:'6 tháng',cash:'Tiền mặt',bank_transfer:'Chuyển khoản',qr:'QR',sepay:'VietQR · SePay',parking:'Gửi xe',payment:'Thanh toán',electricity:'Điện',water:'Nước',awaiting_confirmation:'Chờ ngân hàng xác nhận',matched:'Đã đối soát',partial:'Chuyển thiếu',overpaid:'Chuyển dư',duplicate:'Chuyển lặp',unmatched:'Chưa xác định hóa đơn',ignored:'Không ghi nhận thu',refunded:'Đã hoàn trả',retained:'Đã thống nhất giữ lại',reviewed:'Đã kiểm tra'};
const label = value => statusLabels[value] || typeLabels[value] || value || '—';
const badge = value => `<span class="badge ${['paid','active','completed','resolved','success','occupied'].includes(value)?'green':['unpaid','pending','medium','processing'].includes(value)?'amber':['overdue','high','rejected','failed'].includes(value)?'red':['in_progress','owner'].includes(value)?'blue':''}">${esc(label(value))}</span>`;

async function api(path, options = {}) {
  const headers = {'Accept':'application/json',...(state.token?{'Authorization':`Bearer ${state.token}`} : {}),...options.headers};
  if (options.body && typeof options.body !== 'string') { headers['Content-Type']='application/json'; options.body = JSON.stringify(options.body); }
  let response;
  try { response = await fetch(path, {...options,headers}); }
  catch { throw new Error('Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối và thử lại.'); }
  let result;
  try { result = await response.json(); } catch { result = {}; }
  if (response.status === 401 && state.user) { logout(); throw new Error('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.'); }
  if (!response.ok) {
    const error=new Error(result.error || result.message || `Yêu cầu chưa thực hiện được (${response.status}).`);
    error.code=result.code;error.reason=result.reason;error.status=response.status;throw error;
  }
  return result;
}
const items = async path => (await api(path)).items || [];
const post = (path, body={}) => api(path,{method:'POST',body});
const patch = (path, body) => api(path,{method:'PATCH',body});
function toast(message, error = false) {
  const item = document.createElement('div'); item.className=`toast${error?' error':''}`;item.textContent=message;
  $('#toasts').append(item);setTimeout(()=>item.remove(),5500);
}
function button(text, action, glyph='plus', style='primary', extra='') {
  return `<button type="button" class="button ${style} inline-flex items-center justify-center gap-2 rounded-xl font-medium focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-forest-600" data-action="${esc(action)}" ${extra}>${glyph?icon(glyph):''}${esc(text)}</button>`;
}
function heading(title, subtitle, actions='', eyebrow='') {
  return `<div class="page-heading flex flex-wrap items-start justify-between gap-4"><div>${eyebrow?`<div class="eyebrow">${esc(eyebrow)}</div>`:''}<h1>${esc(title)}</h1>${subtitle?`<p>${esc(subtitle)}</p>`:''}</div>${actions?`<div class="heading-actions">${actions}</div>`:''}</div>`;
}
function stat(title,value,note,glyph='building',tone='',unit='') {
  const currency=String(value).includes('₫');
  return `<div class="stat-card min-w-0"><div class="stat-top"><span>${esc(title)}</span><span class="stat-icon ${tone}">${icon(glyph)}</span></div><div class="stat-value${currency?' stat-value--currency':''}">${esc(value)}${unit?`<small>${esc(unit)}</small>`:''}</div><div class="stat-foot">${esc(note)}</div></div>`;
}
function empty(title='Chưa có dữ liệu',description='Dữ liệu sẽ xuất hiện tại đây khi được cập nhật.',action='') {
  return `<div class="empty-state">${icon('building')}<h3>${esc(title)}</h3><p>${esc(description)}</p>${action}</div>`;
}
function table(columns, rows, options={}) {
  if (!rows.length) return empty(options.emptyTitle,options.emptyDescription);
  return `<div class="table-scroll overflow-x-auto"><table class="data-table w-full text-left"><thead><tr>${columns.map(c=>`<th scope="col">${esc(c[0])}</th>`).join('')}</tr></thead><tbody>${rows.map((row,i)=>`<tr data-search="${esc(Object.values(row).join(' ').toLowerCase())}" data-status="${esc(row.status || '')}">${columns.map(c=>`<td>${c[1](row,i)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${options.count===false?'':`<div class="row-count">${rows.length} bản ghi</div>`}`;
}
function toolbar(placeholder='Tìm kiếm…',statuses=[]) {
  return `<div class="toolbar"><div class="search-box">${icon('search')}<input type="search" id="table-search" placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}"></div>${statuses.length?`<div class="filter-group"><select id="table-status" aria-label="Lọc trạng thái"><option value="">Tất cả trạng thái</option>${statuses.map(x=>`<option value="${esc(x)}">${esc(label(x))}</option>`).join('')}</select></div>`:''}</div>`;
}
function tabs(route, tabsList) {
  const active=state.tab[route]||tabsList[0][0];
  return `<div class="tabs" role="tablist" aria-label="Chọn danh sách">${tabsList.map(([key,text])=>`<button class="tab ${active===key?'active':''}" role="tab" aria-selected="${active===key}" data-action="tab" data-tab="${esc(key)}">${esc(text)}</button>`).join('')}</div>`;
}
function field(name,title,type='text',value='',attrs='') {
  const id=`field-${name}`;
  const isReq = attrs.includes('required') || title.includes('*');
  const cleanTitle = esc(title.replace(/\s*\*/g, '').replace(/\s*\(không bắt buộc\)/g, ''));
  const labelHtml = isReq ? `${cleanTitle} <span class="req-star">*</span>` : cleanTitle;
  return `<div class="field ${type==='textarea'?'wide':''}"><label for="${id}">${labelHtml}</label>${type==='textarea'?`<textarea id="${id}" name="${esc(name)}" ${attrs}>${esc(value)}</textarea>`:`<input id="${id}" name="${esc(name)}" type="${type}" value="${esc(value)}" ${attrs}>`}</div>`;
}
function select(name,title,options,value='',required=true) {
  const id=`field-${esc(name)}`;
  const isReq = Boolean(required) || title.includes('*');
  const cleanTitle = esc(title.replace(/\s*\*/g, '').replace(/\s*\(không bắt buộc\)/g, ''));
  const labelHtml = isReq ? `${cleanTitle} <span class="req-star">*</span>` : cleanTitle;
  return `<div class="field"><label for="${id}">${labelHtml}</label><select id="${id}" name="${esc(name)}" ${required?'required':''}>${!required?'<option value="">Chưa chọn</option>':''}${options.map(o=>`<option value="${esc(o[0])}" ${String(value)===String(o[0])?'selected':''}>${esc(o[1])}</option>`).join('')}</select></div>`;
}
const apartmentOptions = rows => rows.map(r=>[r.apartment_id,`${r.code} · Tòa ${r.block || '—'}`]);
const enumOptions = values => values.map(v=>[v,label(v)]);
const detail = entries => `<dl class="detail-list">${entries.map(([key,value,wide])=>`<div class="${wide?'wide':''}"><dt>${esc(key)}</dt><dd>${esc(value ?? '—')}</dd></div>`).join('')}</dl>`;
let modalSubmit=null,modalBlob=null,modalReturn=null,modalVersion=0;
let requestDrafts={complaint:{},registration:{}};
let paymentWatch=null;
function stopPaymentWatch(){
  if(paymentWatch){clearTimeout(paymentWatch.timer);clearInterval(paymentWatch.clock);paymentWatch.controller?.abort();}
  paymentWatch=null;
}
function closeModal(){
  ++modalVersion;
  if(modalReturn){
    const previous=modalReturn;modalReturn=null;
    $('#modal').replaceChildren(...previous.nodes);modalSubmit=previous.submit;
    $('#modal').scrollTop=previous.scrollTop;previous.focus?.focus({preventScroll:true});
    return;
  }
  stopPaymentWatch();$('#modal').close();
}
function openModal(title,body,footer='') {
  ++modalVersion;
  stopPaymentWatch();
  modalReturn=null;
  if(modalBlob){URL.revokeObjectURL(modalBlob);modalBlob=null;}
  const modal=$('#modal');
  delete modal.dataset.invoiceKind;delete modal.dataset.invoiceId;
  modal.innerHTML=`<div class="modal-header"><h2 id="modal-title">${esc(title)}</h2><button class="icon-button" data-action="close-modal" aria-label="Đóng">${icon('close')}</button></div>${body}${footer}`;
  if (!modal.open) modal.showModal();
}
function formModal(title,fields,onSubmit,submitText='Lưu thông tin',intro='',layout='') {
  modalSubmit=onSubmit;
  const gridClass=layout==='vertical'?'form-grid vertical':'form-grid';
  openModal(title,`<form id="modal-form"><div class="modal-body">${intro?`<div class="info-box">${esc(intro)}</div>`:''}<div class="form-error" role="alert" hidden></div><div class="${gridClass}">${fields}</div></div><div class="modal-footer">${button('Hủy','close-modal','', 'secondary')}<button type="submit" class="button primary">${icon('check')}${esc(submitText)}</button></div></form>`);
}
async function saved(action,message='Đã lưu thông tin.') {await action;modalReturn=null;closeModal();toast(message);await renderPage();}
function formValues(form) {
  const result={};for(const [key,value] of new FormData(form).entries()){if(value==='')continue;const input=form.elements.namedItem(key);result[key]=input?.type==='number'?Number(value):input?.type==='password'?String(value):String(value).trim();}return result;
}
function authView(register=false) {
  clearInterval(state.notificationTimer);
  clearInterval(state.billingTimer);
  $('#app').innerHTML=`<main class="auth-page${register?' auth-page--register':''}" id="main">
    <section class="auth-art" aria-label="Không gian An Cư">
      <div class="auth-photo absolute inset-0 overflow-hidden"><img class="h-full w-full object-cover" src="/assets/images/residence-detail.jpg" alt="Kiến trúc chung cư hiện đại" width="1200" height="1800" fetchpriority="high"><div class="auth-photo-shade"></div></div>
      <a class="brand" href="#" aria-label="An Cư"><div class="brand-mark">A</div><div><div class="brand-name">AN CƯ<span class="brand-dot">.</span></div><div class="brand-tag">Không gian sống · Kết nối cộng đồng</div></div></a>
      <div class="auth-image-inset"><img src="/assets/images/community-lounge.jpg" alt="Góc sinh hoạt với nội thất và cây xanh" width="900" height="1350" decoding="async"><span>Nhịp sống an cư</span></div>
      <div class="auth-intro"><div class="auth-visual-label"><span class="live-dot"></span> Sống an tâm. Kết nối dễ dàng.</div><h1>Chốn an cư.<br>Điều tốt đẹp<br>mỗi ngày.</h1><p>Từ những tiện ích thường ngày đến sự gắn kết trong cộng đồng. An Cư đồng hành cùng không gian sống của bạn.</p><div class="auth-feature-pills hidden min-[701px]:flex flex-wrap gap-3"><span>${icon('building')} Quản lý thuận tiện</span><span>${icon('people')} Cộng đồng gắn kết</span></div></div>
      <footer><span>An Cư · Cổng thông tin chung cư</span></footer>
    </section>
    <section class="auth-main"><form id="auth-form" class="auth-form" data-register="${register}">
      <div class="auth-welcome-icon" aria-hidden="true">${icon('building')}</div><div class="eyebrow">Chào mừng đến An Cư</div><h2>${register?'Bắt đầu kết nối':'Chào mừng trở lại'}</h2><p class="auth-subtitle">${register?'Tạo tài khoản để quản lý tiện ích và kết nối với Ban quản lý.':'Đăng nhập để chăm sóc không gian sống của bạn.'}</p><div class="form-error" role="alert" hidden></div>
      ${register?field('full_name','Họ và tên','text','','required autocomplete="name" minlength="10" maxlength="50"'):''}
      ${field('username','Tên đăng nhập','text','',`required autocomplete="username" minlength="3" maxlength="${register?20:60}" ${register?'pattern="[A-Za-z0-9_.\\-]{3,20}" title="Tên đăng nhập gồm 3–20 chữ cái, số, dấu chấm, gạch dưới hoặc gạch ngang."':''} placeholder="Nhập tên đăng nhập"`)}
      ${register?field('apartment_code','Số căn hộ','text','','required maxlength="30" placeholder="Ví dụ: A-0101"')+field('email','Email','email','','required autocomplete="email" placeholder="ten@gmail.com" pattern="[A-Za-z0-9]+([.][A-Za-z0-9]+)*@[gG][mM][aA][iI][lL][.][cC][oO][mM]" title="Email phải có đuôi @gmail.com"')+field('phone','Số điện thoại','tel','','required autocomplete="tel" maxlength="20"'):''}
      ${field('password','Mật khẩu','password','',`required autocomplete="${register?'new-password':'current-password'}" minlength="${register?'6':'1'}" maxlength="${register?30:128}"`)}
      <button type="submit" class="button primary">${register?'Tạo tài khoản cư dân':'Đăng nhập'} ${icon('arrow')}</button><p class="auth-switch">${register?'Đã có tài khoản?':'Bạn là cư dân mới?'} <button type="button" class="text-button" data-action="auth-switch" data-register="${!register}">${register?'Đăng nhập':'Đăng ký tài khoản'}</button></p>
      <div class="auth-note flex items-start gap-3">${icon('shield')}<span>${register?'Ban quản lý sẽ xác nhận thông tin và liên kết căn hộ với tài khoản của bạn.':'Cần hỗ trợ truy cập? Vui lòng liên hệ Ban quản lý chung cư để được hướng dẫn.'}</span></div>
    </form><div class="auth-form-footer">Một không gian. Mọi kết nối.</div></section>
  </main>`;
}
function residentApartmentLabel(profile){
  return profile.apartment_codes?.length?profile.apartment_codes.join(', '):profile.registered_apartment_code||'Chưa liên kết';
}
async function loadResidentContext(){
  if(!resident())return;
  const userId=state.user.user_id;
  try{
    const profile=await api('/api/residents/me');
    if(!state.user||state.user.user_id!==userId)return;
    state.data.personal=profile;
    state.user.full_name=profile.full_name;state.user.apartment_label=profile.apartment_codes?.length?profile.apartment_codes.join(', '):profile.registered_apartment_code?`${profile.registered_apartment_code} (chưa xác nhận)`:'Chưa liên kết';
    const greet=$('#header-greeting-title');if(greet)greet.textContent=`Xin chào, ${state.user.full_name||state.user.username} 👋`;
    const nameEl=$('#account-label');if(nameEl)nameEl.textContent=state.user.full_name||state.user.username;
    const aptEl=$('#resident-apt-tag');if(aptEl)aptEl.textContent=state.user.apartment_label?`Căn hộ ${state.user.apartment_label}`:'';
  }catch{/* Keep navigation usable when profile service is unavailable. */}
}
function shell() {
  clearInterval(state.notificationTimer);
  clearInterval(state.billingTimer);
  const name=state.user.username;
  const fullName=state.user.full_name||name;
  const nav=navItems.filter(n=>n[3].includes(state.user.role)).map(n=>n[0]==='billing'?[n[0],billingTitle(),...n.slice(2)]:n);
  const brandHref=resident()?'#profile':'#overview';
  const dateStr=esc(new Intl.DateTimeFormat('vi-VN',{day:'numeric',month:'long',year:'numeric'}).format(new Date()));
  const bellBtn=`<button class="icon-button notification-bell" data-action="navigate" data-route="notifications" aria-label="Xem thông báo" style="position:relative">${icon('bell')}<span class="notification-badge" id="notification-badge" hidden></span></button>`;
  const logoutBtn=`<button class="icon-button" data-action="logout" aria-label="Đăng xuất" title="Đăng xuất">${icon('logout')}</button>`;

  let headerLeft='', headerRight='';
  if(resident()){
    headerLeft=`<div class="header-greeting"><strong class="greeting-title" id="header-greeting-title">Xin chào, ${esc(fullName)} 👋</strong><span class="greeting-subtitle">Sẻ chia không gian, nhân đôi hạnh phúc.</span></div>`;
    headerRight=`<div class="resident-identity"><strong id="account-label">${esc(fullName)}</strong><span class="apt-tag" id="resident-apt-tag">${state.user.apartment_label?`Căn hộ ${esc(state.user.apartment_label)}`:''}</span></div>${bellBtn}<span class="top-date">${icon('calendar')} ${dateStr}</span>${logoutBtn}`;
  }else{
    headerLeft=`<div class="header-greeting"><strong class="greeting-title" id="header-greeting-title">Xin chào, ${esc(fullName)} 👋</strong><span class="greeting-subtitle">Cùng chăm sóc một cộng đồng an cư mỗi ngày.</span></div>`;
    headerRight=`<span class="top-date">${icon('calendar')} ${dateStr}</span>${bellBtn}<div class="user-control"><span class="avatar grid shrink-0 place-items-center">${esc(name.slice(0,2).toUpperCase())}</span><div class="user-info"><strong id="account-label">${esc(name)}</strong><small>${esc(roleNames[state.user.role])}</small></div>${logoutBtn}</div>`;
  }

  $('#app').innerHTML=`<div class="layout"><button class="mobile-scrim" aria-label="Đóng điều hướng" data-action="menu-close"></button><aside class="sidebar"><a class="brand" href="${brandHref}" aria-label="An Cư - Trang chủ"><div class="brand-mark">A</div><div><div class="brand-name">AN CƯ<span class="brand-dot">.</span></div><div class="brand-tag">Quản lý chung cư</div></div></a><div class="workspace-label">${icon('building')}<div>Cổng thông tin chung cư<small>${esc(roleNames[state.user.role])}</small></div></div><div class="nav-heading">Không gian làm việc</div><nav class="nav" aria-label="Điều hướng chính">${nav.map(n=>`<a href="#${n[0]}" data-route="${n[0]}">${icon(n[2])}<span>${n[1]}</span></a>`).join('')}</nav><div class="sidebar-bottom"><div class="support-card">${icon('bot')}<strong>Mọi câu hỏi, một trợ lý</strong>Tra cứu chính sách và tiện ích chung cư bất cứ lúc nào.<button data-action="navigate" data-route="chatbot">Trò chuyện ngay ${icon('arrow')}</button></div></div></aside><div class="body-area"><header class="topbar"><button class="icon-button mobile-menu" data-action="menu" aria-label="Mở điều hướng">${icon('menu')}</button>${headerLeft}<div class="topbar-right">${headerRight}</div></header><main class="main" id="main" tabindex="-1"><div id="page"></div><footer class="page-footer"><span>© ${thisYear()} An Cư. Kết nối một cộng đồng tốt đẹp hơn.</span><span>${icon('shield')} Cổng thông tin quản lý chung cư</span></footer></main></div></div>`;
  loadResidentContext();
  const hashRoute=location.hash.slice(1);
  state.route=(hashRoute==='chatbot'||nav.some(n=>n[0]===hashRoute))?hashRoute:(resident()?'profile':'overview');
  renderPage();
  pollNotifications();
  state.notificationTimer=setInterval(pollNotifications,5000);
  state.billingTimer=setInterval(refreshBilling,5000);
  resumePayment();
  AnCuPush.start(state.token,state.user.user_id,payload=>{
    toast(payload.title||'Bạn có thông báo mới.');pollNotifications();
    if(state.route==='notifications'&&!$('#modal').open)renderPage();
  }).catch(()=>{});
}
function logout() {
  AnCuPush.stop().catch(error=>toast(error.message,true));
  state.pushUnsubscribe?.();state.pushUnsubscribe=null;state.lastNotificationId=null;state.token=null;state.user=null;state.data={};state.chat=[];state.tab={};modalReturn=null;sessionStorage.removeItem('ancu_token');sessionStorage.removeItem('ancu_push_token');closeModal();authView();
}
function navigate(route) {if(location.hash===`#${route}`){state.route=route;renderPage();}else location.hash=route;}
function closeMenu() {$('.sidebar')?.classList.remove('open');$('.mobile-scrim')?.classList.remove('open');}
async function pollNotifications() {
  if(!state.user||document.hidden||state.notificationPolling)return;
  const user=state.user;state.notificationPolling=true;
  try {
    const list=await items('/api/notifications');
    if(state.user!==user)return;
    const count=list.filter(n=>!n.is_read).length;
    const badgeEl=$('#notification-badge');
    if(badgeEl){badgeEl.hidden=!count;badgeEl.textContent=count>99?'99+':String(count);}
    const latest=list[0]?.notification_id;
    if(state.lastNotificationId!=null&&latest&&latest!==state.lastNotificationId){toast('Bạn có thông báo mới tại bảng tin.');if(state.route==='notifications'&&!$('#modal').open)renderPage();}
    state.lastNotificationId=latest;
  }catch{/* A service outage must not interrupt the active form. */}
  finally{state.notificationPolling=false;}
}
async function refreshBilling(){
  if(!state.user||state.route!=='billing'||document.hidden||state.billingRefreshing||$('#page')?.getAttribute('aria-busy')==='true')return;
  state.billingRefreshing=true;
  const version=modalVersion,user=state.user,modal=$('#modal');
  try{
    if(modal.open){
      const kind=modal.dataset.invoiceKind,id=modal.dataset.invoiceId;
      if(!kind||!id)return; // Leave forms, receipts and the QR watcher alone.
      const row=await api(`/api/billing/invoices/${kind}/${id}`);
      if(state.user!==user||state.route!=='billing'||modalVersion!==version||!modal.open)return;
      if(JSON.stringify(row)!==JSON.stringify(state.currentInvoice))await invoiceDetail(kind,id,row);
    }else await renderPage({background:true});
  }catch{/* Keep the current view and retry when the connection recovers. */}
  finally{state.billingRefreshing=false;}
}
async function renderPage({background=false}={}) {
  if(!state.user)return;
  const allowed=navItems.filter(n=>n[3].includes(state.user.role));
  if(state.route!=='chatbot'&&!allowed.some(n=>n[0]===state.route))state.route=resident()?'profile':'overview';
  const seq=++state.sequence;
  const page=$('#page');if(!page)return;
  const route=state.route,previousRoute=page.dataset.route,scrollY=window.scrollY;
  page.setAttribute('aria-busy','true');
  const navTitle=state.route==='chatbot'?'Trợ lý cư dân':state.route==='billing'?billingTitle():(allowed.find(n=>n[0]===state.route)?.[1]||'An Cư');
  document.title=`${navTitle} · An Cư`;
  const bc=$('#breadcrumb-title');if(bc)bc.textContent=navTitle;
  $$('[data-route].active').forEach(n=>n.classList.remove('active'));
  $(`.nav [data-route="${state.route}"]`)?.classList.add('active');
  if(!page.hasChildNodes())page.innerHTML='<div class="loading" role="status"><span class="spinner"></span>Đang tải dữ liệu…</div>';
  closeMenu();
  try {
    const html=await pages[route]();if(seq!==state.sequence||!state.user)return;
    if(background&&($('#modal').open||document.hidden))return;
    if(background&&state.billingMarkup===html)return;
    const search=background?$('#table-search')?.value:null,status=background?$('#table-status')?.value:null;
    const focused=background?document.activeElement?.id:null;
    page.innerHTML=html;page.dataset.route=route;
    state.billingMarkup=route==='billing'?html:null;
    if(background){
      if($('#table-search')&&search!=null)$('#table-search').value=search;
      if($('#table-status')&&status!=null)$('#table-status').value=status;
      filterTable();
      if(['table-search','table-status'].includes(focused))document.getElementById(focused)?.focus({preventScroll:true});
    }
    if(previousRoute===route)window.scrollTo({top:scrollY,behavior:'instant'});
    else window.scrollTo({top:0,behavior:'instant'});
  }
  catch(error){if(seq!==state.sequence||!state.user||background)return;page.dataset.route=route;page.innerHTML=`${heading(navTitle,'Dữ liệu hiện chưa sẵn sàng.')}<div class="error-box" role="alert">${esc(error.message)}</div>${button('Thử lại','refresh','refresh','secondary')}`;}
  finally{if(seq===state.sequence)page.setAttribute('aria-busy','false');}
}

function revenueChart(rows,height=220) {
  if(!rows.length||!rows.some(r=>Number(r.collected_amount)>0))return '<div class="empty-chart">Chưa có doanh thu đã thu trong kỳ.<br>Biểu đồ sẽ cập nhật khi ghi nhận thanh toán.</div>';
  const width=650,left=65,right=15,top=15,bottom=35,chartHeight=height-top-bottom,chartWidth=width-left-right,max=Math.max(...rows.map(r=>Number(r.collected_amount||0)),1)*1.18;
  const gap=chartWidth/rows.length,barWidth=Math.min(30,gap*.5);
  let body='';for(let i=0;i<=4;i++){const y=top+chartHeight*(1-i/4),v=max*i/4;body+=`<line class="gridline" x1="${left}" y1="${y}" x2="${width-right}" y2="${y}"/><text x="${left-10}" y="${y+3}" text-anchor="end">${esc(v>=1000000?`${(v/1000000).toFixed(1)} tr`:number(Math.round(v)))}</text>`;}
  rows.forEach((r,i)=>{const value=Number(r.collected_amount||0),barHeight=value/max*chartHeight,x=left+gap*i+(gap-barWidth)/2;body+=`<rect class="bar" x="${x}" y="${top+chartHeight-barHeight}" width="${barWidth}" height="${barHeight}" rx="3"><title>${esc(r.period)}: ${esc(money(value))}</title></rect><text x="${x+barWidth/2}" y="${height-12}" text-anchor="middle">${esc(String(r.period).replace(/^\d{4}-/,'').replace('Q','Quý '))}</text>`;});
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Biểu đồ doanh thu đã thu theo kỳ">${body}</svg>`;
}
function invoiceColumns(withActions=true) {
  return [
    ['Hóa đơn',r=>`<span class="primary-cell">#${r.invoice_type==='semiannual'?'DV':'HD'}${esc(String(r.invoice_id).padStart(4,'0'))}</span><span class="sub-cell">${esc(label(r.invoice_type))} · ${esc(r.period)}</span><span class="sub-cell">Lập: ${esc(dateTime(r.created_at))}</span>`],
    ['Căn hộ',r=>esc(r.apartment_code || apartmentCode(r.apartment_id))],
    ['Số tiền',r=>`<span class="money">${money(r.total_amount)}</span>`],
    ['Hạn thanh toán',r=>esc(date(r.due_date))],
    ['Trạng thái',r=>`${badge(r.status)}${r.paid_at?`<span class="sub-cell">${esc(dateTime(r.paid_at))}</span>`:''}`],
    ...(withActions?[['',r=>button(resident()&&r.status!=='paid'?'Thanh toán':'Chi tiết','invoice-detail','', 'link',`data-id="${esc(r.invoice_id)}" data-kind="${esc(r.invoice_type)}"`)]]:[])
  ];
}
function apartmentCode(id){return state.data.apartments?.find(a=>Number(a.apartment_id)===Number(id))?.code || `Căn hộ #${id}`;}
function overviewHero(){
  const title=admin()?'Vận hành tận tâm.<span>Cộng đồng an cư.</span>':tech()?'Chăm chút từng chi tiết.<span>An tâm mỗi ngày.</span>':'Một chốn bình yên.<span>Mọi kết nối gần hơn.</span>';
  const description=admin()?'Một góc nhìn trọn vẹn để chăm sóc cư dân, quản lý dịch vụ và giữ nhịp sống chung cư luôn thông suốt.':tech()?'Theo dõi công việc, cập nhật tiến độ và cùng xây dựng một không gian sống được chăm sóc chu đáo.':'Theo dõi hóa đơn, gửi yêu cầu và cập nhật tin tức của cộng đồng. Những việc thường ngày, gọn trong một nơi.';
  const primary=admin()?['Xem báo cáo','reports']:tech()?['Xem công việc','maintenance']:['Xem hóa đơn','billing'];
  return `<section class="overview-hero relative isolate overflow-hidden" aria-labelledby="overview-hero-title">
    <div class="overview-hero-copy"><div class="overview-hero-kicker"><span class="live-dot"></span> AN CƯ · GẮN KẾT MỖI NGÀY</div><h2 class="overview-hero-title" id="overview-hero-title">${title}</h2><p class="overview-hero-description">${description}</p><div class="overview-hero-actions flex flex-wrap items-center gap-3">${button(primary[0],'navigate','arrow','primary',`data-route="${primary[1]}"`)}${button('Bảng tin cộng đồng','navigate','bell','secondary','data-route="notifications"')}</div></div>
    <figure class="overview-hero-media relative m-0 min-w-0 overflow-hidden">
      <img class="hero-main-photo" src="/assets/images/residence-garden.jpg" alt="Khu căn hộ hiện đại với không gian xanh" width="1600" height="898" fetchpriority="high">
      <div class="hero-photo-inset"><img src="/assets/images/community-lounge.jpg" alt="Nội thất sáng và cây xanh" width="900" height="1350" decoding="async"><span>Chạm vào sự bình yên</span></div>
      <div class="hero-floating-note">${icon('people')}<span>Cùng nhau, gần hơn<small>Một không gian · Nhiều kết nối</small></span></div>
      <figcaption class="hero-image-caption">Không gian sống đầy cảm hứng</figcaption>
    </figure>
  </section>`;
}
function overviewShortcuts(){
  const entries=admin()?[
    ['Căn hộ & cư dân','Theo dõi không gian và hồ sơ','apartments','building'],
    ['Quản lý hóa đơn','Lập hóa đơn và theo dõi các khoản đã thu','billing','wallet'],
    ['Sửa chữa & bảo trì','Tiếp nhận và điều phối yêu cầu','maintenance','wrench']
  ]:tech()?[
    ['Công việc của tôi','Tiếp nhận và cập nhật tiến độ','maintenance','wrench'],
    ['Gửi thông báo','Kết nối với cư dân và Ban quản lý','notifications','bell'],
    ['Thu phí vãng lai','Ghi nhận doanh thu gửi xe','parking','car']
  ]:[
    ['Hồ sơ của tôi','Thông tin cư dân và căn hộ','profile','people'],
    ['Gửi yêu cầu','Để Ban quản lý hỗ trợ bạn','complaints','message'],
    ['Trợ lý An Cư','Tra cứu nội quy và tiện ích','chatbot','bot']
  ];
  const photos=['residence-garden.jpg','community-lounge.jpg','garden-walk.jpg'];
  return `<section aria-labelledby="overview-shortcuts-title"><div class="overview-section-heading"><div><div class="eyebrow">TIỆN ÍCH NHANH</div><h2 id="overview-shortcuts-title">Dành cho ngày của bạn</h2></div><p>Kết nối mọi việc, từ một nơi.</p></div><div class="overview-shortcuts grid gap-4">${entries.map(([title,description,route,glyph],index)=>`<button type="button" class="overview-shortcut" data-action="navigate" data-route="${route}"><span class="shortcut-media"><img src="/assets/images/${photos[index]}" alt="" width="${index===0?1600:900}" height="${index===0?898:1350}" loading="lazy" decoding="async"><span class="shortcut-index" aria-hidden="true">0${index+1}</span></span><span class="shortcut-body"><span class="shortcut-icon">${icon(glyph)}</span><span class="shortcut-copy min-w-0 flex-1"><strong>${title}</strong><span>${description}</span></span>${icon('arrow')}</span></button>`).join('')}</div></section>`;
}
function pageSpotlight(kind){
  const content=kind==='profile'
    ?['HỒ SƠ CƯ DÂN','Không gian riêng, kết nối chung.','Thông tin của bạn giúp Ban quản lý chăm sóc và hỗ trợ đúng lúc.','community-lounge.jpg']
    :['CHUYỆN CỦA CỘNG ĐỒNG','Mỗi cập nhật, một kết nối.','Theo dõi thông báo và những điều cần biết trong nhịp sống chung cư.','garden-walk.jpg'];
  return `<section class="page-spotlight" data-spotlight="${kind}"><div><div class="eyebrow">${content[0]}</div><h2>${content[1]}</h2><p>${content[2]}</p></div><img src="/assets/images/${content[3]}" alt="Không gian sống xanh" width="900" height="1350" decoding="async"></section>`;
}
const pages = {
  async profile() {
    const [account, personal]=await Promise.all([api('/api/auth/me'),api('/api/residents/me')]);
    state.data.personal=personal;state.data.account=account.user;
    return heading('Thông tin cá nhân','Xem và cập nhật hồ sơ cư dân của bạn.',button('Chỉnh sửa thông tin','profile-edit','edit')+button('Đổi mật khẩu','password-edit','shield','secondary'))+pageSpotlight('profile')+`<section class="panel"><div class="panel-header"><h2>Thông tin cư dân</h2><span class="period-chip">Hồ sơ của bạn</span></div><div class="panel-body">${detail([['Tên đăng nhập',account.user.username],['Số căn hộ',residentApartmentLabel(personal)],['Họ và tên',personal.full_name],['Email',account.user.email||'Chưa cập nhật'],['Số điện thoại',personal.phone||'Chưa cập nhật'],['CCCD',personal.id_card||'Chưa cập nhật'],['Loại cư dân',label(personal.relation_type)]])}</div></section>`;
  },
  async overview() {
    const endpoints = tech()?['/api/maintenance/tickets','/api/notifications','/api/parking/guest-daily']:['/api/apartments','/api/billing/summary','/api/billing/invoices/monthly','/api/billing/invoices/semiannual','/api/notifications','/api/maintenance/tickets',...(admin()?[`/api/billing/reports?year=${thisYear()}&group=month`]:[])];
    const result=await Promise.allSettled(endpoints.map(p=>api(p)));const data=result.map(r=>r.status==='fulfilled'?r.value:null),failed=result.filter(r=>r.status==='rejected').length;
    const warning=failed?`<div class="info-box">${failed} nguồn dữ liệu tạm thời chưa kết nối được. Bạn có thể mở từng chức năng hoặc tải lại trang để thử lại.</div>`:'';
    const top=heading('Tổng quan',admin()?'Nhịp sống cộng đồng, trong tầm tay bạn.':tech()?'Công việc hôm nay, không gian tốt hơn mỗi ngày.':'Chào ngày mới tại không gian của bạn.',button('Cập nhật','refresh','refresh','secondary'))+overviewHero();
    if(tech()){
      const tickets=data[0]?.items||[],notices=data[1]?.items||[],guests=data[2]?.items||[];state.data.tickets=tickets;
      return top+warning+`<div class="stats-grid grid grid-cols-2 gap-3 min-[1280px]:grid-cols-4 min-[1280px]:gap-5">${stat('Công việc được giao',number(tickets.length),'Tất cả phiếu của bạn','wrench')}${stat('Đang chờ xử lý',number(tickets.filter(t=>t.status==='pending').length),'Cần tiếp nhận','clock','orange')}${stat('Đang thực hiện',number(tickets.filter(t=>t.status==='in_progress').length),'Cập nhật tiến độ thường xuyên','wrench','blue')}${stat('Đã hoàn thành',number(tickets.filter(t=>t.status==='completed').length),'Phiếu đã đóng','check','purple')}</div><div class="dashboard-columns"><section class="panel"><div class="panel-header"><h2>Công việc cần xử lý</h2>${button('Tất cả','navigate','arrow','link','data-route="maintenance"')}</div>${table([['Yêu cầu',r=>`<span class="primary-cell">#${esc(r.ticket_id)} · ${esc(label(r.type))}</span><span class="sub-cell">${esc(r.description?.slice(0,80))}</span>`],['Ưu tiên',r=>badge(r.priority)],['Trạng thái',r=>badge(r.status)],['',r=>button('Xử lý','ticket-edit','','link',`data-id="${r.ticket_id}"`)]],tickets.filter(t=>t.status!=='completed').slice(0,5),{count:false})}</section>${noticePanel(notices)}</div><section class="panel"><div class="panel-header"><h2>Thao tác nhanh</h2></div><div class="quick-actions">${quick('Tiếp nhận công việc','maintenance','wrench')}${quick('Gửi thông báo','notifications','bell')}${quick('Thu phí vãng lai','parking','car')}${quick('Tra cứu chính sách','chatbot','bot')}</div></section>`;
    }
    const apartments=data[0]?.items||[],summary=data[1]||{},monthly=(data[2]?.items||[]).map(x=>({...x,invoice_type:'monthly'})),semi=(data[3]?.items||[]).map(x=>({...x,invoice_type:'semiannual'})),notices=data[4]?.items||[],tickets=data[5]?.items||[],report=data[6]||{};
    const bills=[...monthly,...semi];state.data.apartments=apartments;state.data.invoices=bills;state.data.notices=notices;
    const occupied=apartments.filter(a=>a.status==='occupied').length,percent=apartments.length?Math.round(occupied/apartments.length*100):0,openTickets=tickets.filter(t=>t.status!=='completed').length;
    const stats=admin()?stat('Tổng số căn hộ',number(apartments.length),`${occupied} căn hộ đã có cư dân`,'building')+stat('Đã thu thanh toán',money(summary.paid_amount),'Tổng hóa đơn đã thanh toán','wallet','blue')+stat('Công nợ hiện tại',money(summary.outstanding_amount),`${number(summary.overdue_count)} hóa đơn quá hạn`,'invoice','orange')+stat('Yêu cầu đang mở',number(openTickets),'Sửa chữa & bảo trì','wrench','purple'):stat('Căn hộ của bạn',number(apartments.length),'Căn hộ đã được xác nhận','building')+stat('Cần thanh toán',money(summary.outstanding_amount),'Tổng hóa đơn chưa thanh toán','wallet','orange')+stat('Đã thanh toán',money(summary.paid_amount),`${number(summary.paid_count)} hóa đơn hoàn tất`,'check','blue')+stat('Yêu cầu đang mở',number(openTickets),'Phiếu sửa chữa của bạn','wrench','purple');
    const chart=admin()?`<section class="panel"><div class="panel-header"><div><h2>Doanh thu dịch vụ</h2><p>Theo dõi thanh toán thực tế theo tháng</p></div><span class="period-chip">Năm ${thisYear()}</span></div><div class="chart-wrap">${revenueChart(report.items||[])}<div class="chart-caption">Doanh thu đã thu · Đơn vị: VNĐ</div></div></section><section class="panel"><div class="panel-header"><div><h2>Tình trạng căn hộ</h2><p>Không gian sống của cộng đồng</p></div></div><div class="occupancy"><div class="donut" style="--percent:${percent}%"></div><div class="donut-label"><strong>${percent}%</strong><span>Tỷ lệ lấp đầy</span></div></div><div class="occupancy-legend"><div><span><i></i>Đã có cư dân</span><strong>${occupied}</strong></div><div><span><i class="gray"></i>Còn trống</span><strong>${apartments.length-occupied}</strong></div></div></section>`:`<section class="panel"><div class="panel-header"><h2>Không gian của bạn</h2></div><div class="panel-body">${apartments.length?apartments.map(a=>`<div class="apartment-pill"><span>${icon('building')}</span><h2>Căn hộ ${esc(a.code)}</h2></div><p class="muted" style="font-size:12px;margin:12px 0 18px">Tòa ${esc(a.block)} · Tầng ${esc(a.floor)} · ${a.area==null?'Diện tích chưa cập nhật':`${esc(a.area)} m²`}</p>${detail([['Hình thức',label(a.contract_type)],['Trạng thái',label(a.status)],['Bắt đầu',date(a.start_date)],['Kết thúc',date(a.end_date)]])}`).join('<hr class="detail-separator">'):empty('Tài khoản chưa liên kết căn hộ','Vui lòng liên hệ Ban quản lý để xác nhận liên kết tài khoản với căn hộ.')}</div></section><section class="panel"><div class="panel-header"><h2>Luôn sẵn sàng hỗ trợ</h2></div><div class="panel-body"><div class="notice-symbol">${icon('bot')}</div><h3 style="margin:16px 0 10px">Bạn cần tìm thông tin gì?</h3><p class="muted" style="font-size:12px;line-height:1.9;margin-bottom:20px">Tra cứu nội quy, phí dịch vụ và vị trí tiện ích ngay trong trợ lý cư dân.</p>${button('Hỏi trợ lý An Cư','navigate','arrow','primary','data-route="chatbot"')}</div></section>`;
    const billsBlock=admin()?'':`<div class="dashboard-columns"><section class="panel"><div class="panel-header"><div><h2>Hóa đơn cần thanh toán</h2><p>Những khoản phí đang chờ hoàn tất</p></div>${button('Xem tất cả','navigate','arrow','link','data-route="billing"')}</div>${table(invoiceColumns(),bills.filter(b=>b.status!=='paid').sort((a,b)=>String(a.due_date).localeCompare(String(b.due_date))).slice(0,5),{count:false,emptyTitle:'Không có hóa đơn chờ thanh toán',emptyDescription:'Các khoản phí của bạn đã được cập nhật.'})}</section>${noticePanel(notices)}</div>`;
    const adminNoticeBlock=admin()?`<div style="margin-bottom:23px">${noticePanel(notices)}</div>`:'';
    return top+warning+`<div class="stats-grid grid grid-cols-2 gap-3 min-[1280px]:grid-cols-4 min-[1280px]:gap-5">${stats}</div>${overviewShortcuts()}<div class="dashboard-columns">${chart}</div>${billsBlock}${adminNoticeBlock}`;
  },
  async apartments(){
    const rows=await items('/api/apartments');state.data.apartments=rows;
    return heading('Quản lý căn hộ','Theo dõi không gian sống, tình trạng sử dụng và hợp đồng.',button('Thêm căn hộ','apartment-create'))+`<div class="stats-grid maintenance-stats">${stat('Tổng căn hộ',number(rows.length),'Toàn bộ các tòa nhà','building')}${stat('Đã có cư dân',number(rows.filter(r=>r.status==='occupied').length),'Hợp đồng đang hiệu lực','people','blue')}${stat('Căn hộ còn trống',number(rows.filter(r=>r.status!=='occupied').length),'Sẵn sàng đón cư dân','building','orange')}</div><section class="panel">${toolbar('Tìm mã căn hộ, tòa, cư dân…',['occupied','vacant'])}${table([['Căn hộ',r=>`<span class="apartment-pill"><span>${icon('building')}</span><span class="primary-cell">${esc(r.code)}</span></span>`],['Vị trí',r=>`Tòa ${esc(r.block)} · Tầng ${esc(r.floor)}`],['Diện tích',r=>r.area==null?'Chưa cập nhật':`${esc(r.area)} m²`],['Cư dân hiện tại',r=>`<span class="primary-cell">${esc(r.current_resident||'Chưa có cư dân')}</span><span class="sub-cell">${esc(label(r.contract_type))}</span>`],['Thời hạn còn lại',r=>r.remaining_days===null||r.remaining_days===undefined?'—':`${number(r.remaining_days)} ngày`],['Trạng thái',r=>badge(r.status)],['',r=>button('Chi tiết','apartment-detail','','link',`data-id="${r.apartment_id}"`)]],rows)}</section>`;
  },
  async residents(){
    const tab=state.tab.residents||'residents';
    const [residents,contracts,apartments,users]=await Promise.all([items('/api/residents'),items('/api/contracts'),items('/api/apartments'),items('/api/auth/users')]);Object.assign(state.data,{residents,contracts,apartments,users});
    const columns=tab==='residents'?[
      ['Cư dân',r=>`<span class="primary-cell">${esc(r.full_name)}</span><span class="sub-cell">Mã #${esc(r.resident_id)}</span>`],
      ['Căn hộ đang ở',r=>esc(r.apartment_codes?.length?r.apartment_codes.join(', '):(r.registered_apartment_code?`${r.registered_apartment_code} (đăng ký)`:'—'))],
      ['Số điện thoại',r=>esc(r.phone||'—')],
      ['CCCD / giấy tờ',r=>esc(r.id_card||'—')],
      ['Quan hệ',r=>esc(label(r.relation_type))],
      ['Trạng thái tài khoản',r=>{
        if(!r.user_id)return '<span class="badge">Chưa liên kết</span>';
        const u=users.find(x=>x.user_id===r.user_id);
        return u?badge(u.status):badge('active');
      }],
      ['',r=>button('Chi tiết','resident-detail','','link',`data-id="${r.resident_id}"`)+button('Xác nhận căn hộ','resident-apartments','building','link',`data-id="${r.resident_id}"`)]
    ]:[['Hợp đồng',r=>`<span class="primary-cell">#HD${esc(r.contract_id)}</span>`],['Căn hộ',r=>esc(apartmentCode(r.apartment_id))],['Cư dân',r=>esc(residents.find(p=>p.resident_id===r.resident_id)?.full_name||`#${r.resident_id}`)],['Hình thức',r=>esc(label(r.contract_type))],['Hiệu lực',r=>`${esc(date(r.start_date))}<span class="sub-cell">Đến ${esc(date(r.end_date))}</span>`],['Trạng thái',r=>badge(r.effective_status||r.status)],['',r=>button('Cập nhật','contract-edit','','link',`data-id="${r.contract_id}"`)]];
    return heading('Cư dân & hợp đồng','Hồ sơ cư dân, lịch sử sở hữu và thuê căn hộ.',button(tab==='residents'?'Thêm cư dân':'Tạo hợp đồng',tab==='residents'?'resident-create':'contract-create'))+tabs('residents',[['residents','Hồ sơ cư dân'],['contracts','Hợp đồng & lịch sử']])+`<section class="panel">${toolbar(tab==='residents'?'Tìm tên, số điện thoại…':'Tìm hợp đồng…')}${table(columns,tab==='residents'?residents:contracts)}</section>`;
  },
  async billing(){
    const tab=state.tab.billing||'monthly';
    const [apartments,summary,monthlyInvoices,semiannualInvoices,paymentConfig,residentProfile]=await Promise.all([items('/api/apartments'),api('/api/billing/summary'),items('/api/billing/invoices/monthly'),items('/api/billing/invoices/semiannual'),api('/api/billing/payment-config').catch(()=>null),resident()?api('/api/residents/me').catch(()=>null):null]);
    state.data.apartments=apartments;
    state.data.paymentConfig=paymentConfig;
    if(residentProfile)state.data.personal=residentProfile;
    const awaitingApartment=resident()&&Array.isArray(residentProfile?.apartment_ids)&&!residentProfile.apartment_ids.length;
    const apartmentNotice=awaitingApartment?`<div class="info-box" id="billing-apartment-notice">${residentProfile.registered_apartment_code?`Bạn đã đăng ký căn hộ ${esc(residentProfile.registered_apartment_code)}, nhưng căn hộ chưa được Ban quản lý xác nhận liên kết với tài khoản.`:'Tài khoản của bạn chưa được liên kết với căn hộ.'} Vui lòng liên hệ Ban quản lý để xác nhận thông tin cư trú và liên kết căn hộ. Hóa đơn sẽ hiển thị sau khi liên kết hợp lệ; số tiền chưa hiển thị không có nghĩa là đã thanh toán.</div>`:'';
    const allInvoices=[...monthlyInvoices.map(x=>({...x,invoice_type:'monthly'})),...semiannualInvoices.map(x=>({...x,invoice_type:'semiannual'}))];
    const curMonth=today().slice(0,7);
    const qNum=Math.floor(new Date().getMonth()/3)+1;
    const qMonths=[(qNum-1)*3+1,(qNum-1)*3+2,(qNum-1)*3+3].map(m=>`${thisYear()}-${String(m).padStart(2,'0')}`);
    const qSemi=`${thisYear()}-H${qNum<=2?'1':'2'}`;

    const monthInvoices=allInvoices.filter(i=>i.period===curMonth||(i.due_date&&i.due_date.startsWith(curMonth)));
    const monthPaid=monthInvoices.filter(i=>i.status==='paid');
    const monthUnpaid=monthInvoices.filter(i=>i.status!=='paid');
    const quarterInvoices=allInvoices.filter(i=>qMonths.includes(i.period)||(i.due_date&&qMonths.some(m=>i.due_date.startsWith(m)))||i.period===qSemi);

    let body;
    if(tab==='payments'){
      const payments=await items('/api/billing/payments');state.data.payments=payments;
      body=table([['Giao dịch',r=>`<span class="primary-cell">#TT${esc(r.payment_id)}</span><span class="sub-cell">${esc(r.transaction_code||'—')}</span>`],['Hóa đơn',r=>`${esc(label(r.invoice_type))} · ${esc(r.period)}`],['Căn hộ',r=>esc(apartmentCode(r.apartment_id))],['Số tiền',r=>`<span class="money">${money(r.amount)}</span>`],['Hình thức',r=>esc(String(r.transaction_code||'').startsWith('SEPAY-TEST-')?'Chuyển khoản · SePay Test':label(r.payment_method))],['Thời gian thanh toán',r=>esc(dateTime(r.paid_at))],['',r=>button('Tải biên nhận','receipt','download','link',`data-id="${r.payment_id}" data-kind="${esc(r.invoice_type)}"`)]],payments);
    }else if(tab==='bank-transactions'&&admin()){
      const transactions=await items('/api/billing/sepay/transactions');state.data.bankTransactions=transactions;
      const unresolved=transactions.filter(row=>Number(row.unallocated_amount)>0&&!row.resolution);
      body=`<div class="info-box" id="bank-issues-summary">${unresolved.length?`${number(unresolved.length)} khoản cần xử lý, tổng tiền chưa phân bổ ${money(unresolved.reduce((sum,row)=>sum+Number(row.unallocated_amount||0),0))}.`:'Chưa có khoản chuyển dư hoặc chưa xác định cần xử lý.'} Mỗi hóa đơn chỉ được ghi nhận đủ tiền một lần. Ghi chú xử lý không thực hiện chuyển tiền hay hoàn tiền.</div>`+table([['Tham chiếu',r=>`<span class="primary-cell">${esc(r.bank_reference||r.reference||`#${r.transaction_id}`)}</span><span class="sub-cell">${esc(date(r.received_at))}</span>`],['Hóa đơn',r=>r.invoice_id?`${esc(label(r.invoice_type))} #${esc(r.invoice_id)}`:'Chưa xác định'],['Tiền nhận',r=>money(r.amount)],['Đã phân bổ',r=>money(r.allocated_amount)],['Còn cần xử lý',r=>money(r.unallocated_amount)],['Đối soát',r=>`${badge(r.status)}${r.issue?`<span class="sub-cell">${esc(r.issue)}</span>`:''}`],['Xử lý của BQL',r=>`${r.resolution?`<span class="primary-cell">${esc(label(r.resolution))}</span><span class="sub-cell">${esc(r.resolution_note||'')}</span>`:''}${r.status!=='matched'?button(r.resolution?'Cập nhật ghi chú':'Ghi nhận xử lý','bank-transaction-resolve','edit','link',`data-id="${r.transaction_id}"`):''}`]],transactions);
    }else{
      const rows=(tab==='monthly'?monthlyInvoices:semiannualInvoices).map(r=>({...r,invoice_type:tab}));state.data.invoices=rows;
      body=table(invoiceColumns(),rows,awaitingApartment?{emptyTitle:'Chưa thể xem hóa đơn',emptyDescription:'Ban quản lý cần xác nhận căn hộ của bạn trước khi bạn có thể xem và thanh toán hóa đơn.'}:{});
    }
    const statCards=stat('Tổng hóa đơn (trong quý)',number(quarterInvoices.length),`Kỳ thu Quý ${qNum}/${thisYear()}`,'invoice')+stat('Đã thanh toán (trong tháng)',money(monthPaid.reduce((s,i)=>s+Number(i.total_amount||0),0)),`${number(monthPaid.length)} hóa đơn trong tháng`,'wallet','blue')+stat('Chờ thanh toán (trong tháng)',money(monthUnpaid.reduce((s,i)=>s+Number(i.total_amount||0),0)),`${number(monthUnpaid.length)} hóa đơn trong tháng`,'clock','orange')+stat('Hóa đơn quá hạn',number(summary.overdue_count),money(summary.overdue_amount),'invoice','purple');
    const paymentNotice=admin()?'<div class="info-box">Cư dân thanh toán trong tài khoản của mình. Ban quản lý lập hóa đơn, theo dõi trạng thái và chỉ ghi nhận thu khi đã nhận đủ tiền mặt hoặc chuyển khoản. Các khoản chuyển dư hoặc chuyển lặp được theo dõi tại mục Đối soát chuyển khoản.</div>':`<div class="info-box" id="payment-mode-notice">${esc(!paymentConfig?.ready?(paymentConfig?.message||'VietQR chưa sẵn sàng. Ban quản lý cần kết nối tài khoản SePay và ngân hàng nhận tiền.'):paymentConfig.environment==='test'?'VietQR · SePay Test: kiểm thử bằng giao dịch thử trên SePay. Không quét mã bằng ứng dụng ngân hàng để chuyển tiền thật.':'VietQR · Chuyển khoản bằng ứng dụng ngân hàng. Đây là giao dịch tiền thật; mỗi hóa đơn chỉ cần một thành viên thanh toán.')}</div>`;
    return heading(billingTitle(),admin()?'Lập hóa đơn, theo dõi công nợ và kết quả thanh toán của cư dân.':'Minh bạch các khoản phí. Thuận tiện trong từng thanh toán.',admin()&&['monthly','semiannual'].includes(tab)?button('Lập hóa đơn','invoice-create'):'')+apartmentNotice+(awaitingApartment?'':`<div class="stats-grid grid grid-cols-2 gap-3 min-[1280px]:grid-cols-4 min-[1280px]:gap-5">${statCards}</div>`)+paymentNotice+tabs('billing',[['monthly','Điện & nước hàng tháng'],['semiannual','Dịch vụ 6 tháng'],['payments',admin()?'Các khoản đã thu':'Lịch sử thanh toán'],...(admin()?[['bank-transactions','Đối soát chuyển khoản']]:[])])+`<section class="panel">${toolbar(tab==='bank-transactions'?'Tìm tham chiếu, hóa đơn…':'Tìm hóa đơn, kỳ thu…',['payments','bank-transactions'].includes(tab)?[]:['unpaid','overdue','paid'])}${body}</section>`;
  },
  async parking(){
    const tab=state.tab.parking||(tech()?'guest':'vehicles');
    const [vehicles,apartments]=await Promise.all([tab==='guest'?Promise.resolve([]):items('/api/parking/vehicles'),tab==='guest'?Promise.resolve([]):items('/api/apartments')]);Object.assign(state.data,{vehicles,apartments});
    let body;
    if(tab==='guest'){
      const rows=await items('/api/parking/guest-daily');state.data.guests=rows;
      body=table([['Ngày ghi nhận',r=>`<span class="primary-cell">${esc(date(r.parking_date))}</span>`],['Tổng tiền vé vãng lai',r=>`<span class="money">${money(r.daily_revenue)}</span>`],['Mã ghi nhận',r=>`#${esc(r.record_id)}`],['',r=>button('Cập nhật','guest-edit','','link',`data-id="${r.record_id}"`)]],rows);
    }else if(tab==='summary'){
      const grouped=Object.values(vehicles.filter(v=>v.status==='active').reduce((all,v)=>{all[v.apartment_id]??={apartment_id:v.apartment_id,count:0,fee:0};all[v.apartment_id].count++;all[v.apartment_id].fee+=Number(v.monthly_fee);return all;},{}));
      body=table([['Căn hộ',r=>`<span class="primary-cell">${esc(apartmentCode(r.apartment_id))}</span>`],['Số phương tiện',r=>number(r.count)],['Phí hàng tháng',r=>`<span class="money">${money(r.fee)}</span>`],['Phí 6 tháng đủ kỳ (chưa gồm phí thẻ)',r=>money(r.fee*6)]],grouped);
    }else{
      body=table([['Biển số',r=>`<span class="primary-cell">${esc(r.plate_number)}</span>`],['Căn hộ',r=>esc(apartmentCode(r.apartment_id))],['Loại xe',r=>esc(label(r.vehicle_type))],['Phí / tháng',r=>`<span class="money">${money(r.monthly_fee)}</span>`],['Ngày đăng ký',r=>esc(date(r.registered_date))],['Trạng thái',r=>badge(r.status)],...(admin()?[['',r=>button('Cập nhật','vehicle-edit','','link',`data-id="${r.vehicle_id}"`)]]:[])],vehicles);
    }
    return heading('Quản lý gửi xe','',tab==='guest'?button('Ghi nhận doanh thu','guest-create'):admin()?button('Đăng ký phương tiện','vehicle-create'):resident()?button('Gửi đơn đăng ký','parking-request'):'')+(tech()?'':tabs('parking',[['vehicles','Phương tiện đăng ký'],['summary','Thống kê theo căn hộ'],...(admin()?[['guest','Vé vãng lai']]:[])]))+`<section class="panel">${toolbar(tab==='guest'?'Tìm theo ngày…':'Tìm biển số, căn hộ…')}${body}</section>`;
  },
  async maintenance(){
    const tickets=await items('/api/maintenance/tickets');state.data.tickets=tickets;
    return heading('Sửa chữa & bảo trì','Tiếp nhận yêu cầu, theo dõi tiến độ và chăm sóc vận hành.',!tech()?button('Tạo yêu cầu','ticket-create'):'')+`<div class="stats-grid maintenance-stats">${stat('Chờ xử lý',number(tickets.filter(t=>t.status==='pending').length),'Yêu cầu mới tiếp nhận','clock','orange')}${stat('Đang thực hiện',number(tickets.filter(t=>t.status==='in_progress').length),'Kỹ thuật đang xử lý','wrench','blue')}${stat('Đã hoàn thành',number(tickets.filter(t=>t.status==='completed').length),'Các phiếu đã đóng','check')}</div><section class="panel">${toolbar('Tìm nội dung, mã phiếu…',['pending','in_progress','completed'])}${table([['Yêu cầu',r=>`<span class="primary-cell">#${esc(r.ticket_id)} · ${esc(label(r.type))}</span><span class="sub-cell">${esc(r.description?.slice(0,75))}</span>`],['Căn hộ',r=>esc(r.apartment_code||`#${r.apartment_id}`)],['Phụ trách',r=>esc(r.technician_name||'Chưa phân công')],['Ưu tiên',r=>badge(r.priority)],['Trạng thái',r=>badge(r.status)],['Ngày tạo',r=>esc(date(r.created_at))],['',r=>button(tech()||admin()?'Cập nhật':'Chi tiết','ticket-edit','','link',`data-id="${r.ticket_id}"`)]],tickets)}</section>`;
  },
  async notifications(){
    const notices=await items('/api/notifications');state.data.notices=notices;
    const filter=state.noticeFilter||'all';
    const displayed=filter==='all'?notices:notices.filter(n=>n.type===filter);
    const filterTabs=`<div class="tabs" role="tablist" style="margin-bottom:20px"><button class="tab ${filter==='all'?'active':''}" data-action="notice-filter" data-filter="all">Tất cả (${notices.length})</button><button class="tab ${filter==='general'?'active':''}" data-action="notice-filter" data-filter="general">Thông báo chung (${notices.filter(n=>n.type==='general').length})</button><button class="tab ${filter==='private'?'active':''}" data-action="notice-filter" data-filter="private">Thông báo riêng (${notices.filter(n=>n.type==='private').length})</button></div>`;
    const cards=displayed.map(n=>`<article class="panel notice-card clickable ${n.is_read?'read-mark':''}" data-action="notice-detail" data-id="${n.notification_id}"><div class="notification-tag"><span class="badge ${n.type==='private'?'purple':'green'}">${esc(label(n.type))}</span>${!n.is_read?'<span class="live-dot" title="Chưa đọc" style="background:var(--red)"></span>':''}</div><h3 style="margin:14px 0 10px">${esc(n.title)}</h3><footer><span>${esc(dateTime(n.created_at))}${n.related_apartment_id?` · Căn hộ ${esc(n.related_apartment_code)}`:n.target_apartment_id?` · ${esc(apartmentCode(n.target_apartment_id))}`:''}</span>${!n.is_read?'<span style="color:var(--red);font-weight:600;font-size:10px">Chưa đọc</span>':'<span class="muted" style="font-size:10px">Đã đọc</span>'}</footer></article>`).join('');
    return heading('Bảng tin cộng đồng','',!resident()?button('Soạn thông báo','notice-create'):'')+pageSpotlight('notifications')+`<div class="notification-action">${AnCuPush.active()?button('Tắt thông báo trình duyệt','push-disable','bell','secondary'):button('Bật thông báo trình duyệt','push-enable','bell','secondary')}</div>${filterTabs}${displayed.length?`<div class="card-list">${cards}</div>`:`<section class="panel">${empty('Chưa có thông báo','Không tìm thấy thông báo trong mục này.')}</section>`}`;
  },
  async complaints(){
    const rows=await items('/api/complaints');state.data.complaints=rows;
    return heading('Khiếu nại & đăng ký','Lắng nghe ý kiến. Đồng hành cùng cư dân.',button('Gửi yêu cầu','complaint-create'))+`<section class="panel">${toolbar('Tìm nội dung, danh mục…',['pending','processing','resolved','rejected'])}${table([['Mã yêu cầu',r=>`<span class="primary-cell">#YC${esc(r.complaint_id)}</span><span class="sub-cell">${esc(label(r.type))}</span>`],['Nội dung',r=>`<span class="primary-cell">${esc(r.category)}</span><span class="sub-cell">${esc(r.content?.slice(0,75))}</span>`],['Ngày tạo',r=>esc(date(r.created_at))],['Trạng thái',r=>badge(r.status)],['Phản hồi của Ban quản lý',r=>esc(r.response?.slice(0,60)||'Chưa có phản hồi')],['',r=>button(admin()?(r.response?'Sửa phản hồi':'Phản hồi'):'Chi tiết','complaint-edit','','link',`data-id="${r.complaint_id}"`)]],rows)}</section>`;
  },
  async reports(){
    const seq=state.sequence,year=state.reportYear||thisYear(),group=state.reportGroup||'month';
    const report=await api(`/api/billing/reports?year=${year}&group=${group}`);
    if(seq===state.sequence)state.data.report={...report,year};
    const total=report.totals||{};
    return heading('Báo cáo & thống kê','Dữ liệu thu phí giúp bạn đưa ra quyết định rõ ràng.',button('Xuất CSV','report-export','download','secondary'))+`<div class="stats-grid maintenance-stats">${stat('Tổng phát hành',money(total.billed_amount),`${number(total.invoice_count)} hóa đơn`,'invoice','blue')}${stat('Tổng đã thu',money(total.collected_amount),`${number(total.paid_count)} hóa đơn đã thanh toán`,'wallet')}${stat('Công nợ còn lại',money(total.outstanding_amount),'Trong năm được chọn','clock','orange')}</div><section class="panel"><div class="toolbar"><h2>Doanh thu theo kỳ</h2><div class="filter-group"><select id="report-year" aria-label="Chọn năm">${Array.from({length:8},(_,i)=>thisYear()-i).map(y=>`<option value="${y}" ${y===Number(year)?'selected':''}>Năm ${y}</option>`).join('')}</select><select id="report-group" aria-label="Nhóm báo cáo"><option value="month" ${group==='month'?'selected':''}>Theo tháng</option><option value="quarter" ${group==='quarter'?'selected':''}>Theo quý</option></select></div></div><div class="chart-wrap report-chart">${revenueChart(report.items||[],280)}</div>${table([['Kỳ báo cáo',r=>`<span class="primary-cell">${esc(r.period)}</span>`],['Đã phát hành',r=>money(r.billed_amount)],['Đã thu',r=>`<span class="money">${money(r.collected_amount)}</span>`],['Còn phải thu',r=>money(r.outstanding_amount)],['Hóa đơn đã thanh toán',r=>`${number(r.paid_count)} / ${number(r.invoice_count)}`]],report.items||[])}</section>`;
  },
  async users(){
    const tab=state.tab.users||'users';const [users,technicians]=await Promise.all([items('/api/auth/users'),items('/api/maintenance/technicians')]);Object.assign(state.data,{users,technicians});
    return heading('Nhân sự & tài khoản','Phân quyền truy cập và quản lý đội ngũ kỹ thuật.',button(tab==='users'?'Tạo tài khoản':'Thêm kỹ thuật viên',tab==='users'?'user-create':'technician-create'))+tabs('users',[['users','Tài khoản hệ thống'],['technicians','Nhân sự kỹ thuật']])+`<section class="panel">${toolbar('Tìm tên, tài khoản…')}${tab==='users'?table([['Tài khoản',r=>`<span class="primary-cell">${esc(r.username)}</span><span class="sub-cell">#${r.user_id}</span>`],['Vai trò',r=>`<span class="badge ${r.role==='admin'?'purple':r.role==='technician'?'blue':'green'}">${esc(roleNames[r.role]||r.role)}</span>`],['Email',r=>esc(r.email||'—')],['Trạng thái',r=>badge(r.status)],['Ngày tạo',r=>esc(date(r.created_at))],['',r=>button('Cập nhật','user-edit','','link',`data-id="${r.user_id}"`)]],users):table([['Kỹ thuật viên',r=>`<span class="primary-cell">${esc(r.full_name)}</span><span class="sub-cell">#${r.technician_id}</span>`],['Chuyên môn',r=>esc(r.specialty==='general'?'Kỹ thuật tổng hợp':label(r.specialty))],['Tài khoản',r=>esc(users.find(u=>u.user_id===r.user_id)?.username||`#${r.user_id}`)],['Công việc đang mở',r=>number(r.open_tickets)],['',r=>button('Cập nhật','technician-edit','','link',`data-id="${r.technician_id}"`)]],technicians)}</section>`;
  },
  async chatbot(){
    const tab=state.tab.chatbot||'chat';
    const top=heading('Trợ lý cư dân','Tra cứu thông tin từ kho kiến thức chính thức của chung cư.',admin()&&tab!=='chat'?button(tab==='faqs'?'Thêm câu hỏi':'Thêm tiện ích',tab==='faqs'?'faq-create':'location-create'):'')+tabs('chatbot',[['chat','Trò chuyện'],['faqs','Chính sách & câu hỏi'],['locations','Vị trí tiện ích']]);
    if(tab==='faqs'){
      const faqs=await items('/api/chatbot/faqs');state.data.faqs=faqs;
      return top+(faqs.length?`<div class="grid-two">${faqs.map(f=>`<article class="panel notice-card"><span class="inline-meta">${icon('message')}${esc(f.category||'Thông tin chung')}</span><h3>${esc(f.question)}</h3><p>${esc(f.answer)}</p>${admin()?`<footer>${button('Chỉnh sửa','faq-edit','edit','link',`data-id="${f.faq_id}"`)}</footer>`:''}</article>`).join('')}</div>`:`<section class="panel">${empty('Chưa có nội dung chính sách','Ban quản lý sẽ cập nhật kho kiến thức tại đây.')}</section>`);
    }
    if(tab==='locations'){
      const locations=await items('/api/chatbot/locations');state.data.locations=locations;
      return top+(locations.length?`<div class="card-list">${locations.map(l=>`<article class="panel notice-card"><div class="notice-symbol">${icon('location')}</div><h3>${esc(l.name)}</h3><div class="inline-meta">Tòa ${esc(l.block||'—')} · Tầng ${esc(l.floor||'—')}</div><p style="margin-top:12px">${esc(l.description)}</p>${admin()?`<footer>${button('Chỉnh sửa','location-edit','edit','link',`data-id="${l.location_id}"`)}</footer>`:''}</article>`).join('')}</div>`:`<section class="panel">${empty('Chưa có thông tin tiện ích','Vị trí và chỉ dẫn tiện ích sẽ được cập nhật tại đây.')}</section>`);
    }
    if(!state.chat.length)state.chat.push({role:'bot',text:'Xin chào! Tôi là trợ lý An Cư. Tôi có thể giúp bạn tra cứu chính sách, nội quy và vị trí tiện ích của chung cư. Bạn cần tìm thông tin gì?'});
    return top+`<section class="panel chat-container"><div class="panel-header"><div class="apartment-pill"><span>${icon('bot')}</span><div><h2>Trợ lý An Cư</h2><p>Giải đáp chính sách & tiện ích</p></div></div><span class="badge green">Sẵn sàng hỗ trợ</span></div><div id="chat-messages" class="chat-window" role="log" aria-live="polite">${state.chat.map(chatMessage).join('')}</div><div class="chat-suggestions">${['Phí quản lý được tính như thế nào?','Đăng ký gửi xe','Phòng camera ở đâu?','Giờ yên tĩnh'].map(q=>`<button data-action="chat-suggest" data-question="${esc(q)}">${esc(q)}</button>`).join('')}</div><form id="chat-form" class="chat-compose"><input name="question" aria-label="Câu hỏi cho trợ lý" placeholder="Nhập điều bạn muốn hỏi…" required maxlength="1500" autocomplete="off"><button class="button primary" type="submit" aria-label="Gửi câu hỏi">${icon('send')} Gửi</button></form></section>`;
  },
};
function quick(text,route,glyph){return `<button class="quick-action" data-action="navigate" data-route="${route}">${icon(glyph)}${text}</button>`;}
function noticePanel(notices){return `<section class="panel"><div class="panel-header"><h2>Thông báo mới</h2>${button('Tất cả','navigate','arrow','link','data-route="notifications"')}</div><div class="notice-list">${notices.length?notices.slice(0,3).map(n=>`<article class="notice-item"><div class="notice-symbol">${icon(n.type==='private'?'message':'bell')}</div><div><h3>${esc(n.title)}</h3><p>${esc(n.content)}</p><div class="notice-date">${esc(date(n.created_at))} · ${esc(label(n.type))}</div></div></article>`).join(''):empty('Chưa có thông báo','Thông tin mới sẽ được cập nhật tại đây.')}</div></section>`;}
function chatMessage(message){return `<div class="chat-message ${message.role==='user'?'user':'bot'}">${esc(message.text)}${message.source?`<small>Nguồn: ${esc(message.source)}</small>`:''}</div>`;}

Object.assign(statusLabels,{ownership:'Sở hữu',rental:'Thuê',locked:'Đã khóa'});

async function apartmentForm(id){
  const row=id?state.data.apartments.find(r=>r.apartment_id===Number(id)):{};
  formModal(id?'Cập nhật căn hộ':'Thêm căn hộ',field('code','Mã căn hộ','text',row.code||'','required maxlength="30" placeholder="Ví dụ: A-1201"')+field('block','Tòa nhà','text',row.block||'','required maxlength="30"')+field('floor','Tầng','number',row.floor??'','required min="0" max="200" step="1"')+field('area','Diện tích (m²)','number',row.area??'','required min="1" max="10000" step="0.01"'),data=>saved(id?patch(`/api/apartments/${id}`,data):post('/api/apartments',data)));
}
async function apartmentDetail(id){
  const [row,allContracts]=await Promise.all([api(`/api/apartments/${id}`),items('/api/contracts')]);
  const contracts=allContracts.filter(c=>Number(c.apartment_id)===Number(id));
  const body=detail([['Căn hộ',row.code],['Vị trí',`Tòa ${row.block} · Tầng ${row.floor}`],['Diện tích',row.area==null?'Chưa cập nhật':`${row.area} m²`],['Trạng thái',label(row.status)],['Cư dân hiện tại',row.current_resident||'Chưa có'],['Hình thức',label(row.contract_type)],['Bắt đầu',date(row.start_date)],['Kết thúc',date(row.end_date)],['Thời gian còn lại',row.remaining_days!=null?`${number(row.remaining_days)} ngày`:'Không xác định']]);
  openModal(`Căn hộ ${row.code}`,`<div class="modal-body">${body}<hr class="detail-separator"><h3 class="detail-title">Lịch sử sở hữu / thuê</h3>${table([['Cư dân',r=>esc(r.full_name||`#${r.resident_id}`)],['Loại',r=>esc(label(r.contract_type))],['Thời hạn',r=>`${esc(date(r.start_date))} → ${esc(date(r.end_date))}`],['Trạng thái',r=>badge(r.effective_status||r.status)]],contracts,{count:false,emptyTitle:'Chưa có hợp đồng'})}</div>`,`<div class="modal-footer">${button('Đóng','close-modal','','secondary')}</div>`);
}
async function residentForm(id){
  const [users,residents]=await Promise.all([items('/api/auth/users'),items('/api/residents')]);
  const row=id?residents.find(r=>r.resident_id===Number(id)):{};
  const eligible=users.filter(u=>['resident','technician','admin'].includes(u.role)&&(!residents.some(r=>r.user_id===u.user_id)||row.user_id===u.user_id));
  formModal(id?'Cập nhật hồ sơ cư dân':'Thêm cư dân',
    field('full_name','Họ và tên','text',row.full_name||'','required maxlength="120"')+
    field('registered_apartment_code','Căn hộ đăng ký','text',row.registered_apartment_code||'','maxlength="30" placeholder="Ví dụ: A-1201"')+
    field('phone','Số điện thoại','tel',row.phone||'','maxlength="20"')+
    field('id_card','CCCD / giấy tờ định danh','text',row.id_card||'','maxlength="30"')+
    select('relation_type','Quan hệ',[['owner','Chủ sở hữu'],['tenant','Người thuê']],row.relation_type||'tenant')+
    select('user_id','Liên kết tài khoản',eligible.map(u=>[u.user_id,`${u.username} (${roleNames[u.role]||u.role})`]),row.user_id||'',false),
    data=>{
      if(id&&!data.user_id)data.user_id=null;
      if('registered_apartment_code' in data&&!data.registered_apartment_code)data.registered_apartment_code=null;
      return saved(id?patch(`/api/residents/${id}`,data):post('/api/residents',data));
    },
    'Lưu hồ sơ',
    'Liên kết đúng tài khoản với hồ sơ cư dân. Sau đó xác nhận căn hộ hoặc lập hợp đồng để cư dân xem hóa đơn và sử dụng tiện ích của căn hộ.'
  );
}
async function residentDetail(id){
  const row=await api(`/api/residents/${id}`);
  openModal(row.full_name,`<div class="modal-body">${detail([['Mã cư dân',`#${row.resident_id}`],['Tài khoản',row.user_id?`#${row.user_id}`:'Chưa liên kết'],['Họ và tên',row.full_name],['Số điện thoại',row.phone],['CCCD / giấy tờ',row.id_card],['Quan hệ',label(row.relation_type)],['Căn hộ đăng ký',row.registered_apartment_code||'Chưa đăng ký'],['Căn hộ đã xác nhận',row.apartment_codes?.join(', ')||(row.apartment_ids||[]).map(apartmentCode).join(', ')||'Chưa xác nhận căn hộ']])}</div>`,`<div class="modal-footer">${button('Đóng','close-modal','','secondary')}${button('Xác nhận căn hộ','resident-apartments','building','secondary',`data-id="${id}"`)}${button('Cập nhật','resident-edit','edit','primary',`data-id="${id}"`)}</div>`);
}
async function residentApartments(id){
  if(!admin())throw new Error('Chỉ Ban quản lý được xác nhận căn hộ cho cư dân.');
  const [row,apartments]=await Promise.all([api(`/api/residents/${id}`),items('/api/apartments')]);
  const registered=String(row.registered_apartment_code||'').trim().toUpperCase();
  const selected=apartments.find(a=>String(a.code).toUpperCase()===registered)?.apartment_id||'';
  const confirmed=Array.isArray(row.verified_apartments)?row.verified_apartments:[];
  const contracts=(row.contract_apartment_ids||[]).map(aid=>apartments.find(a=>Number(a.apartment_id)===Number(aid))?.code||`#${aid}`);
  const confirmedList=table([['Căn hộ',r=>esc(r.code||apartmentCode(r.apartment_id))],['Ngày xác nhận',r=>esc(date(r.confirmed_at))],['',r=>button('Gỡ xác nhận','resident-apartment-remove','','link',`data-id="${id}" data-apartment="${esc(r.apartment_id)}"`)]],confirmed,{count:false,emptyTitle:'Chưa có xác nhận riêng',emptyDescription:'Bạn có thể xác nhận cư dân đang ở cùng căn hộ mà không cần tạo thêm hợp đồng.'});
  formModal(`Xác nhận căn hộ · ${row.full_name}`,
    `<div class="field wide">${detail([['Cư dân',row.full_name],['Căn hộ đăng ký',row.registered_apartment_code||'Chưa đăng ký'],['Căn hộ theo hợp đồng đang hiệu lực',contracts.join(', ')||'Chưa có']])}</div>`+
    select('apartment_id','Căn hộ cần xác nhận',[['','Chọn căn hộ'],...apartmentOptions(apartments)],selected)+
    `<div class="field wide"><h3 class="detail-title">Các căn hộ được xác nhận riêng</h3>${confirmedList}<p class="muted" style="margin-top:12px">Gỡ xác nhận chỉ xóa liên kết được xác nhận riêng. Quyền truy cập từ hợp đồng đang hiệu lực vẫn được giữ.</p></div>`,
    data=>saved(post(`/api/residents/${id}/apartments`,data),'Đã xác nhận căn hộ. Cư dân có thể đăng nhập lại hoặc tải lại trang để xem hóa đơn.'),
    'Xác nhận căn hộ',
    'Chỉ xác nhận sau khi đã kiểm tra thông tin cư trú. Cư dân sẽ được xem hóa đơn, nhận thông báo và sử dụng tiện ích của căn hộ; thao tác này không tạo hoặc thay đổi hợp đồng.',
    'vertical');
}
async function residentApartmentRemove(id,apartmentId){
  if(!admin())throw new Error('Chỉ Ban quản lý được gỡ xác nhận căn hộ cho cư dân.');
  const row=await api(`/api/residents/${id}`);
  const confirmed=row.verified_apartments?.find(a=>Number(a.apartment_id)===Number(apartmentId));
  if(!confirmed)throw new Error('Không tìm thấy liên kết căn hộ được xác nhận riêng.');
  formModal('Gỡ xác nhận căn hộ',`<div class="field wide">${detail([['Cư dân',row.full_name],['Căn hộ',confirmed.code||apartmentCode(apartmentId)]])}</div>`,
    ()=>saved(api(`/api/residents/${id}/apartments/${encodeURIComponent(apartmentId)}`,{method:'DELETE'}),'Đã gỡ xác nhận căn hộ.'),
    'Gỡ xác nhận',
    'Cư dân sẽ không còn quyền truy cập từ liên kết này. Hợp đồng không bị thay đổi; nếu cư dân vẫn có hợp đồng đang hiệu lực với căn hộ, quyền truy cập theo hợp đồng vẫn còn.');
}
async function contractForm(id){
  const [apartments,residents]=await Promise.all([items('/api/apartments'),items('/api/residents')]);
  const row=id?state.data.contracts.find(c=>c.contract_id===Number(id)):{};
  const currentResident=row.resident_id?residents.find(r=>r.resident_id===row.resident_id)?.full_name||'':'';
  const residentField=`<div class="field"><label for="field-resident_name">Cư dân <span class="req-star">*</span></label><input id="field-resident_name" name="resident_name" list="resident-datalist" value="${esc(currentResident)}" required placeholder="Nhập tên cư dân" autocomplete="off"><datalist id="resident-datalist">${residents.map(r=>`<option value="${esc(r.full_name)}">`).join('')}</datalist></div>`;
  const statusField=id?select('status','Trạng thái',[['active','Đang hoạt động'],['expired','Hết hạn']],row.status==='expired'?'expired':'active'):'';

  formModal(id?'Cập nhật hợp đồng':'Tạo hợp đồng',
    select('apartment_id','Căn hộ',apartmentOptions(apartments),row.apartment_id||'')+
    residentField+
    select('contract_type','Loại hợp đồng',[['rental','Thuê căn hộ'],['ownership','Sở hữu căn hộ']],row.contract_type||'rental')+
    field('start_date','Ngày bắt đầu','date',row.start_date||today(),'required')+
    field('end_date','Ngày kết thúc','date',row.end_date||'')+
    statusField,
    data=>{
      if(data.contract_type==='rental'&&!data.end_date)throw new Error('Vui lòng nhập ngày kết thúc hợp đồng thuê.');
      if(data.end_date&&data.end_date<data.start_date)throw new Error('Ngày kết thúc không được trước ngày bắt đầu.');
      if(!data.end_date)data.end_date=null;
      const matchedRes=residents.find(r=>r.full_name.trim().toLowerCase()===data.resident_name.trim().toLowerCase());
      if(matchedRes){
        data.resident_id=matchedRes.resident_id;
      }
      return saved(id?patch(`/api/contracts/${id}`,data):post('/api/contracts',data));
    },
    'Lưu hợp đồng',
    'Một căn hộ chỉ có một hợp đồng hoạt động trong cùng khoảng thời gian. Hợp đồng thuê cần có ngày kết thúc.'
  );
}
function utilityFields(row={}){
  return field('electricity_usage','Điện tiêu thụ (kWh)','number',row.electricity_usage??'','required min="0" max="1000000" step="0.001"')+
    field('electricity_unit_price','Đơn giá điện (VNĐ/kWh)','number',row.electricity_unit_price??'','required min="1" max="1000000000" step="1"')+
    field('water_usage','Nước tiêu thụ (m³)','number',row.water_usage??'','required min="0" max="1000000" step="0.001"')+
    field('water_unit_price','Đơn giá nước (VNĐ/m³)','number',row.water_unit_price??'','required min="1" max="1000000000" step="1"')+
    '<div class="wide info-box" id="utility-preview" role="status" aria-live="polite"></div>';
}
function updateUtilityPreview(){
  const preview=$('#utility-preview'),form=$('#modal-form');if(!preview||!form)return;
  const amounts={};
  for(const utility of ['electricity','water']){
    const usage=form.elements.namedItem(utility+'_usage'),price=form.elements.namedItem(utility+'_unit_price');
    if(!usage.value||!price.value||!usage.checkValidity()||!price.checkValidity()){
      preview.textContent='Nhập lượng tiêu thụ và đơn giá để xem tiền điện, tiền nước và tổng hóa đơn.';return;
    }
    // Integer thousandths avoid 0.145 × 100 being rounded down by float error.
    const product=Math.round(Number(usage.value)*1000)*Number(price.value);
    if(product/1000>1000000000){preview.textContent='Tiền mỗi khoản không được vượt quá 1 tỷ đồng.';return;}
    amounts[utility]=Math.floor((product+500)/1000);
  }
  preview.innerHTML=`${detail([['Tiền điện',money(amounts.electricity)],['Tiền nước',money(amounts.water)],['Tổng hóa đơn',money(amounts.electricity+amounts.water)]])}<p>Mỗi khoản được làm tròn đến đồng.</p>`;
}
async function invoiceForm(){
  const kind=state.tab.billing||'monthly',apartments=state.data.apartments||await items('/api/apartments');
  const period=kind==='monthly'?today().slice(0,7):`${thisYear()}-H${new Date().getMonth()<6?'1':'2'}`;
  const nextDate=new Date();nextDate.setDate(nextDate.getDate()+14);const due=nextDate.toLocaleDateString('en-CA');
  formModal(kind==='monthly'?'Lập hóa đơn điện & nước':'Lập hóa đơn dịch vụ 6 tháng',select('apartment_id','Căn hộ',apartmentOptions(apartments))+field('period','Kỳ thu',kind==='monthly'?'month':'text',period,kind==='monthly'?'required':'required pattern="[0-9]{4}-H[12]" placeholder="2026-H2"')+(kind==='monthly'?utilityFields():field('service_fee','Phí dịch vụ chung (VNĐ)','number','0','required min="0" step="1"')+field('parking_fee','Phí gửi xe (VNĐ, không bắt buộc)','number','','min="0" step="1" placeholder="Tự tính theo kỳ nếu để trống"'))+field('due_date','Hạn thanh toán','date',due,'required'),data=>saved(post(`/api/billing/invoices/${kind}`,data),'Đã phát hành hóa đơn.'),'Phát hành hóa đơn',kind==='semiannual'?'Nếu để trống phí gửi xe, hệ thống tính các tháng có đăng ký trong kỳ đã chọn và cộng phí làm thẻ lần đầu 100.000 VNĐ/xe trong kỳ có tháng đăng ký.':'Nhập lượng điện, nước đã dùng trong kỳ (chỉ số mới trừ chỉ số cũ) và đơn giá áp dụng. Thành tiền = lượng tiêu thụ × đơn giá.');
  updateUtilityPreview();
}
function findInvoice(kind,id){return state.data.invoices?.find(r=>r.invoice_type===kind&&Number(r.invoice_id)===Number(id));}
async function invoiceDetail(kind,id,updatedRow=null){
  const version=modalVersion,user=state.user;
  const row=updatedRow||await api(`/api/billing/invoices/${kind}/${id}`);
  if(modalVersion!==version||state.user!==user)return;
  if(!row)throw new Error('Không tìm thấy hóa đơn.');
  const paymentConfig=resident()?(state.data.paymentConfig||await api('/api/billing/payment-config').catch(()=>null)):null;
  if(modalVersion!==version||state.user!==user)return;
  row.invoice_type=kind;state.currentInvoice=row;
  if(resident())state.data.paymentConfig=paymentConfig;
  const entries=[['Mã hóa đơn',`#${kind==='monthly'?'HD':'DV'}${String(id).padStart(4,'0')}`],['Căn hộ',apartmentCode(row.apartment_id)],['Kỳ thu',row.period],['Trạng thái',label(row.status)],...(kind==='monthly'?[['Tiền điện',money(row.electricity_fee)],['Tiền nước',money(row.water_fee)]]:[['Phí dịch vụ',money(row.service_fee)],['Phí gửi xe',money(row.parking_fee)]]),['Hạn thanh toán',date(row.due_date)],['Tổng cần thanh toán',money(row.total_amount)],['Thời gian lập hóa đơn',dateTime(row.created_at)],['Thời gian thanh toán',row.paid_at?dateTime(row.paid_at):row.status==='paid'?'Chưa ghi nhận':'Chưa thanh toán']];
  if(kind==='monthly'&&row.electricity_usage!=null)entries.splice(6,0,
    ['Cách tính tiền điện',`${number(row.electricity_usage)} kWh × ${money(row.electricity_unit_price)}/kWh = ${money(row.electricity_fee)}`,true],
    ['Cách tính tiền nước',`${number(row.water_usage)} m³ × ${money(row.water_unit_price)}/m³ = ${money(row.water_fee)}`,true]);
  const unpaidActions=admin()?button('Ghi nhận thu','invoice-cash','wallet','secondary',`data-id="${id}" data-kind="${kind}"`):resident()?button('Thanh toán VietQR','invoice-pay','wallet','primary',`data-id="${id}" data-kind="${kind}" ${paymentConfig?.ready?'':'disabled title="Ban quản lý cần hoàn tất cấu hình SePay trước khi thanh toán."'}`):'';
  openModal('Chi tiết hóa đơn',`<div class="modal-body">${detail(entries)}${row.status==='overdue'?`<div class="info-box" style="margin-top:20px">${admin()?'Hóa đơn đã quá hạn. Vui lòng liên hệ cư dân để nhắc thanh toán.':'Hóa đơn đã quá hạn. Vui lòng thanh toán hoặc liên hệ Ban quản lý để được hỗ trợ.'}</div>`:''}${admin()&&row.status==='unpaid'?`<div style="margin-top:18px">${button('Điều chỉnh số tiền / hạn thanh toán','invoice-edit','edit','link',`data-id="${id}" data-kind="${kind}"`)}</div>`:''}</div>`,`<div class="modal-footer">${row.status!=='paid'?unpaidActions:button(admin()?'Xem khoản đã thu':'Lịch sử thanh toán','payment-history','download','primary')}${button('Đóng','close-modal','','secondary')}</div>`);
  $('#modal').dataset.invoiceKind=kind;$('#modal').dataset.invoiceId=id;
  $('#modal .modal-body').insertAdjacentHTML('beforeend','<p class="muted" style="margin-top:18px">Thời gian theo giờ Việt Nam (UTC+7).</p>');
}
function invoiceEdit(kind,id){
  const row=state.currentInvoice||findInvoice(kind,id);
  const monthlyFields=row.electricity_usage!=null?utilityFields(row):field('electricity_fee','Tiền điện (VNĐ)','number',row.electricity_fee,'required min="0" step="1"')+field('water_fee','Tiền nước (VNĐ)','number',row.water_fee,'required min="0" step="1"');
  formModal('Điều chỉnh hóa đơn',(kind==='monthly'?monthlyFields:field('service_fee','Phí dịch vụ (VNĐ)','number',row.service_fee,'required min="0" step="1"')+field('parking_fee','Phí gửi xe (VNĐ)','number',row.parking_fee,'required min="0" step="1"'))+field('due_date','Hạn thanh toán','date',row.due_date,'required'),data=>saved(patch(`/api/billing/invoices/${kind}/${id}`,data),'Đã điều chỉnh hóa đơn.'),'Lưu điều chỉnh');
  updateUtilityPreview();
}
async function checkout(kind,id){
  if(!resident())throw new Error('Thanh toán online dành cho tài khoản cư dân.');
  const order=await post(`/api/billing/invoices/${kind}/${id}/checkout`);
  showPayment(order);
}
const paymentStorageKey=()=>`ancu_vietqr_order_${state.user?.user_id}`;
const activePayment=order=>['pending','awaiting_confirmation'].includes(order.status);
const sessionExpired=order=>order.status==='pending'&&Number.isFinite(Date.parse(order.expires_at))&&Date.now()>=Date.parse(order.expires_at);
const transferAmount=order=>typeof order.remaining_amount==='number'?order.remaining_amount:order.amount;
function rememberPayment(order){
  if(order.mode==='sepay'&&activePayment(order))sessionStorage.setItem(paymentStorageKey(),order.order_id);
  else if(sessionStorage.getItem(paymentStorageKey())===order.order_id)sessionStorage.removeItem(paymentStorageKey());
}
async function resumePayment(){
  if(!resident())return;
  const orderId=sessionStorage.getItem(paymentStorageKey());
  if(!orderId||!/^VQR-[A-Za-z0-9_-]{1,100}$/.test(orderId))return;
  const userId=state.user.user_id;
  try{
    const order=await api(`/api/billing/orders/${encodeURIComponent(orderId)}`);
    if(state.user?.user_id!==userId)return;
    state.route='billing';state.tab.billing=order.invoice_type;
    history.replaceState(null,'','#billing');renderPage();
    showPayment(order);
  }catch(error){
    if(state.user?.user_id!==userId)return;
    if([403,404].includes(error.status))sessionStorage.removeItem(paymentStorageKey());
    toast(`Chưa kiểm tra được phiên chuyển khoản. ${error.message}`,true);
  }
}
function paymentFeedback(message,error=false){
  const box=$('#payment-feedback');if(!box)return;
  box.textContent=message;box.hidden=!message;box.className=error?'error-box':'info-box';
}
function paymentClock(watch){
  if(paymentWatch!==watch)return;
  const expired=sessionExpired(watch.order);
  if(expired!==watch.expired){updatePayment(watch.order);return;}
  const clock=$('#payment-expiry');if(!clock)return;
  const remaining=Math.max(0,Math.ceil((Date.parse(watch.order.expires_at)-Date.now())/1000));
  clock.textContent=expired?'Phiên trên web đã hết thời gian. Nếu đã chuyển khoản, hãy kiểm tra trạng thái; không chuyển lần nữa.':`Thời gian giữ phiên: ${Math.floor(remaining/60)} phút ${String(remaining%60).padStart(2,'0')} giây. Đây không phải hạn thanh toán hóa đơn.`;
}
function updatePayment(order){
  const watch=paymentWatch;
  if(!watch||watch.order.order_id!==order.order_id)return;
  const previous=watch.order.status;
  watch.order=order;watch.expired=sessionExpired(order);rememberPayment(order);
  const success=order.status==='success',pending=order.status==='pending',awaiting=order.status==='awaiting_confirmation';
  const owner=order.is_owner===true,canPay=owner&&order.can_pay===true&&pending&&!watch.expired;
  $('#payment-amount').textContent=money(success?order.amount:transferAmount(order));
  const title=success?'Đã xác nhận thanh toán':awaiting?'Chờ ngân hàng xác nhận':watch.expired||order.status==='expired'?'Phiên thanh toán đã hết thời gian':pending?(owner?'Đang chờ chuyển khoản':'Một thành viên khác đang thanh toán'):'Phiên thanh toán đã hủy';
  const explanation=success?'Hệ thống đã đối soát khoản nhận. Hóa đơn đã được cập nhật và có thể tải biên nhận.':awaiting?'Đã nhận thông tin báo chuyển khoản. Hóa đơn chỉ chuyển sang đã thanh toán khi hệ thống xác minh đủ tiền nhận. Vui lòng không chuyển thêm.':canPay?'Chỉ một thành viên thanh toán hóa đơn này. Kiểm tra đúng tài khoản, số tiền và giữ nguyên nội dung chuyển khoản.':activePayment(order)&&!owner?'Một thành viên trong căn hộ đang giữ phiên thanh toán. Vui lòng chờ kết quả, không chuyển khoản thêm.':'Nếu đã chuyển khoản, hãy kiểm tra trạng thái hoặc liên hệ Ban quản lý. QR đã lưu vẫn có thể được ngân hàng chấp nhận; không dùng lại mã cũ.';
  $('#payment-status').innerHTML=`${badge(order.status)}<h3 style="margin:12px 0 6px">${esc(title)}</h3><p>${esc(explanation)}</p>${order.message?`<p>${esc(order.message)}</p>`:''}${Number(order.paid_amount)>0&&!success?`<p>Tổng hóa đơn ${esc(money(order.amount))}; đã nhận ${esc(money(order.paid_amount))}; còn thiếu ${esc(money(order.remaining_amount))}. ${canPay?'Chỉ chuyển phần còn thiếu bằng QR mới bên dưới.':'Không chuyển thêm khi chưa có hướng dẫn đối soát.'}</p>`:''}`;
  if(success&&order.paid_at)$('#payment-status').insertAdjacentHTML('beforeend',`<p>Thời gian thanh toán: ${esc(dateTime(order.paid_at))} (giờ Việt Nam).</p>`);
  const options=$('#payment-options'),optionKey=canPay?JSON.stringify([order.order_id,order.qr_image_url,order.transfer_content,order.bank,transferAmount(order)]):'hidden';
  if(options&&watch.optionKey!==optionKey){
    watch.optionKey=optionKey;
    if(modalBlob){URL.revokeObjectURL(modalBlob);modalBlob=null;}
    options.hidden=!canPay;
    options.innerHTML=canPay?`${order.qr_image_url?'<img id="payment-qr" alt="Mã VietQR thanh toán hóa đơn" hidden>':''}<div style="text-align:left;margin-top:18px">${detail([['Ngân hàng',order.bank?.name||order.bank?.code],['Số tài khoản',order.bank?.account_number],['Chủ tài khoản',order.bank?.account_name],['Số tiền cần chuyển',money(transferAmount(order))],['Nội dung chuyển khoản',order.transfer_content]])}</div><p id="payment-expiry" class="muted" role="timer"></p><p class="muted">Hết phiên chỉ ẩn mã trên web, không thu hồi được QR đã lưu. Không chia sẻ QR cho người khác thanh toán cùng lúc.</p>`:'';
    if(canPay&&order.qr_image_url)loadPaymentQr(watch,optionKey);
  }
  $('#payment-actions').innerHTML=button('Đóng','close-modal','','secondary')+(success?
    (order.payment_id?button('Tải biên nhận','receipt','download','primary',`data-id="${esc(order.payment_id)}" data-kind="${esc(order.invoice_type)}"`):'')+button('Lịch sử thanh toán','payment-history','','secondary'):
    button('Kiểm tra trạng thái','payment-check','refresh','secondary')+
    (canPay?button('Tôi đã chuyển khoản','payment-confirm','check','primary')+(Number(order.paid_amount)>0?'':button('Hủy phiên','payment-cancel','','secondary')):'')+
    (['expired','cancelled'].includes(order.status)?button('Mở phiên mới','invoice-pay','wallet','primary',`data-id="${esc(order.invoice_id)}" data-kind="${esc(order.invoice_type)}"`):''));
  paymentClock(watch);
  if(!activePayment(order)){clearTimeout(watch.timer);clearInterval(watch.clock);watch.clock=null;}
  else if(!watch.clock)watch.clock=setInterval(()=>paymentClock(watch),1000);
  if(previous!==order.status&&success){renderPage();toast('Đã xác nhận thanh toán hóa đơn.');}
}
function queuePaymentPoll(watch){
  if(paymentWatch!==watch||!activePayment(watch.order))return;
  clearTimeout(watch.timer);
  watch.timer=setTimeout(async()=>{
    if(!document.hidden)await checkPayment(watch);
    queuePaymentPoll(watch);
  },4000);
}
async function checkPayment(watch,reconcile=false){
  if(!watch||paymentWatch!==watch||watch.busy)return;
  watch.busy=true;
  const controller=new AbortController();watch.controller=controller;
  const timeout=setTimeout(()=>controller.abort(),reconcile?45000:15000);
  const buttonEl=$('[data-action="payment-check"]');if(buttonEl)buttonEl.disabled=true;
  if(reconcile)paymentFeedback('Đang kiểm tra khoản tiền nhận…');
  try{
    const path=`/api/billing/orders/${encodeURIComponent(watch.order.order_id)}`;
    const order=await api(reconcile?path+'/reconcile':path,{...(reconcile?{method:'POST',body:{}}:{}),signal:controller.signal});
    if(paymentWatch!==watch)return;
    updatePayment(order);
    if(order.status==='success')paymentFeedback('');
    else if(reconcile)paymentFeedback(order.message||'Chưa xác nhận đủ tiền nhận. Nếu đã chuyển khoản, không chuyển thêm; vui lòng chờ hoặc liên hệ Ban quản lý.');
  }catch(error){
    if(paymentWatch===watch)paymentFeedback(`Chưa xác minh được kết quả. ${error.message}`,true);
  }finally{
    clearTimeout(timeout);watch.controller=null;watch.busy=false;
    if(paymentWatch===watch){const current=$('[data-action="payment-check"]');if(current)current.disabled=false;queuePaymentPoll(watch);}
  }
}
function showPayment(order){
  if(!resident()||order.mode!=='sepay')return;
  const testing=order.environment==='test';
  openModal(testing?'VietQR · SePay Test':'Thanh toán VietQR',`<div class="modal-body qr-area"><div class="notice-symbol" style="margin:auto">${icon('wallet')}</div><div class="amount" id="payment-amount">${money(transferAmount(order))}</div><p>Hóa đơn #${esc(order.invoice_id)} · ${esc(label(order.invoice_type))}</p><div class="info-box" style="margin-top:18px;text-align:left">${testing?'Môi trường SePay Test: dùng chức năng gửi giao dịch thử trên SePay để kiểm tra. Không quét mã bằng ứng dụng ngân hàng để chuyển tiền thật.':'Chuyển khoản ngân hàng sử dụng tiền thật. Mỗi hóa đơn chỉ cần một thành viên chuyển tiền một lần. Nếu đã chuyển, không mở giao dịch khác.'}</div><div id="payment-status" role="status" aria-live="polite"></div><div id="payment-options"></div><div id="payment-feedback" role="status" style="margin-top:18px" hidden></div><p class="muted" style="font-size:10px;margin-top:13px;overflow-wrap:anywhere">Mã phiên: ${esc(order.order_id)}</p></div>`,`<div class="modal-footer" id="payment-actions" style="flex-wrap:wrap"></div>`);
  const watch={order,timer:null,clock:null,busy:false};paymentWatch=watch;
  updatePayment(order);queuePaymentPoll(watch);
}
async function loadPaymentQr(watch,optionKey){
  try{
    const path=new URL(watch.order.qr_image_url,location.origin);
    if(path.origin!==location.origin||!path.pathname.startsWith('/api/billing/orders/'))throw new Error('Đường dẫn mã QR không hợp lệ.');
    const response=await fetch(path.href,{cache:'no-store',headers:{Authorization:`Bearer ${state.token}`}});
    if(!response.ok)throw new Error('Chưa tải được mã VietQR. Hãy kiểm tra trạng thái trước khi thử lại.');
    const blob=await response.blob();
    if(paymentWatch!==watch||watch.optionKey!==optionKey)return;
    modalBlob=URL.createObjectURL(blob);const image=$('#payment-qr');if(image){image.src=modalBlob;image.hidden=false;}
  }catch(error){if(paymentWatch===watch)paymentFeedback(error.message,true);}
}
async function confirmTransfer(){
  const watch=paymentWatch;
  if(!watch||watch.busy||!watch.order.is_owner||!watch.order.can_pay||sessionExpired(watch.order))return;
  watch.busy=true;
  try{
    const order=await post(`/api/billing/orders/${encodeURIComponent(watch.order.order_id)}/confirm-transfer`);
    if(paymentWatch===watch){updatePayment(order);paymentFeedback('Đã báo chuyển khoản. Đây chưa phải xác nhận đã thanh toán; hệ thống đang chờ đối soát tiền nhận.');}
  }finally{watch.busy=false;}
}
async function cancelPayment(){
  const watch=paymentWatch;
  if(!watch||watch.busy||!watch.order.is_owner||watch.order.status!=='pending'||Number(watch.order.paid_amount)>0)return;
  if(!window.confirm('Chỉ hủy khi bạn CHƯA chuyển khoản. Nếu đã chuyển, chọn Hủy bỏ và bấm “Tôi đã chuyển khoản” để chờ đối soát. Bạn chắc chắn chưa chuyển tiền?'))return;
  watch.busy=true;
  try{
    const order=await post(`/api/billing/orders/${encodeURIComponent(watch.order.order_id)}/cancel`);
    if(paymentWatch===watch)updatePayment(order);
  }finally{watch.busy=false;}
}
function resolveBankTransaction(id){
  if(!admin())throw new Error('Chỉ Ban quản lý được ghi nhận xử lý giao dịch.');
  const row=state.data.bankTransactions?.find(item=>Number(item.transaction_id)===Number(id));
  if(!row)throw new Error('Không tìm thấy giao dịch.');
  formModal('Ghi nhận xử lý chuyển khoản',select('resolution','Kết quả xử lý',[['reviewed','Đã kiểm tra'],['refunded','Đã hoàn trả thực tế'],['retained','Đã thống nhất giữ lại']],row.resolution||'reviewed')+field('note','Ghi chú xử lý','textarea',row.resolution_note||'','required maxlength="2000"'),data=>saved(post(`/api/billing/sepay/transactions/${encodeURIComponent(id)}/resolve`,data),'Đã lưu ghi chú xử lý.'),'Lưu ghi chú',`Khoản nhận ${money(row.amount)}, chưa phân bổ ${money(row.unallocated_amount)}. Thao tác này chỉ lưu sổ theo dõi, không chuyển tiền hoặc hoàn tiền. Chỉ chọn “Đã hoàn trả thực tế” sau khi đã hoàn tiền và kiểm tra chứng từ.`);
}
function cashPayment(kind,id){
  if(!admin())throw new Error('Chỉ Ban quản lý được ghi nhận khoản tiền đã nhận.');
  const row=state.currentInvoice||findInvoice(kind,id);
  formModal('Ghi nhận thanh toán đã nhận',select('payment_method','Hình thức thu',[['cash','Tiền mặt'],['bank_transfer','Chuyển khoản ngân hàng']])+field('transaction_code','Mã giao dịch / tham chiếu','text','','maxlength="100"'),data=>saved(post(`/api/billing/invoices/${kind}/${id}/pay`,data),'Đã ghi nhận thanh toán.'),'Xác nhận đã nhận tiền',`Chỉ xác nhận sau khi đã thực nhận đủ ${money(row?.total_amount)} cho hóa đơn #${id}.`);
}
async function receipt(kind,id){
  const response=await fetch(`/api/billing/payments/${kind}/${id}/receipt`,{headers:{Authorization:`Bearer ${state.token}`}});
  if(!response.ok){let data={};try{data=await response.json();}catch{}throw new Error(data.error||'Chưa tải được biên nhận.');}
  downloadBlob(await response.blob(),`bien-nhan-${kind}-${id}.html`);toast('Đã tải biên nhận điện tử.');
}
function downloadBlob(blob,name){const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function vehicleForm(id){
  const apartments=state.data.apartments||await items('/api/apartments'),row=id?state.data.vehicles.find(r=>r.vehicle_id===Number(id)):{};
  if(row.status==='cancelled'){
    openModal('Phương tiện đã hủy',`<div class="modal-body">${detail([['Biển số',row.plate_number],['Căn hộ',apartmentCode(row.apartment_id)],['Loại xe',label(row.vehicle_type)],['Trạng thái','Đã hủy']])}</div>`,`<div class="modal-footer">${button('Đóng','close-modal','','secondary')}</div>`);return;
  }
  formModal(id?'Cập nhật phương tiện':'Đăng ký phương tiện',
    select('apartment_id','Căn hộ',apartmentOptions(apartments),row.apartment_id||'')+
    select('vehicle_type','Loại phương tiện',parkingTypes,row.vehicle_type||'motorbike')+
    field('plate_number','Biển số xe','text',row.plate_number||'','maxlength="30" aria-describedby="parking-plate-help"')+
    '<p id="parking-plate-help" class="muted">Xe máy và xe điện phải có biển số. Xe điện chưa có biển phải làm biển nhận dạng theo căn hộ, ví dụ A101-XD01.</p>'+
    field('monthly_fee','Phí hàng tháng (VNĐ)','number',parkingFee(row.vehicle_type),'readonly required')+
    field('registered_date','Ngày đăng ký','date',row.registered_date||today(),`required ${id?'readonly':''}`)+
    field('registration_months','Thời gian cam kết (tháng, tối thiểu 2)','number',row.registration_months||2,`required min="${row.registration_months||2}" step="1"`)+
    (id?select('status','Trạng thái',enumOptions(['active','cancelled']),row.status):''),
    data=>{validateParking(data);return saved(id?patch(`/api/parking/vehicles/${id}`,data):post('/api/parking/vehicles',data));},
    'Lưu thông tin',`Thu phí 6 tháng một lần cùng tiền dịch vụ. Phí cấp thẻ lần đầu: 100.000 VNĐ/xe trong tháng đầu.${row.minimum_end_date?' Có thể hủy từ ngày '+date(row.minimum_end_date)+'.':''}`);
  updateParkingFields();
}
function guestForm(id){const row=id?state.data.guests.find(r=>r.record_id===Number(id)):{};formModal(id?'Cập nhật doanh thu vãng lai':'Ghi nhận doanh thu vé vãng lai',field('parking_date','Ngày ghi nhận','date',row.parking_date||today(),`required max="${today()}"`)+field('daily_revenue','Tổng doanh thu trong ngày (VNĐ)','number',row.daily_revenue??'','required min="0" step="1"'),data=>saved(id?api(`/api/parking/guest-daily/${id}`,{method:'PUT',body:data}):post('/api/parking/guest-daily',data),'Đã ghi nhận doanh thu vãng lai.'),'Lưu doanh thu','Nhập tổng số tiền thu từ khách vãng lai trong ngày. Mỗi ngày được ghi nhận một lần.');}
async function ticketForm(id){
  if(id){
    const row=state.data.tickets.find(r=>r.ticket_id===Number(id));
    const details=detail([['Yêu cầu',`#${id} · ${label(row.type)}`],['Căn hộ',row.apartment_code||`#${row.apartment_id}`],['Trạng thái',label(row.status)],['Ưu tiên',label(row.priority)],['Phụ trách',row.technician_name||'Chưa phân công'],['Ngày tạo',date(row.created_at)],['Nội dung',row.description,true]]);
    if(resident()||row.status==='completed'){
      openModal('Chi tiết yêu cầu',`<div class="modal-body">${details}${row.completed_at?`<p class="muted" style="font-size:11px;margin-top:18px">Hoàn thành: ${esc(date(row.completed_at))}</p>`:''}</div>`,`<div class="modal-footer">${button('Đóng','close-modal','','secondary')}</div>`);return;
    }
    const statuses=row.status==='pending'?['pending','in_progress']:['in_progress','completed'];
    let fields=select('status','Trạng thái xử lý',enumOptions(statuses),row.status);
    if(admin()){
      const technicians=await items('/api/maintenance/technicians');
      fields+=select('technician_id','Phân công kỹ thuật viên',technicians.map(t=>[t.technician_id,`${t.full_name} · ${t.specialty==='general'?'Kỹ thuật tổng hợp':label(t.specialty)}`]),row.technician_id||'',true)+select('priority','Ưu tiên',enumOptions(['low','medium','high']),row.priority)+field('description','Nội dung','textarea',row.description,'required maxlength="10000"');
    }
    formModal(`Cập nhật yêu cầu #${id}`,fields,data=>saved(patch(`/api/maintenance/tickets/${id}`,data),'Đã cập nhật tiến độ.'),'Lưu tiến độ',tech()?row.description:'Chọn kỹ thuật viên trước khi bắt đầu xử lý. Đóng phiếu sau khi công việc đã hoàn tất.');
  }else{
    if(resident()){
      const aptDefault=residentApartmentLabel(state.data.personal||{})||'';
      const fields=field('apartment_code','Căn hộ','text',aptDefault,'required placeholder="Ví dụ: A-1201"')
        +select('type','Loại yêu cầu',[['repair','Sửa chữa'],['maintenance','Bảo trì']])
        +field('description','Mô tả vấn đề','textarea','','required maxlength="10000" placeholder="Mô tả vị trí, hiện trạng và thời gian có thể hỗ trợ…"');
      formModal('Tạo yêu cầu sửa chữa / bảo trì',fields,async data=>{
        const apts=state.data.apartments||await items('/api/apartments');
        const match=apts.find(a=>a.code.toUpperCase()===data.apartment_code.toUpperCase());
        if(match)data.apartment_id=match.apartment_id;
        return saved(post('/api/maintenance/tickets',data),'Đã gửi yêu cầu sửa chữa.');
      },'Gửi yêu cầu','','vertical');
    }else{
      const [apartments,technicians]=await Promise.all([items('/api/apartments'),admin()?items('/api/maintenance/technicians'):Promise.resolve([])]);
      formModal('Tạo yêu cầu sửa chữa / bảo trì',
        select('apartment_id','Căn hộ',apartmentOptions(apartments))+
        select('type','Loại yêu cầu',enumOptions(['repair','maintenance']))+
        select('priority','Mức độ ưu tiên',enumOptions(['low','medium','high']),'medium')+
        (admin()?select('technician_id','Phân công kỹ thuật viên',technicians.map(t=>[t.technician_id,t.full_name]),'',false):'')+
        field('description','Mô tả vấn đề','textarea','','required maxlength="10000" placeholder="Mô tả vị trí, hiện trạng và thời gian có thể hỗ trợ…"'),
        data=>saved(post('/api/maintenance/tickets',data),'Đã gửi yêu cầu sửa chữa.'),
        'Gửi yêu cầu'
      );
    }
  }
}
const parkingTypes=[['motorbike','Xe máy'],['electric_bike','Xe điện (thu phí như xe máy)'],['bicycle','Xe đạp']];
const parkingFee=type=>type==='bicycle'?50000:100000;
function updateParkingFields(){
  const form=$('#modal-form'),type=form?.elements.vehicle_type?.value;if(!type)return;
  const plate=form.elements.plate_number;plate.required=type!=='bicycle';
  $('label[for="field-plate_number"]',form).innerHTML=`Biển số xe${plate.required?' <span class="req-star">*</span>':''}`;
  form.elements.monthly_fee.value=parkingFee(type);
}
function validateParking(data){
  if(!parkingTypes.some(([value])=>value===data.vehicle_type))throw new Error('Vui lòng chọn loại xe hợp lệ.');
  if(data.vehicle_type!=='bicycle'&&!data.plate_number?.trim())throw new Error('Vui lòng nhập biển số xe máy hoặc xe điện; xe điện chưa có biển cần biển nhận dạng theo căn hộ.');
  if(!Number.isInteger(data.registration_months)||data.registration_months<2)throw new Error('Thời gian gửi xe tối thiểu là 2 tháng.');
  data.monthly_fee=parkingFee(data.vehicle_type);
}
function parkingRulesModal(){
  const modal=$('#modal');
  const previous={nodes:[...modal.childNodes],submit:modalSubmit,scrollTop:modal.scrollTop,focus:document.activeElement};
  openModal('Quy định đăng ký gửi xe tại chung cư',`<div class="modal-body"><ul style="line-height:2.1;padding-left:20px;font-size:12px;color:var(--ink)"><li><strong>Thời gian gửi xe:</strong> Bắt buộc gửi tối thiểu 2 tháng. Phí gửi xe được thu 6 tháng một lần cùng tiền dịch vụ của tòa nhà.</li><li><strong>Biểu phí:</strong> Xe đạp: 50.000 VNĐ/xe/tháng. Xe máy: 100.000 VNĐ/xe/tháng. Xe điện (thu phí như xe máy): 100.000 VNĐ/xe/tháng.</li><li><strong>Phí làm thẻ:</strong> Tháng đầu tiên phụ thu 100.000 VNĐ/xe để làm thẻ gửi xe.</li><li><strong>Biển số & thẻ xe:</strong> Xe máy và xe điện bắt buộc khai báo biển số. Xe điện chưa có biển phải làm biển nhận dạng theo căn hộ. Không tự ý cho người ngoài tòa nhà mượn thẻ xe.</li><li><strong>Quy định di chuyển & đỗ xe:</strong> Tốc độ tối đa 20 km/h trong khuôn viên hầm xe. Đỗ đúng vị trí cho từng loại phương tiện; không chắn lối đi, lối thoát hiểm hoặc thiết bị PCCC.</li></ul><p style="margin-top:16px;line-height:1.9">Đơn đăng ký sẽ được xem xét và duyệt trong vòng 48h. Cảm ơn quý cư dân đã tin tưởng. Mọi thắc mắc vui lòng liên hệ trực tiếp với Ban quản lý qua số điện thoại <strong>0228913665</strong>!</p></div>`,`<div class="modal-footer">${button('Đóng','close-modal','','primary')}</div>`);
  modalReturn=previous;modalSubmit=null;modal.scrollTop=0;
}
async function parkingRequestForm(draft={},fromComplaint=false){
  const version=++modalVersion,route=state.route;
  const [profile,apartments,residents]=await Promise.all([
    resident()?(state.data.personal||api('/api/residents/me')):{},
    resident()?(state.data.apartments||items('/api/apartments')):[],
    admin()?(state.data.requestResidents||items('/api/residents')):[]
  ]);
  if(version!==modalVersion||route!==state.route||!state.user)return;
  const aptDefault=profile.apartment_codes?.[0]||profile.registered_apartment_code||apartments[0]?.code||'';
  const fields=(fromComplaint?select('type','Loại yêu cầu',[['complaint','Góp ý / Khiếu nại'],['registration','Đăng ký thủ tục']],'registration'):'')+
    (admin()?select('resident_id','Cư dân',residents.map(r=>[r.resident_id,r.full_name]),draft.resident_id||''):'')+
    select('vehicle_type','Loại xe',parkingTypes,draft.vehicle_type||'motorbike')+
    field('plate_number','Biển số xe','text',draft.plate_number||'','maxlength="30" aria-describedby="parking-plate-help" placeholder="Ví dụ: 29A-123.45 hoặc A101-XD01"')+
    '<p id="parking-plate-help" class="muted">Xe máy và xe điện phải có biển số. Xe điện chưa có biển phải làm biển nhận dạng theo căn hộ. Xe đạp được cấp mã khi duyệt đăng ký.</p>'+
    field('apartment_code','Căn hộ','text',draft.apartment_code||aptDefault,'required maxlength="30"')+
    field('registered_date','Ngày bắt đầu gửi xe','date',draft.registered_date||today(),'required')+
    field('registration_months','Thời gian cam kết (tháng, tối thiểu 2)','number',draft.registration_months||2,'required min="2" step="1"')+
    field('monthly_fee','Phí hàng tháng (VNĐ)','number',parkingFee(draft.vehicle_type),'readonly required')+
    field('notes','Ghi chú thêm','textarea',draft.notes||'','maxlength="1000" placeholder="Nhãn hiệu xe, màu sơn hoặc yêu cầu bổ sung…"')+
    button('Quy định đăng ký gửi xe tại chung cư','parking-rules-modal','shield','link')+
    '<div class="info-box">Thu phí 6 tháng một lần cùng tiền dịch vụ. Tháng đầu tiên phụ thu 100.000 VNĐ/xe để làm thẻ. Đơn được xem xét và duyệt trong vòng 48h. Mọi thắc mắc vui lòng liên hệ Ban quản lý: <strong>0228913665</strong>.</div>';
  formModal('Đơn đăng ký gửi xe',fields,data=>{
    validateParking(data);
    const content=`Loại xe: ${label(data.vehicle_type)}\nBiển số: ${data.plate_number||'Cấp mã theo căn hộ khi duyệt'}\nCăn hộ: ${data.apartment_code}\nNgày bắt đầu: ${data.registered_date}\nThời gian cam kết: ${data.registration_months} tháng (tối thiểu 2 tháng)\nPhí gửi xe: ${money(data.monthly_fee)}/xe/tháng\nPhí làm thẻ lần đầu: 100.000 VNĐ/xe trong tháng đầu\nThu phí: 6 tháng một lần cùng tiền dịch vụ\nGhi chú: ${data.notes||'Không có'}`;
    return saved(post('/api/complaints',{type:'registration',category:'Đăng ký gửi xe',content,...(admin()?{resident_id:data.resident_id}:{})}),'Đã gửi đơn đăng ký. Ban quản lý sẽ xem xét trong vòng 48h.');
  },'Gửi đơn đăng ký','','vertical');
  $('#modal-form').dataset.requestKind='registration';updateParkingFields();
}
async function noticeDetail(id){
  const notices=state.data.notices||await items('/api/notifications');
  let row=notices.find(n=>Number(n.notification_id)===Number(id));
  if(!row)row=await api(`/api/notifications/${id}`);
  if(!row.is_read){
    try{
      await post(`/api/notifications/${id}/read`);
      row.is_read=1;
      pollNotifications();
    }catch(e){}
  }
  const entries=[
    ['Tiêu đề',row.title],
    ['Phân loại',label(row.type)],
    ['Thời gian thông báo',dateTime(row.created_at)],
    ...(row.related_apartment_id?[['Căn hộ',row.related_apartment_code||apartmentCode(row.related_apartment_id)]]:row.target_apartment_id?[['Căn hộ nhận',apartmentCode(row.target_apartment_id)]]:[]),
    ...(row.invoice_created_at?[['Thời gian lập hóa đơn',dateTime(row.invoice_created_at)]]:[]),
    ...(row.paid_at?[['Thời gian thanh toán',dateTime(row.paid_at)]]:[]),
    ['Nội dung',row.content,true]
  ];
  openModal(row.title,`<div class="modal-body">${detail(entries)}</div>`,`<div class="modal-footer">${button('Đóng','close-modal','','secondary')}</div>`);
  if(state.route==='notifications')renderPage();
}
async function noticeForm(){
  const apartments=await items('/api/apartments');
  formModal('Soạn thông báo',select('audience','Đối tượng nhận',[['general','Thông báo chung đến mọi người'],['admin','Thông báo riêng đến Ban quản lý'],...apartments.map(a=>[String(a.apartment_id),`Căn hộ ${a.code}`])])+field('title','Tiêu đề','text','','required maxlength="250"')+field('content','Nội dung thông báo','textarea','','required maxlength="10000"'),data=>{const audience=data.audience;delete data.audience;data.type=audience==='general'?'general':'private';if(audience==='admin')data.target_role='admin';else if(audience!=='general')data.target_apartment_id=Number(audience);return saved(post('/api/notifications',data),'Đã đăng thông báo.');},'Đăng thông báo');
}
async function complaintForm(id,draft={}){
  const version=++modalVersion,route=state.route;
  if(id){
    const row=state.data.complaints.find(r=>r.complaint_id===Number(id));
    if(!admin()){
      openModal(`Yêu cầu #YC${id}`,`<div class="modal-body">${detail([['Loại yêu cầu',label(row.type)],['Danh mục',row.category],['Trạng thái',label(row.status)],['Ngày gửi',date(row.created_at)],['Nội dung',row.content,true],['Phản hồi của Ban quản lý',row.response||'Ban quản lý chưa phản hồi yêu cầu này.',true],['Ngày hoàn tất',date(row.resolved_at)]])}</div>`,`<div class="modal-footer">${button('Đóng','close-modal','','secondary')}</div>`);return;
    }
    const closed=['resolved','rejected'].includes(row.status);
    const statuses=closed?[row.status]:row.status==='processing'?['processing','resolved','rejected']:['pending','processing','resolved','rejected'];
    formModal(`Phản hồi yêu cầu #YC${id}`,detail([['Danh mục',row.category],['Nội dung cư dân gửi',row.content,true]])+select('status','Trạng thái',enumOptions(statuses),row.status)+field('response','Phản hồi của Ban quản lý','textarea',row.response||'','required maxlength="10000" placeholder="Nhập câu trả lời và hướng dẫn cụ thể cho cư dân…"'),data=>{if(!data.response?.trim())throw new Error('Vui lòng nhập nội dung phản hồi cho cư dân.');return saved(patch(`/api/complaints/${id}`,data),'Đã lưu phản hồi cho cư dân.');},row.response?'Cập nhật phản hồi':'Gửi phản hồi',`Cư dân đã gửi yêu cầu sẽ nhận thông báo riêng khi nội dung phản hồi được cập nhật.${closed?' Yêu cầu đã hoàn tất; bạn có thể sửa phản hồi.':''}`,'vertical');
  }else{
    const residents=admin()?await items('/api/residents'):[];
    if(version!==modalVersion||route!==state.route||!state.user)return;
    state.data.requestResidents=residents;
    formModal('Gửi yêu cầu đến Ban quản lý',
      (admin()?select('resident_id','Cư dân',residents.map(r=>[r.resident_id,r.full_name]),draft.resident_id||''):'')+
      select('type','Loại yêu cầu',[['complaint','Góp ý / Khiếu nại'],['registration','Đăng ký thủ tục']])+
      field('category','Danh mục / chủ đề','text',draft.category||'','required maxlength="100" placeholder="Ví dụ: Tiếng ồn, an ninh, vệ sinh…"')+
      field('content','Nội dung chi tiết','textarea',draft.content||'','required maxlength="10000" placeholder="Mô tả chi tiết vấn đề và mong muốn được hỗ trợ…"'),
      data=>saved(post('/api/complaints',data),'Đã gửi yêu cầu đến Ban quản lý.'),
      'Gửi yêu cầu',
      '',
      'vertical'
    );
    $('#modal-form').dataset.requestKind='complaint';
  }
}
function personalForm(){
  const row=state.data.personal||{},account=state.data.account||{};
  const aptLabel=residentApartmentLabel(row);
  formModal('Chỉnh sửa thông tin cá nhân',
    `<div class="field"><label>Số căn hộ</label><input value="${esc(aptLabel)}" readonly disabled aria-label="Số căn hộ" style="background:var(--bg);cursor:not-allowed"></div>`+
    field('username','Tên đăng nhập','text',account.username,'required minlength="3" maxlength="20" pattern="[A-Za-z0-9_.\\-]{3,20}" autocomplete="username"')+
    field('full_name','Họ và tên','text',row.full_name,'required minlength="10" maxlength="50" autocomplete="name"')+
    field('email','Email','email',account.email||'','required pattern="[A-Za-z0-9]+([.][A-Za-z0-9]+)*@[gG][mM][aA][iI][lL][.][cC][oO][mM]" title="Email phải có đuôi @gmail.com" autocomplete="email"')+
    field('phone','Số điện thoại','tel',row.phone||'','required maxlength="20" autocomplete="tel"')+
    field('id_card','CCCD','text',row.id_card||'','maxlength="30"'),
    async data=>{
      data.phone=data.phone||null;data.id_card=data.id_card||null;
      const result=await patch('/api/auth/me',data);state.user={...result.user,full_name:result.profile.full_name};
      state.token=result.token;sessionStorage.setItem('ancu_token',result.token);
      closeModal();toast('Đã cập nhật thông tin cá nhân.');shell();
    },
    'Lưu thông tin',
    'Căn hộ đã đăng ký do Ban quản lý quản lý và không thể tự thay đổi.',
    'vertical'
  );
}
function passwordForm(){
  formModal('Đổi mật khẩu',field('current_password','Mật khẩu hiện tại','password','','required maxlength="128" autocomplete="current-password"')+field('new_password','Mật khẩu mới','password','','required minlength="6" maxlength="30" autocomplete="new-password"')+field('confirm_password','Nhập lại mật khẩu mới','password','','required minlength="6" maxlength="30" autocomplete="new-password"'),async data=>{
    if(data.new_password!==data.confirm_password)throw new Error('Mật khẩu mới và mật khẩu nhập lại không trùng khớp.');
    await saved(post('/api/auth/me/password',data),'Đã đổi mật khẩu thành công.');
  },'Đổi mật khẩu');
}
function userForm(id){
  const row=id?state.data.users.find(u=>u.user_id===Number(id)):{};
  const fields=id?select('status','Trạng thái tài khoản',[['active','Đang hoạt động'],['locked','Đã khóa']],row.status)+field('lock_reason','Lý do khóa (không bắt buộc)','textarea',row.lock_reason||'','maxlength="500"')+field('password','Mật khẩu mới (để trống nếu không đổi)','password','','minlength="6" maxlength="30" autocomplete="new-password"'):field('username','Tên đăng nhập','text','','required minlength="3" maxlength="20" autocomplete="off"')+field('password','Mật khẩu','password','','required minlength="6" maxlength="30" autocomplete="new-password"')+field('email','Email','email','','autocomplete="off"')+field('phone','Số điện thoại (không bắt buộc)','tel','','maxlength="20"')+select('role','Vai trò',Object.entries(roleNames).map(([value,text])=>[value,text]),'resident');
  formModal(id?`Cập nhật tài khoản ${row.username}`:'Tạo tài khoản hệ thống',fields,data=>saved(id?patch(`/api/auth/users/${id}`,data):post('/api/auth/users',data)),'Lưu tài khoản',id?'Khóa tài khoản để ngăn đăng nhập. Không thể tự khóa tài khoản đang sử dụng.':'Sau khi tạo tài khoản, liên kết với hồ sơ cư dân hoặc hồ sơ kỹ thuật tương ứng.');
}
function technicianForm(id){
  const row=id?state.data.technicians.find(t=>t.technician_id===Number(id)):{};
  const users=(state.data.users||[]).filter(u=>u.role==='technician'&&(!state.data.technicians.some(t=>t.user_id===u.user_id)||row.user_id===u.user_id));
  formModal(id?'Cập nhật kỹ thuật viên':'Thêm kỹ thuật viên',select('user_id','Tài khoản kỹ thuật viên',users.map(u=>[u.user_id,u.username]),row.user_id||'')+field('full_name','Họ và tên','text',row.full_name||'','required maxlength="120"')+select('specialty','Chuyên môn',[['general','Kỹ thuật tổng hợp'],['parking','Quản lý gửi xe'],['payment','Dịch vụ & thanh toán']],row.specialty||'general'),data=>saved(id?patch(`/api/maintenance/technicians/${id}`,data):post('/api/maintenance/technicians',data)));
}
function knowledgeForm(kind,id){
  if(kind==='faqs'){
    const row=id?state.data.faqs.find(f=>f.faq_id===Number(id)):{};
    formModal(id?'Cập nhật nội dung chính sách':'Thêm câu hỏi & chính sách',field('category','Danh mục','text',row.category||'','maxlength="150"')+field('question','Câu hỏi','text',row.question||'','required maxlength="1500"')+field('answer','Nội dung trả lời','textarea',row.answer||'','required maxlength="10000"'),data=>saved(id?patch(`/api/chatbot/faqs/${id}`,data):post('/api/chatbot/faqs',data)));
  }else{
    const row=id?state.data.locations.find(l=>l.location_id===Number(id)):{};
    formModal(id?'Cập nhật tiện ích':'Thêm vị trí tiện ích',field('name','Tên tiện ích','text',row.name||'','required maxlength="200"')+field('block','Tòa / khu vực','text',row.block||'','maxlength="200"')+field('floor','Tầng','text',row.floor??'','maxlength="200"')+field('description','Mô tả & chỉ dẫn','textarea',row.description||'','maxlength="5000"'),data=>saved(id?patch(`/api/chatbot/locations/${id}`,data):post('/api/chatbot/locations',data)));
  }
}
function exportReport(){
  if($('#page')?.getAttribute('aria-busy')==='true'){toast('Vui lòng đợi báo cáo cập nhật xong.');return;}
  const report=state.data.report;if(!report)return;
  const csvCell=value=>`"${String(value??'').replace(/"/g,'""').replace(/^[=+@-]/,"'$&")}"`;
  const rows=[['Kỳ báo cáo','Đã phát hành (VNĐ)','Đã thu (VNĐ)','Công nợ (VNĐ)','Số hóa đơn','Đã thanh toán'],...(report.items||[]).map(r=>[r.period,r.billed_amount,r.collected_amount,r.outstanding_amount,r.invoice_count,r.paid_count])];
  downloadBlob(new Blob(['\uFEFF'+rows.map(r=>r.map(csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),`bao-cao-doanh-thu-${report.year||thisYear()}.csv`);
}
async function askChat(question){
  const value=question.trim();if(!value)return;
  const form=$('#chat-form'),messages=$('#chat-messages');if(!form||!messages)return;
  if(form.dataset.busy==='true')return;form.dataset.busy='true';
  state.chat.push({role:'user',text:value});messages.insertAdjacentHTML('beforeend',chatMessage({role:'user',text:value}));form.reset();
  const loader=document.createElement('div');loader.className='chat-message chat-loading';loader.textContent='Đang tìm thông tin…';messages.append(loader);messages.scrollTop=messages.scrollHeight;
  $('button',form).disabled=true;
  try{const result=await post('/api/chatbot/ask',{question:value});const reply={role:'bot',text:result.answer,source:result.source_title||result.source};state.chat.push(reply);loader.outerHTML=chatMessage(reply);}
  catch(error){loader.textContent=error.message;state.chat.push({role:'bot',text:error.message});}
  finally{form.dataset.busy='false';$('button',form).disabled=false;messages.scrollTop=messages.scrollHeight;$('input',form).focus();}
}
function filterTable(){
  const query=($('#table-search')?.value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase(),status=$('#table-status')?.value||'';
  let visible=0;
  $$('.data-table tbody tr').forEach(row=>{const search=row.dataset.search.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();row.hidden=!(search.includes(query)&&(!status||row.dataset.status===status));if(!row.hidden)visible++;});
  const count=$('.row-count');if(count)count.textContent=`${visible} bản ghi phù hợp`;
}

document.addEventListener('click',async event=>{
  if(event.target.closest('.sidebar a[href^="#"]'))closeMenu();
  const target=event.target.closest('[data-action]');if(!target||target.disabled)return;
  const action=target.dataset.action,id=target.dataset.id,kind=target.dataset.kind;
  try{
    switch(action){
      case 'auth-switch':authView(target.dataset.register==='true');break;
      case 'logout':logout();break;
      case 'menu':$('.sidebar').classList.add('open');$('.mobile-scrim').classList.add('open');break;
      case 'menu-close':closeMenu();break;
      case 'navigate':navigate(target.dataset.route);break;
      case 'refresh':await renderPage();break;
      case 'close-modal':closeModal();break;
      case 'tab':state.tab[state.route]=target.dataset.tab;await renderPage();break;
      case 'apartment-create':await apartmentForm();break;
      case 'apartment-edit':await apartmentForm(id);break;
      case 'apartment-detail':await apartmentDetail(id);break;
      case 'profile-edit':personalForm();break;
      case 'password-edit':passwordForm();break;
      case 'resident-create':await residentForm();break;
      case 'resident-edit':await residentForm(id);break;
      case 'resident-detail':await residentDetail(id);break;
      case 'resident-apartments':await residentApartments(id);break;
      case 'resident-apartment-remove':await residentApartmentRemove(id,target.dataset.apartment);break;
      case 'contract-create':await contractForm();break;
      case 'contract-edit':await contractForm(id);break;
      case 'invoice-create':await invoiceForm();break;
      case 'invoice-detail':await invoiceDetail(kind,id);break;
      case 'invoice-edit':invoiceEdit(kind,id);break;
      case 'invoice-pay':target.disabled=true;await checkout(kind,id);break;
      case 'invoice-cash':cashPayment(kind,id);break;
      case 'payment-confirm':await confirmTransfer();break;
      case 'payment-cancel':await cancelPayment();break;
      case 'bank-transaction-resolve':resolveBankTransaction(id);break;
      case 'payment-history':closeModal();state.tab.billing='payments';navigate('billing');break;
      case 'payment-check':await checkPayment(paymentWatch,true);break;
      case 'receipt':target.disabled=true;await receipt(kind,id);break;
      case 'vehicle-create':await vehicleForm();break;
      case 'vehicle-edit':await vehicleForm(id);break;
      case 'guest-create':guestForm();break;
      case 'parking-request':requestDrafts={complaint:{},registration:{}};await parkingRequestForm();break;
      case 'parking-rules-modal':parkingRulesModal();break;
      case 'ticket-create':await ticketForm();break;
      case 'ticket-edit':await ticketForm(id);break;
      case 'notice-create':await noticeForm();break;
      case 'notice-detail':await noticeDetail(id);break;
      case 'notice-filter':state.noticeFilter=target.dataset.filter;await renderPage();break;
      case 'notice-read':target.disabled=true;await post(`/api/notifications/${id}/read`);await renderPage();pollNotifications();break;
      case 'complaint-create':requestDrafts={complaint:{},registration:{}};await complaintForm();break;
      case 'complaint-edit':await complaintForm(id);break;
      case 'user-create':userForm();break;
      case 'user-edit':userForm(id);break;
      case 'technician-create':technicianForm();break;
      case 'technician-edit':technicianForm(id);break;
      case 'faq-create':knowledgeForm('faqs');break;
      case 'faq-edit':knowledgeForm('faqs',id);break;
      case 'location-create':knowledgeForm('locations');break;
      case 'location-edit':knowledgeForm('locations',id);break;
      case 'report-export':exportReport();break;
      case 'chat-suggest':await askChat(target.dataset.question);break;
      case 'push-enable':target.disabled=true;await AnCuPush.enable();toast('Đã bật thông báo trình duyệt.');await renderPage();break;
      case 'push-disable':target.disabled=true;await AnCuPush.disable();toast('Đã tắt thông báo trên trình duyệt này.');await renderPage();break;
    }
  }catch(error){toast(error.message,true);}
  finally{target.disabled=false;}
});
document.addEventListener('submit',async event=>{
  const form=event.target;
  if(!['auth-form','modal-form','chat-form'].includes(form.id))return;
  event.preventDefault();
  if(form.id==='chat-form'){await askChat(new FormData(form).get('question')||'');return;}
  const submit=$('[type="submit"]',form),errorBox=$('.form-error',form);
  submit.disabled=true;errorBox.hidden=true;
  try{
    const data=formValues(form);
    if(form.id==='auth-form'){
      const registering=form.dataset.register==='true';
      const result=await post(registering?'/api/auth/register':'/api/auth/login',data);
      if(registering){
        state.token=null;state.user=null;sessionStorage.removeItem('ancu_token');
        authView();$('#auth-form [name=username]').value=data.username;
        toast('Đăng ký thành công. Vui lòng đăng nhập.');$('#auth-form [name=password]').focus();
      }else{
        state.token=result.token;state.user=result.user;sessionStorage.setItem('ancu_token',result.token);
        history.replaceState(null,'','#overview');shell();
      }
    }else if(modalSubmit){await modalSubmit(data);}
  }catch(error){
    if(form.id==='auth-form'&&error.code==='ACCOUNT_LOCKED'){
      openModal('Tài khoản đã bị khóa',`<div class="modal-body"><p>Tài khoản của bạn đã bị khóa.</p>${error.reason?`<p style="margin-top:12px">Lý do: ${esc(error.reason)}</p>`:''}<p style="margin-top:12px">Vui lòng liên hệ Ban quản lý để được hỗ trợ.</p></div>`,`<div class="modal-footer">${button('Đã hiểu','close-modal','','primary')}</div>`);
    }else{errorBox.textContent=error.message;errorBox.hidden=false;}
  }
  finally{submit.disabled=false;}
});
document.addEventListener('invalid',event=>{
  const input=event.target;
  if(input.type==='password'&&input.minLength===6&&input.value&&input.value.length<6){
    input.setCustomValidity('Mật khẩu cần ít nhất 6 ký tự.');
  }else if(input.name==='full_name'&&input.minLength===10&&input.value&&input.value.trim().length<10){
    input.setCustomValidity('Họ tên phải có từ 10 đến 50 ký tự.');
  }
},true);
document.addEventListener('input',event=>{
  if(event.target.setCustomValidity)event.target.setCustomValidity('');
  if(event.target.id==='table-search')filterTable();
  if(['electricity_usage','electricity_unit_price','water_usage','water_unit_price'].includes(event.target.name))updateUtilityPreview();
});
document.addEventListener('change',async event=>{
  if(event.target.name==='vehicle_type'&&event.target.closest('#modal-form'))updateParkingFields();
  if(event.target.name==='type'&&event.target.closest('#modal-form')?.dataset.requestKind){
    const form=event.target.form,kind=form.dataset.requestKind,data=formValues(form);
    requestDrafts[kind]=data;
    try{
      if(data.type==='registration')await parkingRequestForm({...requestDrafts.registration,...(data.resident_id?{resident_id:data.resident_id}:{})},true);
      else await complaintForm(null,{...requestDrafts.complaint,...(data.resident_id?{resident_id:data.resident_id}:{})});
    }catch(error){event.target.value=kind;toast(error.message,true);}
  }
  if(event.target.id==='table-status')filterTable();
  if(event.target.id==='report-year'){state.reportYear=Number(event.target.value);renderPage();}
  if(event.target.id==='report-group'){state.reportGroup=event.target.value;renderPage();}
});
window.addEventListener('hashchange',()=>{if(state.user){state.route=location.hash.slice(1)||'overview';renderPage();}});
document.addEventListener('visibilitychange',()=>{if(!document.hidden){refreshBilling();pollNotifications();}});
$('#modal').addEventListener('click',event=>{if(event.target===$('#modal')){const bounds=event.target.getBoundingClientRect();if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)closeModal();}});
$('#modal').addEventListener('cancel',event=>{event.preventDefault();closeModal();});
$('#modal').addEventListener('close',()=>{stopPaymentWatch();modalSubmit=null;modalReturn=null;if(modalBlob){URL.revokeObjectURL(modalBlob);modalBlob=null;}});
document.addEventListener('keydown',event=>{if(event.key==='Escape')closeMenu();});
(async()=>{
  if(state.token){try{const result=await api('/api/auth/me');state.user=result.user;shell();return;}catch{sessionStorage.removeItem('ancu_token');state.token=null;}}
  authView();
})();

'use strict';

// Lets a long HTML fragment span several lines in the source without adding whitespace to the page.
const view = (strings, ...values) =>
  strings.reduce((out, text, i) => out + text.replace(/\n\s*/g, '') + (i < values.length ? String(values[i]) : ''), '');

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value) =>
  String(value ?? '').replace(
    /[&<>"']/g,
    (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char],
  );
const money = (value) =>
  new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(
    Number(value || 0),
  );
const number = (value) => new Intl.NumberFormat('vi-VN').format(Number(value || 0));
const date = (value) => {
  if (!value) return '—';
  const parsed = new Date(
    /^\d{4}-\d{2}-\d{2}$/.test(String(value)) ? value + 'T12:00:00' : String(value).replace(' ', 'T'),
  );
  return Number.isNaN(parsed.getTime())
    ? 'Chưa cập nhật'
    : new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(parsed);
};
// SQLite CURRENT_TIMESTAMP is UTC even when the container TZ is Vietnam.
// Explicit offsets from payments are respected; date-only deadlines stay dates.
function dateTime(value) {
  if (!value) return 'Chưa ghi nhận';
  let text = String(value).trim().replace(' ', 'T');
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return `${date(text)} (chưa có giờ)`;
  if (!/(Z|[+-]\d{2}:?\d{2})$/i.test(text)) text += 'Z';
  const parsed = new Date(text);
  return Number.isNaN(parsed.getTime())
    ? 'Chưa cập nhật'
    : new Intl.DateTimeFormat('vi-VN', {
        timeZone: 'Asia/Ho_Chi_Minh',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hourCycle: 'h23',
      }).format(parsed);
}
const today = () => new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' });
const thisYear = () => new Date().getFullYear();
const icons = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  building:
    '<path d="M4 21V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v16M17 9h3v12M2 21h20M8 7h1m3 0h1M8 11h1m3 0h1M8 15h1m3 0h1M9 21v-3h3v3"/>',
  people: '<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6m2 3a5 5 0 0 1 3 4v3"/>',
  invoice: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z"/><path d="M9 7h6m-6 4h6m-6 4h3"/>',
  car: '<path d="m5 7 2-4h10l2 4 2 4v7H3v-7l2-4Zm0 0h14M3 12h18M5 18v3m14-3v3M6 15h2m8 0h2"/>',
  wrench: '<path d="M14 6a5 5 0 0 0-6 6l-5 5a2.1 2.1 0 0 0 3 3l5-5a5 5 0 0 0 6-6l-3 3-3-3 3-3Z"/><path d="m18 3 3 3"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  message: '<path d="M21 11a8 8 0 0 1-8 8H8l-5 3V5a3 3 0 0 1 3-3h7a8 8 0 0 1 8 9Z"/><path d="M7 7h8M7 11h8M7 15h4"/>',
  chart: '<path d="M4 3v18h18M8 16v-4m5 4V7m5 9V3"/>',
  bot: '<rect x="3" y="6" width="18" height="15" rx="4"/><path d="M12 6V3m-1 0h2M7 11v2m10-2v2m-9 4h8M1 11v5m22-5v5"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  plus: '<path d="M12 4v16M4 12h16"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
  logout: '<path d="M9 4H4v16h5m6-13 5 5-5 5m-7-5h12"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  menu: '<path d="M3 5h18M3 12h18M3 19h18"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 11h18m-14 4h2m4 0h2"/>',
  wallet: '<path d="M20 7V4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16V7H4a1 1 0 0 1 0-2"/><path d="M20 11h-5v5h5m-2-3h-1"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 15v6h16v-6"/>',
  refresh: '<path d="M20 8a8 8 0 0 0-14-3L3 8m0-5v5h5m-4 8a8 8 0 0 0 14 3l3-3m0 5v-5h-5"/>',
  edit: '<path d="m16 3 5 5-12 12H4v-5L16 3Zm-3 3 5 5M3 22h18"/>',
  shield: '<path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4Z"/><path d="m8 12 3 3 5-6"/>',
  send: '<path d="m22 2-7 20-4-9L2 9 22 2ZM11 13 22 2"/>',
  eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff:
    '<path d="M3 3l18 18M10.6 5.1A10 10 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.2 4M6.6 6.6A17 17 0 0 0 2 12s3.6 7 10 7a10 10 0 0 0 5.4-1.6M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  location: '<path d="M19 9c0 6-7 13-7 13S5 15 5 9a7 7 0 1 1 14 0Z"/><circle cx="12" cy="9" r="2"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  phone: '<path d="M5 3h4l2 5-2.5 1.5a12 12 0 0 0 6 6L16 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 5a2 2 0 0 1 2-2Z"/>',
  power: '<path d="M12 3v9M6.4 6.4a8 8 0 1 0 11.2 0"/>',
  idcard:
    '<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="8" cy="11" r="2"/><path d="M5 16a3 3 0 0 1 6 0M14 10h5M14 14h5"/>',
};
const icon = (name) =>
  view`
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.grid}</svg>
  `;
const state = {
  token: sessionStorage.getItem('ancu_token'),
  user: null,
  route: 'overview',
  tab: {},
  data: {},
  sequence: 0,
  chat: [],
  notificationTimer: null,
};
const roleNames = { admin: 'Ban quản lý', resident: 'Cư dân', technician: 'Kỹ thuật viên' };
const admin = () => state.user?.role === 'admin';
const tech = () => state.user?.role === 'technician';
const resident = () => state.user?.role === 'resident';
// The parent role of invoice management, mirroring BILLING_MANAGERS in billing-service:
// admin and technician inherit the same screen and actions. Reports stay admin-only.
const billingManager = () => admin() || tech();
const billingTitle = () => (billingManager() ? 'Quản lý hóa đơn' : 'Hóa đơn & thanh toán');
const dockRoutes = {
  admin: ['overview', 'billing', 'residents', 'complaints'],
  resident: ['overview', 'billing', 'complaints', 'maintenance'],
  technician: ['overview', 'maintenance', 'services', 'parking'],
};
const dockLabels = { billing: 'Hóa đơn', complaints: 'Khiếu nại' };
const navItems = [
  ['overview', 'Tổng quan', 'grid', ['admin', 'resident', 'technician'], 'Tổng quan'],
  ['apartments', 'Quản lý căn hộ', 'building', ['admin'], 'Căn hộ'],
  ['residents', 'Cư dân & hợp đồng', 'people', ['admin'], 'Cư dân'],
  ['profile', 'Thông tin cá nhân', 'user', ['admin', 'resident', 'technician'], 'Cá nhân'],
  ['billing', 'Hóa đơn & thanh toán', 'invoice', ['admin', 'resident', 'technician'], 'Hóa đơn'],
  ['parking', 'Quản lý gửi xe', 'car', ['admin', 'resident', 'technician'], 'Gửi xe'],
  ['maintenance', 'Sửa chữa & bảo trì', 'wrench', ['admin', 'resident', 'technician'], 'Sửa chữa'],
  ['services', 'Quản lý dịch vụ', 'power', ['technician'], 'Dịch vụ'],
  ['notifications', 'Thông báo', 'bell', ['admin', 'resident', 'technician'], 'Thông báo'],
  ['complaints', 'Khiếu nại & đăng ký', 'message', ['admin', 'resident'], 'Khiếu nại & đăng ký'],
  ['reports', 'Báo cáo & thống kê', 'chart', ['admin'], 'Báo cáo'],
  ['users', 'Nhân sự & tài khoản', 'shield', ['admin'], 'Nhân sự'],
];
const statusLabels = {
  paid: 'Đã thanh toán',
  unpaid: 'Chưa thanh toán',
  overdue: 'Quá hạn',
  occupied: 'Đã có cư dân',
  vacant: 'Còn trống',
  empty: 'Còn trống',
  active: 'Đang hoạt động',
  cancelled: 'Đã hủy',
  pending: 'Chờ xử lý',
  processing: 'Đang xử lý',
  in_progress: 'Đang xử lý',
  completed: 'Hoàn thành',
  resolved: 'Đã giải quyết',
  rejected: 'Từ chối',
  expired: 'Hết hạn',
  terminated: 'Đã kết thúc',
  owner: 'Sở hữu',
  tenant: 'Thuê',
  rent: 'Thuê',
  own: 'Sở hữu',
  high: 'Cao',
  medium: 'Trung bình',
  low: 'Thấp',
  success: 'Thành công',
  failed: 'Thất bại',
};
const typeLabels = {
  repair: 'Sửa chữa',
  maintenance: 'Bảo trì',
  cut_service: 'Tạm ngưng dịch vụ',
  restore_service: 'Khôi phục dịch vụ',
  complaint: 'Khiếu nại',
  registration: 'Đơn đăng ký',
  general: 'Thông báo chung',
  private: 'Thông báo riêng',
  car: 'Ô tô',
  motorbike: 'Xe máy',
  motorcycle: 'Xe máy',
  bicycle: 'Xe đạp',
  electric_bike: 'Xe điện',
  monthly: 'Hàng tháng',
  semiannual: '6 tháng',
  cash: 'Tiền mặt',
  bank_transfer: 'Chuyển khoản',
  qr: 'QR',
  sepay: 'VietQR · SePay',
  parking: 'Gửi xe',
  payment: 'Thanh toán',
  electricity: 'Điện',
  common_service: 'Dịch vụ chung',
  water: 'Nước',
  awaiting_confirmation: 'Chờ ngân hàng xác nhận',
  matched: 'Đã đối soát',
  partial: 'Chuyển thiếu',
  overpaid: 'Chuyển dư',
  duplicate: 'Chuyển lặp',
  unmatched: 'Chưa xác định hóa đơn',
  ignored: 'Không ghi nhận thu',
  refunded: 'Đã hoàn trả',
  retained: 'Đã thống nhất giữ lại',
  reviewed: 'Đã kiểm tra',
};
const label = (value) => statusLabels[value] || typeLabels[value] || value || '—';
const badge = (value) =>
  view`
    <span class="badge ${['paid', 'active', 'completed', 'resolved', 'success', 'occupied'].includes(value) ? 'green' : ['unpaid', 'pending', 'medium', 'processing'].includes(value) ? 'amber' : ['overdue', 'high', 'rejected', 'failed'].includes(value) ? 'red' : ['in_progress', 'owner'].includes(value) ? 'blue' : ''}">${esc(label(value))}</span>
  `;

async function api(path, options = {}) {
  const headers = {
    'Accept': 'application/json',
    ...(state.token ? { 'Authorization': `Bearer ${state.token}` } : {}),
    ...options.headers,
  };
  if (options.body && typeof options.body !== 'string') {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  let response;
  try {
    response = await fetch(path, { ...options, headers });
  } catch {
    throw new Error('Không thể kết nối máy chủ. Vui lòng kiểm tra kết nối và thử lại.');
  }
  let result;
  try {
    result = await response.json();
  } catch {
    result = {};
  }
  if (response.status === 401 && state.user) {
    logout();
    throw new Error('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
  }
  if (!response.ok) {
    const error = new Error(result.error || result.message || `Yêu cầu chưa thực hiện được (${response.status}).`);
    error.code = result.code;
    error.reason = result.reason;
    error.status = response.status;
    throw error;
  }
  return result;
}
const items = async (path) => (await api(path)).items || [];
const post = (path, body = {}) => api(path, { method: 'POST', body });
const patch = (path, body) => api(path, { method: 'PATCH', body });
function toast(message, error = false) {
  const item = document.createElement('div');
  item.className = `toast${error ? ' error' : ''}`;
  item.textContent = message;
  $('#toasts').append(item);
  setTimeout(() => item.remove(), 5500);
}
function button(text, action, glyph = 'plus', style = 'primary', extra = '') {
  return view`
    <button type="button" class="button ${style} inline-flex items-center justify-center gap-2 rounded-xl font-semibold focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-forest-600" data-action="${esc(action)}" ${extra}>${glyph ? icon(glyph) : ''}${esc(text)}</button>
  `;
}
function heading(title, subtitle, actions = '', eyebrow = '') {
  return view`
    <div class="page-heading flex flex-wrap items-start justify-between gap-4">
      <div>${eyebrow ? `<div class="eyebrow">${esc(eyebrow)}</div>` : ''}<h1>${esc(title)}</h1>${subtitle ? `<p>${esc(subtitle)}</p>` : ''}</div>${actions ? `<div class="heading-actions">${actions}</div>` : ''}</div>
  `;
}
function stat(title, value, note, glyph = 'building', tone = '', unit = '') {
  const currency = String(value).includes('₫');
  return view`
    <div class="stat-card min-w-0">
      <div class="stat-top">
        <span>${esc(title)}</span>
        <span class="stat-icon ${tone}">${icon(glyph)}</span>
    </div>
    <div class="stat-value${currency ? ' stat-value--currency' : ''}">${esc(value)}${unit ? `<small>${esc(unit)}</small>` : ''}</div>
    <div class="stat-foot">${esc(note)}</div>
    </div>
  `;
}
const emptyArt = view`
  <svg class="empty-art" viewBox="0 0 120 88" aria-hidden="true">
    <ellipse cx="60" cy="81" rx="50" ry="5" fill="#d9eee1"/>
    <rect x="36" y="14" width="34" height="66" rx="5" fill="#1f7f57"/>
    <rect x="70" y="36" width="22" height="44" rx="4" fill="#8fd0a9"/>
    <g fill="#d6f2e0">
      <rect x="43" y="22" width="7" height="7" rx="1.5"/>
      <rect x="56" y="22" width="7" height="7" rx="1.5"/>
      <rect x="43" y="36" width="7" height="7" rx="1.5"/>
      <rect x="56" y="36" width="7" height="7" rx="1.5"/>
      <rect x="43" y="50" width="7" height="7" rx="1.5"/>
      <rect x="56" y="50" width="7" height="7" rx="1.5"/>
    </g>
    <rect x="49" y="66" width="8" height="14" rx="1.5" fill="#f3fbf6"/>
    <g fill="#f3fbf6">
      <rect x="76" y="44" width="5" height="5" rx="1"/>
      <rect x="76" y="56" width="5" height="5" rx="1"/>
    </g>
    <g fill="#2f9a6b">
      <path d="M22 80c-8-8-8-20 0-30 8 10 8 22 0 30Z"/>
      <path d="M104 80c-6-6-6-15 0-22 6 7 6 16 0 22Z"/>
    </g>
  </svg>
`;
function empty(
  title = 'Chưa có dữ liệu',
  description = 'Dữ liệu sẽ xuất hiện tại đây khi được cập nhật.',
  action = '',
) {
  return `<div class="empty-state">${emptyArt}<h3>${esc(title)}</h3><p>${esc(description)}</p>${action}</div>`;
}
function table(columns, rows, options = {}) {
  if (!rows.length) return empty(options.emptyTitle, options.emptyDescription);
  const searchText = options.search || ((row) => Object.values(row).join(' '));
  return view`
    <div class="table-scroll overflow-x-auto">
      <table class="data-table w-full text-left">
        <thead>
          <tr>${columns.map((c) => `<th scope="col">${esc(c[0])}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${rows.map((row, i) => view`
            <tr data-search="${esc(String(searchText(row)).toLowerCase())}" data-status="${esc(row.status || '')}" data-type="${esc(options.type ? options.type(row) : '')}">${columns.map((c) => `<td>${c[1](row, i)}</td>`).join('')}</tr>
          `).join('')}
          </tbody>
      </table>
    </div>
    ${options.count === false ? '' : `<div class="row-count">${rows.length} bản ghi</div>`}
    
  `;
}
function toolbar(placeholder = 'Tìm kiếm…', statuses = [], types = []) {
  const typeSelect = types.length
    ? view`
      <select id="table-type" aria-label="Lọc loại xe">
        <option value="">Tất cả loại xe</option>
        ${types.map(([value, text]) => `<option value="${esc(value)}">${esc(text)}</option>`).join('')}
        </select>
    `
    : '';
  const statusSelect = statuses.length
    ? view`
      <select id="table-status" aria-label="Lọc trạng thái">
        <option value="">Tất cả trạng thái</option>
        ${statuses.map((x) => `<option value="${esc(x)}">${esc(label(x))}</option>`).join('')}
        </select>
    `
    : '';
  return view`
    <div class="toolbar">
      <div class="search-box">${icon('search')}<input type="search" id="table-search" placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}">
      </div>
      ${typeSelect || statusSelect ? `<div class="filter-group">${typeSelect}${statusSelect}</div>` : ''}
      </div>
  `;
}
function tabs(route, tabsList) {
  const active = state.tab[route] || tabsList[0][0];
  return view`
    <div class="tabs" role="tablist" aria-label="Chọn danh sách">
      ${tabsList.map(([key, text]) => view`
        <button class="tab ${active === key ? 'active' : ''}" role="tab" aria-selected="${active === key}" data-action="tab" data-tab="${esc(key)}">${esc(text)}</button>
      `).join('')}
      </div>
  `;
}
function field(name, title, type = 'text', value = '', attrs = '') {
  const id = `field-${name}`;
  const isReq = attrs.includes('required') || title.includes('*');
  const cleanTitle = esc(title.replace(/\s*\*/g, '').replace(/\s*\(không bắt buộc\)/g, ''));
  const labelHtml = isReq ? `${cleanTitle} <span class="req-star">*</span>` : cleanTitle;
  const control =
    type === 'textarea'
      ? `<textarea id="${id}" name="${esc(name)}" ${attrs}>${esc(value)}</textarea>`
      : type === 'password'
        ? view`
          <div class="password-wrap">
            <input id="${id}" name="${esc(name)}" type="password" data-secret="true" value="${esc(value)}" ${attrs}>
            <button type="button" class="password-toggle" data-action="toggle-password" data-target="${id}" aria-controls="${id}" aria-label="Hiện mật khẩu" aria-pressed="false" title="Hiện mật khẩu">${icon('eye')}</button>
          </div>
        `
        : `<input id="${id}" name="${esc(name)}" type="${type}" value="${esc(value)}" ${attrs}>`;
  return view`
    <div class="field ${type === 'textarea' ? 'wide' : ''}">
    <label for="${id}">${labelHtml}</label>${control}</div>
  `;
}
function select(name, title, options, value = '', required = true) {
  const id = `field-${esc(name)}`;
  const isReq = Boolean(required) || title.includes('*');
  const cleanTitle = esc(title.replace(/\s*\*/g, '').replace(/\s*\(không bắt buộc\)/g, ''));
  const labelHtml = isReq ? `${cleanTitle} <span class="req-star">*</span>` : cleanTitle;
  return view`
    <div class="field">
      <label for="${id}">${labelHtml}</label>
    <select id="${id}" name="${esc(name)}" ${required ? 'required' : ''}>${!required ? '<option value="">Chưa chọn</option>' : ''}
    ${options.map((o) => `<option value="${esc(o[0])}" ${String(value) === String(o[0]) ? 'selected' : ''}>${esc(o[1])}</option>`).join('')}
    </select>
    </div>
  `;
}
// A value the user sees but cannot change; the optional hidden input still submits it.
function fixedField(title, shown, name = '', value = '') {
  return view`
    <div class="field">
      <label>${esc(title)}</label>
      <input value="${esc(shown)}" readonly disabled aria-label="${esc(title)}" style="background:var(--bg);cursor:not-allowed">
      ${name ? `<input type="hidden" name="${esc(name)}" value="${esc(value)}">` : ''}
    </div>
  `;
}
const apartmentOptions = (rows) => rows.map((r) => [r.apartment_id, `${r.code} · Tòa ${r.block || '—'}`]);
const enumOptions = (values) => values.map((v) => [v, label(v)]);
const detail = (entries) =>
  view`
    <dl class="detail-list">
      ${entries.map(([key, value, wide]) => `<div class="${wide ? 'wide' : ''}"><dt>${esc(key)}</dt><dd>${esc(value ?? '—')}</dd></div>`).join('')}
      </dl>
  `;
let modalSubmit = null,
  modalBlob = null,
  modalReturn = null,
  modalVersion = 0;
let requestDrafts = { complaint: {}, registration: {} };
let paymentWatch = null;
function stopPaymentWatch() {
  if (paymentWatch) {
    clearTimeout(paymentWatch.timer);
    clearInterval(paymentWatch.clock);
    paymentWatch.controller?.abort();
  }
  paymentWatch = null;
}
function closeModal() {
  ++modalVersion;
  if (modalReturn) {
    const previous = modalReturn;
    modalReturn = null;
    $('#modal').replaceChildren(...previous.nodes);
    modalSubmit = previous.submit;
    $('#modal').scrollTop = previous.scrollTop;
    previous.focus?.focus({ preventScroll: true });
    return;
  }
  stopPaymentWatch();
  $('#modal').close();
}
function openModal(title, body, footer = '') {
  ++modalVersion;
  stopPaymentWatch();
  modalReturn = null;
  if (modalBlob) {
    URL.revokeObjectURL(modalBlob);
    modalBlob = null;
  }
  const modal = $('#modal');
  delete modal.dataset.invoiceKind;
  delete modal.dataset.invoiceId;
  modal.innerHTML = view`
    <div class="modal-header">
      <h2 id="modal-title">${esc(title)}</h2>
      <button class="icon-button" data-action="close-modal" aria-label="Đóng">${icon('close')}</button>
    </div>${body}${footer}
  `;
  if (!modal.open) modal.showModal();
}
function formModal(title, fields, onSubmit, submitText = 'Lưu thông tin', intro = '', layout = '', cancel = true) {
  modalSubmit = onSubmit;
  const gridClass = layout === 'vertical' ? 'form-grid vertical' : 'form-grid';
  openModal(
    title,
    view`
      <form id="modal-form">
        <div class="modal-body">${intro ? `<div class="info-box">${esc(intro)}</div>` : ''}<div class="form-error" role="alert" hidden>
          </div>
          <div class="${gridClass}">${fields}</div>
      </div>
      <div class="modal-footer">${cancel ? button('Hủy', 'close-modal', '', 'secondary') : ''}<button type="submit" class="button primary">${icon('check')}${esc(submitText)}</button>
      </div>
      </form>
    `,
  );
}
async function saved(action, message = 'Đã lưu thông tin.') {
  await action;
  modalReturn = null;
  closeModal();
  toast(message);
  await renderPage();
}
function formValues(form) {
  const result = {};
  for (const [key, value] of new FormData(form).entries()) {
    if (value === '') continue;
    const input = form.elements.namedItem(key);
    result[key] =
      input?.type === 'number' ? Number(value) : input?.dataset?.secret ? String(value) : String(value).trim();
  }
  return result;
}
function authView(register = false) {
  clearInterval(state.notificationTimer);
  clearInterval(state.billingTimer);
  $('#app').innerHTML = `<main class="auth-page${register ? ' auth-page--register' : ''}" id="main">
    <section class="auth-art" aria-label="Không gian An Cư">
      <div class="auth-photo absolute inset-0 overflow-hidden"><img class="h-full w-full object-cover" src="/assets/images/residence-detail.jpg" alt="Kiến trúc chung cư hiện đại" width="1200" height="1800" fetchpriority="high"><div class="auth-photo-shade"></div></div>
      <a class="brand" href="#" aria-label="An Cư"><div class="brand-mark">A</div><div><div class="brand-name">AN CƯ<span class="brand-dot">.</span></div><div class="brand-tag">Không gian sống · Kết nối cộng đồng</div></div></a>
      <div class="auth-image-inset"><img src="/assets/images/community-lounge.jpg" alt="Góc sinh hoạt với nội thất và cây xanh" width="900" height="1350" decoding="async"><span>Nhịp sống an cư</span></div>
      <div class="auth-intro"><div class="auth-visual-label"><span class="live-dot"></span> Sống an tâm. Kết nối dễ dàng.</div><h1>Chốn an cư.<br>Điều tốt đẹp<br>mỗi ngày.</h1><p>Từ những tiện ích thường ngày đến sự gắn kết trong cộng đồng. An Cư đồng hành cùng không gian sống của bạn.</p><div class="auth-feature-pills hidden min-[701px]:flex flex-wrap gap-3"><span>${icon('building')} Quản lý thuận tiện</span><span>${icon('people')} Cộng đồng gắn kết</span></div></div>
      <footer><span>An Cư · Cổng thông tin chung cư</span></footer>
    </section>
    <section class="auth-main"><form id="auth-form" class="auth-form" data-register="${register}">
      <div class="auth-welcome-icon" aria-hidden="true">${icon('building')}</div><div class="eyebrow">Chào mừng đến An Cư</div><h2>${register ? 'Bắt đầu kết nối' : 'Chào mừng trở lại'}</h2><p class="auth-subtitle">${register ? 'Tạo tài khoản để quản lý tiện ích và kết nối với Ban quản lý.' : 'Đăng nhập để quản lý không gian sống của bạn.'}</p><div class="form-error" role="alert" hidden></div>
      ${register ? field('full_name', 'Họ và tên', 'text', '', 'required autocomplete="name" minlength="2" maxlength="50"') : ''}
      ${field('username', 'Tên đăng nhập', 'text', '', `required autocomplete="username" minlength="3" maxlength="${register ? 20 : 60}" ${register ? 'pattern="[A-Za-z0-9_.\\-]{3,20}" title="Tên đăng nhập gồm 3–20 chữ cái, số, dấu chấm, gạch dưới hoặc gạch ngang."' : ''} placeholder="Nhập tên đăng nhập"`)}
      ${register ? field('apartment_code', 'Số căn hộ', 'text', '', 'required maxlength="30" placeholder="Ví dụ: A101" title="Nhập số căn hộ theo dạng Tòa + số phòng, ví dụ A101"') + field('email', 'Email', 'email', '', 'required autocomplete="email" placeholder="ten@gmail.com" pattern="[A-Za-z0-9]+([.][A-Za-z0-9]+)*@[gG][mM][aA][iI][lL][.][cC][oO][mM]" title="Email phải có đuôi @gmail.com"') + field('phone', 'Số điện thoại', 'tel', '', 'required autocomplete="tel" maxlength="20"') : ''}
      ${field('password', 'Mật khẩu', 'password', '', `required autocomplete="${register ? 'new-password' : 'current-password'}" minlength="${register ? '6' : '1'}" maxlength="${register ? 30 : 128}"`)}
      <button type="submit" class="button primary">${register ? 'Tạo tài khoản cư dân' : 'Đăng nhập'} ${icon('arrow')}</button><p class="auth-switch">${register ? 'Đã có tài khoản?' : 'Bạn là cư dân mới?'} <button type="button" class="text-button" data-action="auth-switch" data-register="${!register}">${register ? 'Đăng nhập' : 'Đăng ký tài khoản'}</button></p>
      <div class="auth-note flex items-start gap-3">${icon('shield')}<span>${register ? 'Ban quản lý sẽ xác nhận thông tin và liên kết căn hộ với tài khoản của bạn.' : 'Cần hỗ trợ truy cập? Vui lòng liên hệ Ban quản lý chung cư để được hướng dẫn.'}</span></div>
    </form><div class="auth-form-footer">Một không gian. Mọi kết nối.</div></section>
  </main>`;
}
function residentApartmentLabel(profile) {
  return profile.apartment_codes?.length
    ? profile.apartment_codes.join(', ')
    : profile.registered_apartment_code || 'Chưa liên kết';
}
async function loadResidentContext() {
  if (!resident()) return;
  const userId = state.user.user_id;
  try {
    const profile = await api('/api/residents/me');
    if (!state.user || state.user.user_id !== userId) return;
    state.data.personal = profile;
    state.user.full_name = profile.full_name;
    state.user.apartment_label = profile.apartment_codes?.length
      ? profile.apartment_codes.join(', ')
      : profile.registered_apartment_code
        ? `${profile.registered_apartment_code} (chưa xác nhận)`
        : 'Chưa liên kết';
    const greet = $('#header-greeting-title');
    if (greet) greet.textContent = `Xin chào, ${state.user.full_name || state.user.username} 👋`;
    const nameEl = $('#account-label');
    if (nameEl) nameEl.textContent = state.user.full_name || state.user.username;
    const aptEl = $('#resident-apt-tag');
    if (aptEl) aptEl.textContent = state.user.apartment_label ? `Căn hộ ${state.user.apartment_label}` : '';
  } catch {
    /* Keep navigation usable when profile service is unavailable. */
  }
}
function shell() {
  clearInterval(state.notificationTimer);
  clearInterval(state.billingTimer);
  const name = state.user.username;
  const fullName = state.user.full_name || name;
  const nav = navItems
    .filter((n) => n[3].includes(state.user.role))
    .map((n) => (n[0] === 'billing' && billingManager() ? [n[0], billingTitle(), n[2], n[3], billingTitle()] : n));
  const brandHref = resident() ? '#profile' : '#overview';
  const dateStr = esc(
    new Intl.DateTimeFormat('vi-VN', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date()),
  );
  const bellBtn = view`
    <button class="icon-button notification-bell" data-action="navigate" data-route="notifications" aria-label="Xem thông báo" style="position:relative">${icon('bell')}<span class="notification-badge" id="notification-badge" hidden>
      </span>
    </button>
  `;
  const logoutBtn = view`
    <button class="icon-button" data-action="logout" aria-label="Đăng xuất" title="Đăng xuất">${icon('logout')}</button>
  `;

  let headerLeft = '',
    headerRight = '';
  if (resident()) {
    headerLeft = view`
      <div class="header-greeting">
        <strong class="greeting-title" id="header-greeting-title">Xin chào, ${esc(fullName)} 👋</strong>
        <span class="greeting-subtitle">Sẻ chia không gian, nhân đôi hạnh phúc.</span>
      </div>
    `;
    headerRight = view`
      <div class="resident-identity">
        <strong id="account-label">${esc(fullName)}</strong>
        <span class="apt-tag" id="resident-apt-tag">
          ${state.user.apartment_label ? `Căn hộ ${esc(state.user.apartment_label)}` : ''}
          </span>
      </div>${bellBtn}<span class="top-date">${icon('calendar')} ${dateStr}</span>${logoutBtn}
    `;
  } else {
    headerLeft = view`
      <div class="header-greeting">
        <strong class="greeting-title" id="header-greeting-title">Xin chào, ${esc(fullName)} 👋</strong>
        <span class="greeting-subtitle">Cùng chăm sóc một cộng đồng an cư mỗi ngày.</span>
      </div>
    `;
    headerRight = view`
      <span class="top-date">${icon('calendar')} ${dateStr}</span>${bellBtn}<div class="user-control">
        <span class="avatar grid shrink-0 place-items-center">${esc(name.slice(0, 2).toUpperCase())}</span>
        <div class="user-info">
          <strong id="account-label">${esc(fullName)}</strong>
          <small>${esc(roleNames[state.user.role])}</small>
        </div>${logoutBtn}</div>
    `;
  }

  const dock = dockRoutes[state.user.role]
    .map((route) => nav.find((n) => n[0] === route))
    .map(
      (n) =>
        view`
          <a href="#${n[0]}" data-route="${n[0]}" aria-label="${esc(n[1])}">${icon(n[2])}<span>${dockLabels[n[0]] || n[4]}</span>
          </a>
        `,
    )
    .join('');
  $('#app').innerHTML =
    view`
      <div class="layout${admin() ? '' : ' layout-rail'}">
        <button class="mobile-scrim" aria-label="Đóng điều hướng" data-action="menu-close">
        </button>
        <aside class="sidebar">
          <a class="brand" href="${brandHref}" aria-label="An Cư - Trang chủ">
          <div class="brand-mark">A</div>
          <div>
            <div class="brand-name">AN CƯ<span class="brand-dot">.</span>
            </div>
            <div class="brand-tag">Quản lý chung cư</div>
          </div>
        </a>
        <div class="workspace-label">${icon('building')}<div>Cổng thông tin chung cư<small>${esc(roleNames[state.user.role])}</small>
          </div>
        </div>
        <div class="nav-heading">Không gian làm việc</div>
        <nav class="nav" aria-label="Điều hướng chính">
          ${nav.map((n) => view`
            <a href="#${n[0]}" data-route="${n[0]}" aria-label="${esc(n[1])}" title="${esc(n[1])}">${icon(n[2])}<span class="nav-full">${n[1]}</span>
            <span class="nav-short">${n[4]}</span>
            </a>
          `).join('')}
          </nav>
        <div class="sidebar-bottom">
          <div class="support-card">${icon('bot')}<strong>Mọi câu hỏi, một trợ lý</strong>
            <p>Tra cứu chính sách và tiện ích chung cư bất cứ lúc nào.</p>
            <button data-action="navigate" data-route="chatbot" data-tab="chat" aria-label="Mở trợ lý An Cư">
              <span class="support-rail">${icon('bot')}Trợ lý</span>
              <span class="support-cta">Trò chuyện ngay ${icon('arrow')}</span>
            </button>
          </div>
        </div>
      </aside>
      <div class="body-area">
        <header class="topbar">${headerLeft}<div class="topbar-right">${headerRight}</div>
        </header>
        <main class="main" id="main" tabindex="-1">
          <div id="page">
          </div>
          <footer class="page-footer">
            <span>© ${thisYear()} An Cư. Kết nối một cộng đồng tốt đẹp hơn.</span>
            <span>${icon('shield')} Cổng thông tin quản lý chung cư</span>
          </footer>
        </main>
      </div>
      <nav class="dock" aria-label="Điều hướng nhanh">${dock}<button data-action="menu" aria-label="Mở tất cả chức năng">${icon('menu')}<span>Thêm</span>
        </button>
      </nav>
      </div>
    `;
  loadResidentContext();
  const hashRoute = location.hash.slice(1);
  state.route =
    hashRoute === 'chatbot' || nav.some((n) => n[0] === hashRoute) ? hashRoute : resident() ? 'profile' : 'overview';
  renderPage();
  pollNotifications();
  state.notificationTimer = setInterval(pollNotifications, 5000);
  state.billingTimer = setInterval(refreshBilling, 5000);
  resumePayment();
  startPush();
}
function startPush() {
  AnCuPush.start(state.token, state.user.user_id, (payload) => {
    toast(payload.title || 'Bạn có thông báo mới.');
    pollNotifications();
    if (state.route === 'notifications' && !$('#modal').open) renderPage();
  }).catch(() => {});
}
// A password change revokes earlier tokens, so this tab must switch to the one just issued.
function adoptToken(result) {
  if (result?.token) {
    state.token = result.token;
    sessionStorage.setItem('ancu_token', result.token);
    startPush();
  }
  return result;
}
function logout() {
  AnCuPush.stop().catch((error) => toast(error.message, true));
  state.pushUnsubscribe?.();
  state.pushUnsubscribe = null;
  state.lastNotificationId = null;
  state.token = null;
  state.user = null;
  state.data = {};
  state.chat = [];
  state.tab = {};
  modalReturn = null;
  sessionStorage.removeItem('ancu_token');
  sessionStorage.removeItem('ancu_push_token');
  closeModal();
  authView();
}
function navigate(route) {
  if (location.hash === `#${route}`) {
    state.route = route;
    renderPage();
  } else location.hash = route;
}
function closeMenu() {
  $('.sidebar')?.classList.remove('open');
  $('.mobile-scrim')?.classList.remove('open');
}
async function pollNotifications() {
  if (!state.user || document.hidden || state.notificationPolling) return;
  const user = state.user;
  state.notificationPolling = true;
  try {
    const list = await items('/api/notifications');
    if (state.user !== user) return;
    const count = list.filter((n) => !n.is_read).length;
    const badgeEl = $('#notification-badge');
    if (badgeEl) {
      badgeEl.hidden = !count;
      badgeEl.textContent = count > 99 ? '99+' : String(count);
    }
    const latest = list[0]?.notification_id;
    if (state.lastNotificationId != null && latest && latest !== state.lastNotificationId) {
      toast('Bạn có thông báo mới tại bảng tin.');
      if (state.route === 'notifications' && !$('#modal').open) renderPage();
    }
    state.lastNotificationId = latest;
  } catch {
    /* A service outage must not interrupt the active form. */
  } finally {
    state.notificationPolling = false;
  }
}
async function refreshBilling() {
  if (
    !state.user ||
    state.route !== 'billing' ||
    document.hidden ||
    state.billingRefreshing ||
    $('#page')?.getAttribute('aria-busy') === 'true'
  )
    return;
  state.billingRefreshing = true;
  const version = modalVersion,
    user = state.user,
    modal = $('#modal');
  try {
    if (modal.open) {
      const kind = modal.dataset.invoiceKind,
        id = modal.dataset.invoiceId;
      if (!kind || !id) return; // Leave forms, receipts and the QR watcher alone.
      const row = await api(`/api/billing/invoices/${kind}/${id}`);
      if (state.user !== user || state.route !== 'billing' || modalVersion !== version || !modal.open) return;
      if (JSON.stringify(row) !== JSON.stringify(state.currentInvoice)) await invoiceDetail(kind, id, row);
    } else await renderPage({ background: true });
  } catch {
    /* Keep the current view and retry when the connection recovers. */
  } finally {
    state.billingRefreshing = false;
  }
}
async function renderPage({ background = false } = {}) {
  if (!state.user) return;
  const allowed = navItems.filter((n) => n[3].includes(state.user.role));
  if (state.route !== 'chatbot' && !allowed.some((n) => n[0] === state.route))
    state.route = resident() ? 'profile' : 'overview';
  const seq = ++state.sequence;
  const page = $('#page');
  if (!page) return;
  const route = state.route,
    previousRoute = page.dataset.route,
    scrollY = window.scrollY;
  page.setAttribute('aria-busy', 'true');
  const navTitle =
    state.route === 'chatbot'
      ? 'Trợ lý cư dân'
      : state.route === 'billing'
        ? billingTitle()
        : allowed.find((n) => n[0] === state.route)?.[1] || 'An Cư';
  document.title = `${navTitle} · An Cư`;
  const bc = $('#breadcrumb-title');
  if (bc) bc.textContent = navTitle;
  $$('[data-route].active').forEach((n) => n.classList.remove('active'));
  $$(`.nav [data-route="${route}"],.dock [data-route="${route}"]`).forEach((n) => n.classList.add('active'));
  $('.dock [data-action=menu]')?.classList.toggle('active', !$(`.dock [data-route="${route}"]`));
  if (previousRoute !== route && matchMedia('(min-width:701px)').matches)
    $(`.nav [data-route="${route}"]`)?.scrollIntoView({ block: 'nearest' });
  if (!page.hasChildNodes())
    page.innerHTML = '<div class="loading" role="status"><span class="spinner"></span>Đang tải dữ liệu…</div>';
  closeMenu();
  try {
    const html = await pages[route]();
    if (seq !== state.sequence || !state.user) return;
    if (background && ($('#modal').open || document.hidden)) return;
    if (background && state.billingMarkup === html) return;
    const search = background ? $('#table-search')?.value : null,
      status = background ? $('#table-status')?.value : null,
      typeFilter = background ? $('#table-type')?.value : null;
    const focused = background ? document.activeElement?.id : null;
    page.innerHTML = html;
    page.dataset.route = route;
    // Only arriving on a screen animates; saves and background refreshes stay still.
    page.classList.toggle('page-enter', previousRoute !== route);
    state.billingMarkup = route === 'billing' ? html : null;
    if (background) {
      if ($('#table-search') && search != null) $('#table-search').value = search;
      if ($('#table-status') && status != null) $('#table-status').value = status;
      if ($('#table-type') && typeFilter != null) $('#table-type').value = typeFilter;
      filterTable();
      if (['table-search', 'table-status'].includes(focused))
        document.getElementById(focused)?.focus({ preventScroll: true });
    }
    if (previousRoute === route) window.scrollTo({ top: scrollY, behavior: 'instant' });
    else window.scrollTo({ top: 0, behavior: 'instant' });
  } catch (error) {
    if (seq !== state.sequence || !state.user || background) return;
    page.dataset.route = route;
    page.innerHTML = view`
      ${heading(navTitle, 'Dữ liệu hiện chưa sẵn sàng.')}<div class="error-box" role="alert">${esc(error.message)}</div>${button('Thử lại', 'refresh', 'refresh', 'secondary')}
    `;
  } finally {
    if (seq === state.sequence) page.setAttribute('aria-busy', 'false');
  }
}

function revenueChart(rows, height = 220) {
  if (!rows.length || !rows.some((r) => Number(r.collected_amount) > 0))
    return '<div class="empty-chart">Chưa có doanh thu đã thu trong kỳ.<br>Biểu đồ sẽ cập nhật khi ghi nhận thanh toán.</div>';
  const width = 650,
    left = 65,
    right = 15,
    top = 15,
    bottom = 35,
    chartHeight = height - top - bottom,
    chartWidth = width - left - right,
    max = Math.max(...rows.map((r) => Number(r.collected_amount || 0)), 1) * 1.18;
  const gap = chartWidth / rows.length,
    barWidth = Math.min(30, gap * 0.5);
  let body = '';
  for (let i = 0; i <= 4; i++) {
    const y = top + chartHeight * (1 - i / 4),
      v = (max * i) / 4;
    body += view`
      <line class="gridline" x1="${left}" y1="${y}" x2="${width - right}" y2="${y}"/>
      <text x="${left - 10}" y="${y + 3}" text-anchor="end">
      ${esc(v >= 1000000 ? `${(v / 1000000).toFixed(1)} tr` : number(Math.round(v)))}
      </text>
    `;
  }
  rows.forEach((r, i) => {
    const value = Number(r.collected_amount || 0),
      barHeight = (value / max) * chartHeight,
      x = left + gap * i + (gap - barWidth) / 2;
    body += view`
      <rect class="bar" style="--i:${i}" fill="url(#bar-fill)" x="${x}" y="${top + chartHeight - barHeight}" width="${barWidth}" height="${barHeight}" rx="5">
      <title>${esc(r.period)}: ${esc(money(value))}</title>
      </rect>
      <text x="${x + barWidth / 2}" y="${height - 12}" text-anchor="middle">
      ${esc(
      String(r.period)
        .replace(/^\d{4}-/, '')
        .replace('Q', 'Quý '),
    )}
      </text>
    `;
  });
  return view`
    <svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Biểu đồ doanh thu đã thu theo kỳ">
    <defs>
      <linearGradient id="bar-fill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#46b985"/>
        <stop offset="1" stop-color="#16684a"/>
      </linearGradient>
    </defs>${body}</svg>
  `;
}
function invoiceColumns(withActions = true) {
  return [
    [
      'Hóa đơn',
      (r) =>
        view`
          <span class="primary-cell">#${r.invoice_type === 'semiannual' ? 'DV' : 'HD'}${esc(String(r.invoice_id).padStart(4, '0'))}</span>
          <span class="sub-cell">${esc(label(r.invoice_type))} · ${esc(periodText(r.period))}</span>
          <span class="sub-cell">Lập: ${esc(dateTime(r.created_at))}</span>
        `,
    ],
    ['Căn hộ', (r) => esc(r.apartment_code || apartmentCode(r.apartment_id))],
    ['Số tiền', (r) => `<span class="money">${money(r.total_amount)}</span>`],
    ['Hạn thanh toán', (r) => esc(date(r.due_date))],
    [
      'Trạng thái',
      (r) => `${badge(r.status)}${r.paid_at ? `<span class="sub-cell">${esc(dateTime(r.paid_at))}</span>` : ''}`,
    ],
    ...(withActions
      ? [
          [
            '',
            (r) =>
              button(
                resident() && r.status !== 'paid' ? 'Thanh toán' : 'Chi tiết',
                'invoice-detail',
                '',
                'link',
                `data-id="${esc(r.invoice_id)}" data-kind="${esc(r.invoice_type)}"`,
              ),
          ],
        ]
      : []),
  ];
}
const invoiceCode = (kind, id) => `#${kind === 'semiannual' ? 'DV' : 'HD'}${String(id).padStart(4, '0')}`;
const invoiceSearch = (r) => {
  const code = invoiceCode(r.invoice_type, r.invoice_id);
  return `${code} ${code.slice(1)} ${r.invoice_id} ${r.apartment_code || apartmentCode(r.apartment_id)}`;
};
const bankSearch = (r) => {
  const invoice = r.invoice_id ? invoiceCode(r.invoice_type, r.invoice_id) : '';
  return `${r.bank_reference || ''} ${r.reference || ''} ${invoice} ${invoice.slice(1)} ${r.invoice_id ? `${label(r.invoice_type)} #${r.invoice_id}` : ''}`;
};
// An extra parking invoice is stored as YYYY-Hn-XE<vehicle id>.
const periodText = (period) =>
  /-XE\d+$/.test(period) ? `${String(period).replace(/-XE\d+$/, '')} (gửi xe bổ sung)` : period;
function apartmentCode(id) {
  return (
    state.data.apartments?.find((a) => Number(a.apartment_id) === Number(id))?.code ||
    state.data.apartmentCodes?.[id] ||
    'Chưa xác định'
  );
}
function overviewHero() {
  const title = admin()
    ? 'Vận hành tận tâm.<span>Cộng đồng an cư.</span>'
    : tech()
      ? 'Chăm chút từng chi tiết.<span>An tâm mỗi ngày.</span>'
      : 'Một chốn bình yên.<span>Mọi kết nối gần hơn.</span>';
  const description = admin()
    ? 'Một góc nhìn trọn vẹn để chăm sóc cư dân, quản lý dịch vụ và giữ nhịp sống chung cư luôn thông suốt.'
    : tech()
      ? 'Theo dõi công việc, cập nhật tiến độ và cùng xây dựng một không gian sống được chăm sóc chu đáo.'
      : 'Theo dõi hóa đơn, gửi yêu cầu và cập nhật tin tức của cộng đồng. Những việc thường ngày, gọn trong một nơi.';
  const primary = admin()
    ? ['Xem báo cáo', 'reports']
    : tech()
      ? ['Xem công việc', 'maintenance']
      : ['Xem hóa đơn', 'billing'];
  return `<section class="overview-hero relative isolate overflow-hidden" aria-labelledby="overview-hero-title">
    <div class="overview-hero-copy"><div class="overview-hero-kicker"><span class="live-dot"></span> AN CƯ · GẮN KẾT MỖI NGÀY</div><h2 class="overview-hero-title" id="overview-hero-title">${title}</h2><p class="overview-hero-description">${description}</p><div class="overview-hero-actions flex flex-wrap items-center gap-3">${button(primary[0], 'navigate', 'arrow', 'primary', `data-route="${primary[1]}"`)}${button('Bảng tin cộng đồng', 'navigate', 'bell', 'secondary', 'data-route="notifications"')}</div></div>
    <figure class="overview-hero-media relative m-0 min-w-0 overflow-hidden">
      <img class="hero-main-photo" src="/assets/images/residence-garden.jpg" alt="Khu căn hộ hiện đại với không gian xanh" width="1600" height="898" fetchpriority="high">
      <div class="hero-photo-inset"><img src="/assets/images/community-lounge.jpg" alt="Nội thất sáng và cây xanh" width="900" height="1350" decoding="async"><span>Chạm vào sự bình yên</span></div>
      <div class="hero-floating-note">${icon('people')}<span>Cùng nhau, gần hơn<small>Một không gian · Nhiều kết nối</small></span></div>
      <figcaption class="hero-image-caption">Không gian sống đầy cảm hứng</figcaption>
    </figure>
  </section>`;
}
// Management's overview is long enough already, so only residents and technicians get these.
function overviewShortcuts() {
  const entries = tech()
      ? [
          ['Công việc kỹ thuật', 'Tiếp nhận và cập nhật tiến độ', 'maintenance', 'wrench'],
          ['Quản lý hóa đơn', 'Theo dõi hóa đơn và các khoản đã thu', 'billing', 'wallet'],
          ['Thu phí vãng lai', 'Ghi nhận doanh thu gửi xe', 'parking', 'car'],
        ]
      : [
          ['Hồ sơ của tôi', 'Thông tin cư dân và căn hộ', 'profile', 'people'],
          ['Gửi yêu cầu', 'Để Ban quản lý hỗ trợ bạn', 'complaints', 'message'],
          ['Sửa chữa & bảo trì', 'Báo hỏng và theo dõi tiến độ', 'maintenance', 'wrench'],
          ['Chính sách chung cư', 'Nội quy, phí dịch vụ và câu hỏi thường gặp', 'chatbot', 'shield', 'faqs'],
        ];
  const photos = ['residence-garden.jpg', 'community-lounge.jpg', 'garden-walk.jpg', 'residence-detail.jpg'];
  return view`
    <section aria-labelledby="overview-shortcuts-title">
      <div class="overview-section-heading">
        <div>
          <div class="eyebrow">TIỆN ÍCH NHANH</div>
          <h2 id="overview-shortcuts-title">Dành cho ngày của bạn</h2>
        </div>
        <p>Kết nối mọi việc, từ một nơi.</p>
      </div>
      <div class="overview-shortcuts grid gap-4${entries.length > 3 ? ' four' : ''}">
        ${entries.map(([title, description, route, glyph, tab], index) => view`
          <button type="button" class="overview-shortcut" data-action="navigate" data-route="${route}"${tab ? ` data-tab="${tab}"` : ''}>
          <span class="shortcut-media">
            <img src="/assets/images/${photos[index]}" alt="" width="${index === 0 ? 1600 : 900}" height="${index === 0 ? 898 : 1350}" loading="lazy" decoding="async">
            <span class="shortcut-index" aria-hidden="true">0${index + 1}</span>
          </span>
          <span class="shortcut-body">
            <span class="shortcut-icon">${icon(glyph)}</span>
            <span class="shortcut-copy min-w-0 flex-1">
              <strong>${title}</strong>
              <span>${description}</span>
            </span>${icon('arrow')}</span>
          </button>
        `).join('')}
        </div>
    </section>
  `;
}
function pageSpotlight(kind, person = null) {
  const content =
    kind === 'profile'
      ? [
          'HỒ SƠ CƯ DÂN',
          'Không gian riêng, kết nối chung.',
          'Thông tin của bạn giúp Ban quản lý chăm sóc và hỗ trợ đúng lúc.',
          'community-lounge.jpg',
        ]
      : kind === 'staff-profile'
        ? [
            'HỒ SƠ NHÂN SỰ',
            'Đồng hành cùng cộng đồng.',
            'Thông tin của bạn giúp các bộ phận liên hệ và phối hợp đúng lúc.',
            'residence-detail.jpg',
          ]
        : [
            'CHUYỆN CỦA CỘNG ĐỒNG',
            'Mỗi cập nhật, một kết nối.',
            'Theo dõi thông báo và những điều cần biết trong nhịp sống chung cư.',
            'garden-walk.jpg',
          ];
  const avatar = person ? `<span class="spotlight-avatar" aria-hidden="true">${esc(person.initial)}</span>` : '';
  const chips = person
    ? view`
      <div class="spotlight-chips">
        ${person.chips.map(([glyph, text]) => `<span>${icon(glyph)}${esc(text)}</span>`).join('')}
        </div>
    `
    : '';
  return view`
    <section class="page-spotlight" data-spotlight="${kind}">
    <div>${avatar}<div class="spotlight-copy">
        <div class="eyebrow">${content[0]}</div>
        <h2>${content[1]}</h2>
        <p>${content[2]}</p>${chips}</div>
    </div>
    <img src="/assets/images/${content[3]}" alt="Không gian sống xanh" width="900" height="1350" decoding="async">
    </section>
  `;
}
function profileFacts(rows) {
  return view`
    <dl class="profile-facts">
      ${rows.map(([title, value, glyph, wide]) => view`
        <div class="profile-fact${wide ? ' wide' : ''}">
        <dt>
          <span class="profile-fact-icon">${icon(glyph)}</span>${esc(title)}</dt>
        <dd>${esc(value ?? '—')}</dd>
        </div>
      `).join('')}
      </dl>
  `;
}
const pages = {
  async profile() {
    const actions =
      button('Chỉnh sửa thông tin', 'profile-edit', 'edit') +
      button('Đổi mật khẩu', 'password-edit', 'shield', 'secondary');
    if (!resident()) {
      const staff = (await api('/api/auth/me')).user;
      state.data.account = staff;
      state.data.personal = null;
      const staffInitial = String(staff.full_name || staff.username)
        .trim()
        .split(/\s+/)
        .pop()
        .charAt(0)
        .toUpperCase();
      return (
        heading('Thông tin cá nhân', 'Xem và cập nhật hồ sơ của bạn.', actions) +
        pageSpotlight('staff-profile', { initial: staffInitial, chips: [['shield', roleNames[staff.role]]] }) +
        view`
          <section class="panel">
            <div class="panel-header">
              <h2>Thông tin nhân sự</h2>
              <span class="period-chip">Hồ sơ của bạn</span>
            </div>
            <div class="panel-body">
              ${profileFacts(
          [
            ['Họ và tên', staff.full_name || 'Chưa cập nhật', 'people', true],
            ['Vai trò', roleNames[staff.role], 'shield'],
            ['Email', staff.email || 'Chưa cập nhật', 'mail', true],
            ['Số điện thoại', staff.phone || 'Chưa cập nhật', 'phone'],
            ['Tên đăng nhập', staff.username, 'user'],
            ['CCCD', staff.id_card || 'Chưa cập nhật', 'idcard', true],
          ],
        )}
              </div>
          </section>
        `
      );
    }
    const [account, personal] = await Promise.all([api('/api/auth/me'), api('/api/residents/me')]);
    state.data.personal = personal;
    state.data.account = account.user;
    const initial = String(personal.full_name || account.user.username || '?')
      .trim()
      .split(/\s+/)
      .pop()
      .charAt(0)
      .toUpperCase();
    return (
      heading('Thông tin cá nhân', 'Xem và cập nhật hồ sơ cư dân của bạn.', actions) +
      pageSpotlight('profile', {
        initial,
        chips: [
          ['building', residentApartmentLabel(personal)],
          ['shield', label(personal.relation_type)],
        ],
      }) +
      view`
        <section class="panel">
          <div class="panel-header">
            <h2>Thông tin cư dân</h2>
            <span class="period-chip">Hồ sơ của bạn</span>
          </div>
          <div class="panel-body">
            ${profileFacts(
        [
          ['Họ và tên', personal.full_name, 'people', true],
          ['Số căn hộ', residentApartmentLabel(personal), 'building'],
          ['Email', account.user.email || 'Chưa cập nhật', 'mail', true],
          ['Số điện thoại', personal.phone || 'Chưa cập nhật', 'phone'],
          ['Tên đăng nhập', account.user.username, 'user'],
          ['CCCD', personal.id_card || 'Chưa cập nhật', 'idcard'],
          ['Loại cư dân', label(personal.relation_type), 'shield'],
        ],
      )}
            </div>
        </section>
      `
    );
  },
  async overview() {
    const endpoints = tech()
      ? ['/api/maintenance/tickets', '/api/notifications', '/api/parking/guest-daily']
      : [
          '/api/apartments',
          '/api/billing/summary',
          '/api/billing/invoices/monthly',
          '/api/billing/invoices/semiannual',
          '/api/notifications',
          '/api/maintenance/tickets',
          '/api/complaints',
          ...(admin() ? [`/api/billing/reports?year=${thisYear()}&group=month`] : []),
        ];
    const result = await Promise.allSettled(endpoints.map((p) => api(p)));
    const data = result.map((r) => (r.status === 'fulfilled' ? r.value : null)),
      failed = result.filter((r) => r.status === 'rejected').length;
    const warning = failed
      ? view`
        <div class="info-box">${failed} nguồn dữ liệu tạm thời chưa kết nối được. Bạn có thể mở từng chức năng hoặc tải lại trang để thử lại.</div>
      `
      : '';
    const top =
      heading(
        'Tổng quan',
        admin()
          ? 'Nhịp sống cộng đồng, trong tầm tay bạn.'
          : tech()
            ? 'Công việc hôm nay, không gian tốt hơn mỗi ngày.'
            : 'Chào ngày mới tại không gian của bạn.',
        button('Cập nhật', 'refresh', 'refresh', 'secondary'),
      ) + overviewHero();
    if (tech()) {
      const tickets = data[0]?.items || [],
        notices = data[1]?.items || [],
        guests = data[2]?.items || [];
      state.data.tickets = tickets;
      return overviewBoard(
        top +
          warning +
          view`
            <div class="stats-grid grid grid-cols-2 gap-3 min-[1280px]:grid-cols-4 min-[1280px]:gap-5">
              ${stat('Công việc kỹ thuật', number(tickets.length), 'Tất cả phiếu của đội kỹ thuật', 'wrench')}
              
              ${stat('Đang chờ xử lý', number(tickets.filter((t) => t.status === 'pending').length), 'Cần tiếp nhận', 'clock', 'orange')}
              
              ${stat('Đang thực hiện', number(tickets.filter((t) => t.status === 'in_progress').length), 'Cập nhật tiến độ thường xuyên', 'wrench', 'blue')}
              
              ${stat('Đã hoàn thành', number(tickets.filter((t) => t.status === 'completed').length), 'Phiếu đã đóng', 'check', 'purple')}
              </div>
            <div class="overview-stack">
              <section class="panel">
                <div class="panel-header">
                  <h2>Công việc cần xử lý</h2>
                  ${button('Tất cả', 'navigate', 'arrow', 'link', 'data-route="maintenance"')}
                  </div>
                ${table(
            [
              [
                'Yêu cầu',
                (r) =>
                  view`
                  <span class="primary-cell">#${esc(r.ticket_id)} · ${esc(label(r.type))}</span>
                  <span class="sub-cell">${esc(r.description?.slice(0, 80))}</span>
                `,
              ],
              ['Ưu tiên', (r) => badge(r.priority)],
              ['Trạng thái', (r) => badge(r.status)],
              ['', (r) => button('Xử lý', 'ticket-edit', '', 'link', `data-id="${r.ticket_id}"`)],
            ],
            tickets.filter((t) => t.status !== 'completed').slice(0, 5),
            { count: false },
          )}
                </section>
              <section class="panel">
                <div class="panel-header">
                  <h2>Thao tác nhanh</h2>
                </div>
                <div class="quick-actions">${quick('Tiếp nhận công việc', 'maintenance', 'wrench')}${quick('Quản lý dịch vụ', 'services', 'power')}${quick('Thu phí vãng lai', 'parking', 'car')}</div>
              </section>
            </div>
          `,
        [
          ...tickets
            .filter((t) => t.status !== 'completed')
            .slice(0, 3)
            .map(ticketStep),
          ...notices.slice(0, 3).map(noticeStep),
        ],
      );
    }
    const apartments = data[0]?.items || [],
      summary = data[1] || {},
      monthly = (data[2]?.items || []).map((x) => ({ ...x, invoice_type: 'monthly' })),
      semi = (data[3]?.items || []).map((x) => ({ ...x, invoice_type: 'semiannual' })),
      notices = data[4]?.items || [],
      tickets = data[5]?.items || [],
      requests = data[6]?.items || [],
      report = data[7] || {};
    const bills = [...monthly, ...semi];
    state.data.apartments = apartments;
    state.data.invoices = bills;
    state.data.notices = notices;
    const occupied = apartments.filter((a) => a.status === 'occupied').length,
      percent = apartments.length ? Math.round((occupied / apartments.length) * 100) : 0,
      openTickets = tickets.filter((t) => t.status !== 'completed').length;
    const stats = admin()
      ? stat('Tổng số căn hộ', number(apartments.length), `${occupied} căn hộ đã có cư dân`, 'building') +
        stat('Đã thu thanh toán', money(summary.paid_amount), 'Tổng hóa đơn đã thanh toán', 'wallet', 'blue') +
        stat(
          'Công nợ hiện tại',
          money(summary.outstanding_amount),
          `${number(summary.overdue_count)} hóa đơn quá hạn`,
          'invoice',
          'orange',
        ) +
        stat('Yêu cầu đang mở', number(openTickets), 'Sửa chữa & bảo trì', 'wrench', 'purple')
      : stat('Cần thanh toán', money(summary.outstanding_amount), 'Tổng hóa đơn chưa thanh toán', 'wallet', 'orange') +
        stat(
          'Đã thanh toán',
          money(summary.paid_amount),
          `${number(summary.paid_count)} hóa đơn hoàn tất`,
          'check',
          'blue',
        ) +
        stat('Yêu cầu đang mở', number(openTickets), 'Phiếu sửa chữa của bạn', 'wrench', 'purple');
    const chart = admin()
      ? view`
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Doanh thu dịch vụ</h2>
              <p>Số tiền đã thu của các hóa đơn theo từng kỳ</p>
            </div>
            <span class="period-chip">Năm ${thisYear()}</span>
          </div>
          <div class="chart-wrap">${revenueChart(report.items || [])}<div class="chart-caption">Đã thu theo kỳ hóa đơn · Đơn vị: VNĐ</div>
          </div>
        </section>
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Tình trạng căn hộ</h2>
              <p>Không gian sống của cộng đồng</p>
            </div>
          </div>
          <div class="occupancy">
            <div class="donut" style="--percent:${percent}%">
          </div>
          <div class="donut-label">
            <strong>${percent}%</strong>
            <span>Tỷ lệ lấp đầy</span>
          </div>
        </div>
        <div class="occupancy-legend">
          <div>
            <span>
              <i>
              </i>Đã có cư dân</span>
            <strong>${occupied}</strong>
          </div>
          <div>
            <span>
              <i class="gray">
              </i>Còn trống</span>
            <strong>${apartments.length - occupied}</strong>
          </div>
        </div>
        </section>
      `
      : view`
        <section class="panel">
          <div class="panel-header">
            <h2>Không gian của bạn</h2>
          </div>
          <div class="panel-body">
            ${apartments.length
            ? apartments
                .map(
                  (a) =>
                    view`
              <div class="apartment-pill">
                <span>${icon('building')}</span>
                <h2>Căn hộ ${esc(a.code)}</h2>
              </div>
              <p class="muted" style="font-size:12px;margin:12px 0 18px">Tòa ${esc(a.block)} · Tầng ${esc(a.floor)} · ${a.area == null ? 'Diện tích chưa cập nhật' : `${esc(a.area)} m²`}</p>
              ${detail(
                      [
                        ['Hình thức', label(a.contract_type)],
                        ['Trạng thái', label(a.status)],
                        ['Bắt đầu', date(a.start_date)],
                        ['Kết thúc', date(a.end_date)],
                      ],
                    )}
              
            `,
                )
                .join('<hr class="detail-separator">')
            : empty(
                'Tài khoản chưa liên kết căn hộ',
                'Vui lòng liên hệ Ban quản lý để xác nhận liên kết tài khoản với căn hộ.',
              )}
            </div>
        </section>
      `;
    const unpaid = bills
      .filter((b) => b.status !== 'paid')
      .sort((a, b) => String(a.due_date).localeCompare(String(b.due_date)));
    const billsBlock = admin()
      ? ''
      : view`
        <section class="panel">
          <div class="panel-header">
            <div>
              <h2>Hóa đơn cần thanh toán</h2>
              <p>Những khoản phí đang chờ hoàn tất</p>
            </div>
            ${button('Xem tất cả', 'navigate', 'arrow', 'link', 'data-route="billing"')}
            </div>
          ${table(invoiceColumns(), unpaid.slice(0, 5), { count: false, emptyTitle: 'Không có hóa đơn chờ thanh toán', emptyDescription: 'Các khoản phí của bạn đã được cập nhật.' })}
          </section>
      `;
    const pendingRequests = requests.filter((r) => r.status === 'pending').length;
    const steps = admin()
      ? [
          ...(summary.overdue_count
            ? [
                {
                  warn: true,
                  when: 'Cần xử lý',
                  title: `${number(summary.overdue_count)} hóa đơn quá hạn`,
                  detail: `Tổng ${money(summary.overdue_amount)}`,
                  route: 'billing',
                },
              ]
            : []),
          ...(pendingRequests
            ? [
                {
                  warn: true,
                  when: 'Chờ xử lý',
                  title: `${number(pendingRequests)} đơn khiếu nại & đăng ký`,
                  route: 'complaints',
                },
              ]
            : []),
          ...(openTickets
            ? [{ when: 'Đang mở', title: `${number(openTickets)} phiếu sửa chữa & bảo trì`, route: 'maintenance' }]
            : []),
          ...notices.slice(0, 3).map(noticeStep),
        ]
      : [
          ...unpaid.slice(0, 2).map(billStep),
          ...requests
            .filter((r) => r.status === 'pending' || r.status === 'processing')
            .slice(0, 1)
            .map(requestStep),
          ...tickets
            .filter((t) => t.status !== 'completed')
            .slice(0, 1)
            .map(ticketStep),
          ...notices.slice(0, 2).map(noticeStep),
        ];
    return overviewBoard(
      top +
        warning +
        view`
          <div class="${admin() ? 'stats-grid grid grid-cols-2 gap-3 min-[1280px]:grid-cols-4 min-[1280px]:gap-5' : 'stats-grid maintenance-stats'}">${stats}</div>${admin() ? '' : overviewShortcuts()}<div class="${admin() ? 'dashboard-columns' : 'overview-stack'}">${chart}${billsBlock}</div>
        `,
      steps,
    );
  },
  async apartments() {
    const rows = await items('/api/apartments');
    state.data.apartments = rows;
    return (
      heading(
        'Quản lý căn hộ',
        'Theo dõi không gian sống, tình trạng sử dụng và hợp đồng.',
        button('Thêm căn hộ', 'apartment-create'),
      ) +
      view`
        <div class="stats-grid maintenance-stats">
          ${stat('Tổng căn hộ', number(rows.length), 'Toàn bộ các tòa nhà', 'building')}
          
          ${stat('Đã có cư dân', number(rows.filter((r) => r.status === 'occupied').length), 'Hợp đồng đang hiệu lực', 'people', 'blue')}
          
          ${stat('Căn hộ còn trống', number(rows.filter((r) => r.status !== 'occupied').length), 'Sẵn sàng đón cư dân', 'building', 'orange')}
          </div>
        <section class="panel">${toolbar('Tìm mã căn hộ, tòa, cư dân…', ['occupied', 'vacant'])}
          ${table(
        [
          [
            'Căn hộ',
            (r) =>
              view`
            <span class="apartment-pill">
              <span>${icon('building')}</span>
              <span class="primary-cell">${esc(r.code)}</span>
            </span>
          `,
          ],
          ['Vị trí', (r) => `Tòa ${esc(r.block)} · Tầng ${esc(r.floor)}`],
          ['Diện tích', (r) => (r.area == null ? 'Chưa cập nhật' : `${esc(r.area)} m²`)],
          ['Chủ sở hữu', (r) => esc(r.owner_name || 'Chưa có')],
          [
            'Cư dân hiện tại',
            (r) =>
              r.current_residents?.length
                ? r.current_residents.map((p) => `<span class="primary-cell">${esc(p.full_name)}</span>`).join('') +
                  `<span class="sub-cell">${esc(label(r.contract_type))}</span>`
                : '<span class="primary-cell">Chưa có cư dân</span>',
          ],
          [
            'Thời hạn còn lại',
            (r) =>
              r.remaining_days === null || r.remaining_days === undefined ? '—' : `${number(r.remaining_days)} ngày`,
          ],
          ['Trạng thái', (r) => badge(r.status)],
          ['', (r) => button('Chi tiết', 'apartment-detail', '', 'link', `data-id="${r.apartment_id}"`)],
        ],
        rows,
      )}
          </section>
      `
    );
  },
  async residents() {
    const tab = state.tab.residents || 'residents';
    const [residents, contracts, apartments, users] = await Promise.all([
      items('/api/residents'),
      items('/api/contracts'),
      items('/api/apartments'),
      items('/api/auth/users'),
    ]);
    Object.assign(state.data, { residents, contracts, apartments, users });
    const columns =
      tab === 'residents'
        ? [
            [
              'Cư dân',
              (r) =>
                `<span class="primary-cell">${esc(r.full_name)}</span><span class="sub-cell">Mã #${esc(r.resident_id)}</span>`,
            ],
            [
              'Căn hộ đang ở',
              (r) =>
                esc(
                  r.apartment_codes?.length
                    ? r.apartment_codes.join(', ')
                    : r.registered_apartment_code
                      ? `${r.registered_apartment_code} (đăng ký)`
                      : '—',
                ),
            ],
            ['Số điện thoại', (r) => esc(r.phone || '—')],
            ['CCCD / giấy tờ', (r) => esc(r.id_card || '—')],
            ['Quan hệ', (r) => esc(label(r.relation_type))],
            [
              'Trạng thái tài khoản',
              (r) => {
                if (!r.user_id) return '<span class="badge">Chưa liên kết</span>';
                const u = users.find((x) => x.user_id === r.user_id);
                return u ? badge(u.status) : badge('active');
              },
            ],
            [
              '',
              (r) =>
                button('Chi tiết', 'resident-detail', '', 'link', `data-id="${r.resident_id}"`) +
                button('Xác nhận căn hộ', 'resident-apartments', 'building', 'link', `data-id="${r.resident_id}"`),
            ],
          ]
        : [
            ['Hợp đồng', (r) => `<span class="primary-cell">#HD${esc(r.contract_id)}</span>`],
            ['Căn hộ', (r) => esc(apartmentCode(r.apartment_id))],
            [
              'Cư dân',
              (r) => esc(residents.find((p) => p.resident_id === r.resident_id)?.full_name || `#${r.resident_id}`),
            ],
            ['Hình thức', (r) => esc(label(r.contract_type))],
            ['Hiệu lực', (r) => `${esc(date(r.start_date))}<span class="sub-cell">Đến ${esc(date(r.end_date))}</span>`],
            ['Trạng thái', (r) => badge(r.effective_status || r.status)],
            ['', (r) => button('Cập nhật', 'contract-edit', '', 'link', `data-id="${r.contract_id}"`)],
          ];
    return (
      // Residents join by registering; management confirms their apartment instead of adding them.
      heading(
        'Cư dân & hợp đồng',
        'Hồ sơ cư dân, lịch sử sở hữu và thuê căn hộ.',
        tab === 'residents' ? '' : button('Tạo hợp đồng', 'contract-create'),
      ) +
      tabs('residents', [
        ['residents', 'Hồ sơ cư dân'],
        ['contracts', 'Hợp đồng & lịch sử'],
      ]) +
      view`
        <section class="panel">
          ${toolbar(tab === 'residents' ? 'Tìm tên, số điện thoại…' : 'Tìm mã hợp đồng, căn hộ, cư dân…')}
          ${table(columns, tab === 'residents' ? residents : contracts, tab === 'residents' ? {} : { search: (r) => `#HD${r.contract_id} HD${r.contract_id} ${apartmentCode(r.apartment_id)} ${r.full_name || residents.find((p) => p.resident_id === r.resident_id)?.full_name || ''}` })}</section>
      `
    );
  },
  async billing() {
    const tab = state.tab.billing || 'monthly';
    const [apartments, summary, monthlyInvoices, semiannualInvoices, paymentConfig, residentProfile] =
      await Promise.all([
        items('/api/apartments'),
        api('/api/billing/summary'),
        items('/api/billing/invoices/monthly'),
        items('/api/billing/invoices/semiannual'),
        api('/api/billing/payment-config').catch(() => null),
        resident() ? api('/api/residents/me').catch(() => null) : null,
      ]);
    state.data.apartments = apartments;
    state.data.paymentConfig = paymentConfig;
    if (residentProfile) state.data.personal = residentProfile;
    const awaitingApartment =
      resident() && Array.isArray(residentProfile?.apartment_ids) && !residentProfile.apartment_ids.length;
    const apartmentNotice = awaitingApartment
      ? view`
        <div class="info-box" id="billing-apartment-notice">
          ${residentProfile.registered_apartment_code ? `Bạn đã đăng ký căn hộ ${esc(residentProfile.registered_apartment_code)}, nhưng căn hộ chưa được Ban quản lý xác nhận liên kết với tài khoản.` : 'Tài khoản của bạn chưa được liên kết với căn hộ.'} Vui lòng liên hệ Ban quản lý để xác nhận thông tin cư trú và liên kết căn hộ. Hóa đơn sẽ hiển thị sau khi liên kết hợp lệ; số tiền chưa hiển thị không có nghĩa là đã thanh toán.</div>
      `
      : '';
    const allInvoices = [
      ...monthlyInvoices.map((x) => ({ ...x, invoice_type: 'monthly' })),
      ...semiannualInvoices.map((x) => ({ ...x, invoice_type: 'semiannual' })),
    ];
    const curMonth = today().slice(0, 7);
    const qNum = Math.floor(new Date().getMonth() / 3) + 1;
    const qMonths = [(qNum - 1) * 3 + 1, (qNum - 1) * 3 + 2, (qNum - 1) * 3 + 3].map(
      (m) => `${thisYear()}-${String(m).padStart(2, '0')}`,
    );
    const qSemi = `${thisYear()}-H${qNum <= 2 ? '1' : '2'}`;

    const monthInvoices = allInvoices.filter(
      (i) => i.period === curMonth || (i.due_date && i.due_date.startsWith(curMonth)),
    );
    const monthPaid = monthInvoices.filter((i) => i.status === 'paid');
    const monthUnpaid = monthInvoices.filter((i) => i.status !== 'paid');
    const quarterInvoices = allInvoices.filter(
      (i) =>
        qMonths.includes(i.period) ||
        (i.due_date && qMonths.some((m) => i.due_date.startsWith(m))) ||
        String(i.period).startsWith(qSemi),
    );

    let body;
    if (tab === 'payments') {
      const payments = await items('/api/billing/payments');
      state.data.payments = payments;
      body = table(
        [
          [
            'Giao dịch',
            (r) =>
              view`
                <span class="primary-cell">#TT${esc(r.payment_id)}</span>
                <span class="sub-cell">${esc(r.transaction_code || '—')}</span>
              `,
          ],
          ['Hóa đơn', (r) => `${esc(label(r.invoice_type))} · ${esc(periodText(r.period))}`],
          ['Căn hộ', (r) => esc(apartmentCode(r.apartment_id))],
          ['Số tiền', (r) => `<span class="money">${money(r.amount)}</span>`],
          [
            'Hình thức',
            (r) =>
              esc(
                String(r.transaction_code || '').startsWith('SEPAY-TEST-')
                  ? 'Chuyển khoản · SePay Test'
                  : label(r.payment_method),
              ),
          ],
          ['Thời gian thanh toán', (r) => esc(dateTime(r.paid_at))],
          [
            '',
            (r) =>
              button(
                'Tải biên nhận',
                'receipt',
                'download',
                'link',
                `data-id="${r.payment_id}" data-kind="${esc(r.invoice_type)}"`,
              ),
          ],
        ],
        payments,
        {
          search: (r) => `#TT${r.payment_id} TT${r.payment_id} ${r.transaction_code || ''} ${apartmentCode(r.apartment_id)}`,
        },
      );
    } else if (tab === 'bank-transactions' && billingManager()) {
      const transactions = await items('/api/billing/sepay/transactions');
      state.data.bankTransactions = transactions;
      const unresolved = transactions.filter((row) => Number(row.unallocated_amount) > 0 && !row.resolution);
      body =
        view`
          <div class="info-box" id="bank-issues-summary">
            ${unresolved.length ? `${number(unresolved.length)} khoản cần xử lý, tổng tiền chưa phân bổ ${money(unresolved.reduce((sum, row) => sum + Number(row.unallocated_amount || 0), 0))}.` : 'Chưa có khoản chuyển dư hoặc chưa xác định cần xử lý.'} Mỗi hóa đơn chỉ được ghi nhận đủ tiền một lần. Ghi chú xử lý không thực hiện chuyển tiền hay hoàn tiền.</div>
        ` +
        table(
          [
            [
              'Tham chiếu',
              (r) =>
                view`
                  <span class="primary-cell">${esc(r.bank_reference || r.reference || `#${r.transaction_id}`)}</span>
                  <span class="sub-cell">${esc(date(r.received_at))}</span>
                `,
            ],
            [
              'Hóa đơn',
              (r) => (r.invoice_id ? `${esc(label(r.invoice_type))} #${esc(r.invoice_id)}` : 'Chưa xác định'),
            ],
            ['Tiền nhận', (r) => money(r.amount)],
            ['Đã phân bổ', (r) => money(r.allocated_amount)],
            ['Còn cần xử lý', (r) => money(r.unallocated_amount)],
            ['Đối soát', (r) => `${badge(r.status)}${r.issue ? `<span class="sub-cell">${esc(r.issue)}</span>` : ''}`],
            [
              'Xử lý của BQL',
              (r) =>
                `${r.resolution ? view`
                  <span class="primary-cell">${esc(label(r.resolution))}</span>
                  <span class="sub-cell">${esc(r.resolution_note || '')}</span>
                ` : ''}${r.status !== 'matched' ? button(r.resolution ? 'Cập nhật ghi chú' : 'Ghi nhận xử lý', 'bank-transaction-resolve', 'edit', 'link', `data-id="${r.transaction_id}"`) : ''}`,
            ],
          ],
          transactions,
          { search: bankSearch },
        );
    } else {
      const rows = (tab === 'monthly' ? monthlyInvoices : semiannualInvoices).map((r) => ({ ...r, invoice_type: tab }));
      state.data.invoices = rows;
      body = table(invoiceColumns(), rows, {
        search: invoiceSearch,
        ...(awaitingApartment
          ? {
              emptyTitle: 'Chưa thể xem hóa đơn',
              emptyDescription:
                'Ban quản lý cần xác nhận căn hộ của bạn trước khi bạn có thể xem và thanh toán hóa đơn.',
            }
          : {}),
      });
    }
    const statCards =
      stat('Tổng hóa đơn (trong quý)', number(quarterInvoices.length), `Kỳ thu Quý ${qNum}/${thisYear()}`, 'invoice') +
      stat(
        'Đã thanh toán (trong tháng)',
        number(monthPaid.length),
        money(monthPaid.reduce((s, i) => s + Number(i.total_amount || 0), 0)),
        'wallet',
        'blue',
      ) +
      stat(
        'Chờ thanh toán (trong tháng)',
        number(monthUnpaid.length),
        money(monthUnpaid.reduce((s, i) => s + Number(i.total_amount || 0), 0)),
        'clock',
        'orange',
      ) +
      stat('Hóa đơn quá hạn', number(summary.overdue_count), money(summary.overdue_amount), 'invoice', 'purple');
    const residentPaymentNotice = !paymentConfig?.ready
      ? paymentConfig?.message ||
        'VietQR chưa sẵn sàng. Ban quản lý cần kết nối tài khoản SePay và ngân hàng nhận tiền.'
      : paymentConfig.environment === 'test'
        ? 'VietQR · SePay Test: kiểm thử bằng giao dịch thử trên SePay.'
        : '';
    const paymentNotice = billingManager()
      ? '<div class="info-box">Cư dân thanh toán trong tài khoản của mình. Ban quản lý và kỹ thuật viên lập hóa đơn, theo dõi trạng thái và chỉ ghi nhận thu khi đã nhận đủ tiền mặt hoặc chuyển khoản. Các khoản chuyển dư hoặc chuyển lặp được theo dõi tại mục Đối soát chuyển khoản.</div>'
      : residentPaymentNotice
        ? `<div class="info-box" id="payment-mode-notice">${esc(residentPaymentNotice)}</div>`
        : '';
    return (
      heading(
        billingTitle(),
        billingManager()
          ? 'Lập hóa đơn, theo dõi công nợ và kết quả thanh toán của cư dân.'
          : 'Minh bạch các khoản phí. Thuận tiện trong từng thanh toán.',
        billingManager() && ['monthly', 'semiannual'].includes(tab) ? button('Lập hóa đơn', 'invoice-create') : '',
      ) +
      apartmentNotice +
      (awaitingApartment
        ? ''
        : view`
          <div class="stats-grid grid grid-cols-2 gap-3 min-[1280px]:grid-cols-4 min-[1280px]:gap-5">${statCards}</div>
        `) +
      paymentNotice +
      tabs('billing', [
        ['monthly', 'Điện & nước hàng tháng'],
        ['semiannual', 'Dịch vụ 6 tháng'],
        ['payments', billingManager() ? 'Các khoản đã thu' : 'Lịch sử thanh toán'],
        ...(billingManager() ? [['bank-transactions', 'Đối soát chuyển khoản']] : []),
      ]) +
      view`
        <section class="panel">
          ${toolbar(tab === 'bank-transactions' ? 'Tìm tham chiếu, hóa đơn…' : tab === 'payments' ? 'Tìm mã giao dịch, căn hộ…' : 'Tìm mã hóa đơn, căn hộ…', ['payments', 'bank-transactions'].includes(tab) ? [] : ['unpaid', 'overdue', 'paid'])}
          ${body}</section>
      `
    );
  },
  async parking() {
    if (!admin() && state.tab.parking === 'guest') state.tab.parking = 'vehicles';
    if (state.tab.parking === 'summary') state.tab.parking = 'vehicles';
    const tab = state.tab.parking || (tech() ? 'guest' : 'vehicles');
    const [vehicles, apartments] = await Promise.all([
      tab === 'guest' ? Promise.resolve([]) : items('/api/parking/vehicles'),
      tab === 'guest' ? Promise.resolve([]) : items('/api/apartments'),
    ]);
    Object.assign(state.data, { vehicles, apartments });
    let body;
    if (tab === 'guest') {
      const rows = await items('/api/parking/guest-daily');
      state.data.guests = rows;
      body = table(
        [
          ['Ngày ghi nhận', (r) => `<span class="primary-cell">${esc(date(r.parking_date))}</span>`],
          ['Tổng tiền vé vãng lai', (r) => `<span class="money">${money(r.daily_revenue)}</span>`],
          ['Mã ghi nhận', (r) => `#${esc(r.record_id)}`],
          ['', (r) => button('Cập nhật', 'guest-edit', '', 'link', `data-id="${r.record_id}"`)],
        ],
        rows,
        { search: (r) => `${date(r.parking_date)} ${date(r.parking_date).replace(/\b0/g, '')} ${r.parking_date}` },
      );
    } else {
      body = table(
        [
          ['Biển số', (r) => `<span class="primary-cell">${esc(r.plate_number)}</span>`],
          ['Căn hộ', (r) => esc(apartmentCode(r.apartment_id))],
          ['Loại xe', (r) => esc(vehicleTypeLabel(r.vehicle_type))],
          ['Phí / tháng', (r) => `<span class="money">${money(r.monthly_fee)}</span>`],
          ['Ngày đăng ký', (r) => esc(date(r.registered_date))],
          [
            'Ngày hết hạn',
            (r) =>
              `${esc(date(r.minimum_end_date))}${r.registration_expired ? '<span class="sub-cell">Đã hết hạn · cần gia hạn mới gửi tiếp</span>' : ''}`,
          ],
          // A registration that ran out is no longer billed, so it is shown as expired, not active.
          ['Trạng thái', (r) => badge(r.registration_expired ? 'expired' : r.status)],
          ...(admin()
            ? [
                [
                  '',
                  (r) =>
                    button('Cập nhật', 'vehicle-edit', '', 'link', `data-id="${r.vehicle_id}"`) +
                    (r.status === 'active'
                      ? button('Gia hạn', 'vehicle-renew', '', 'link', `data-id="${r.vehicle_id}"`) +
                        button('Hóa đơn bổ sung', 'vehicle-supplement', '', 'link', `data-id="${r.vehicle_id}"`)
                      : ''),
                ],
              ]
            : []),
        ],
        vehicles,
        { search: (r) => r.plate_number || '', type: (r) => r.vehicle_type },
      );
    }
    const parkingTabs = admin()
      ? tabs('parking', [
          ['vehicles', 'Phương tiện đăng ký'],
          ['guest', 'Vé vãng lai'],
        ])
      : '';
    return (
      heading(
        'Quản lý gửi xe',
        '',
        tab === 'guest'
          ? button('Ghi nhận doanh thu', 'guest-create')
          : admin()
            ? button('Đăng ký phương tiện', 'vehicle-create')
            : resident()
              ? button('Gửi đơn đăng ký', 'parking-request')
              : '',
      ) +
      parkingTabs +
      view`
        <section class="panel">
          ${tab === 'guest'
          ? toolbar('Tìm theo ngày (VD: 09/11/2026)…')
          : toolbar(
              'Tìm theo biển số…',
              [],
              parkingTypes.map(([value]) => [value, vehicleTypeLabel(value)]),
            )}
          ${body}</section>
      `
    );
  },
  async maintenance() {
    const [tickets, apartments, profile] = await Promise.all([
      items('/api/maintenance/tickets'),
      items('/api/apartments').catch(() => state.data.apartments || []),
      resident() ? api('/api/residents/me').catch(() => state.data.personal || null) : null,
    ]);
    state.data.tickets = tickets;
    state.data.apartments = apartments;
    if (profile) state.data.personal = profile;
    const unlinked = resident() && !(profile?.apartment_ids || []).length;
    const linkNotice = unlinked
      ? view`
        <div class="info-box" id="maintenance-apartment-notice">
          ${profile?.registered_apartment_code ? `Tài khoản chưa liên kết căn hộ: căn hộ ${esc(profile.registered_apartment_code)} bạn đăng ký đang chờ Ban quản lý xác nhận.` : 'Tài khoản chưa liên kết căn hộ.'} Bạn có thể tạo yêu cầu sửa chữa, bảo trì sau khi Ban quản lý xác nhận liên kết căn hộ.</div>
      `
      : '';
    return (
      heading(
        'Sửa chữa & bảo trì',
        'Tiếp nhận yêu cầu, theo dõi tiến độ và chăm sóc vận hành.',
        !tech() && !unlinked ? button('Tạo yêu cầu', 'ticket-create') : '',
      ) +
      linkNotice +
      view`
        <div class="stats-grid maintenance-stats">
          ${stat('Chờ xử lý', number(tickets.filter((t) => t.status === 'pending').length), 'Yêu cầu mới tiếp nhận', 'clock', 'orange')}
          
          ${stat('Đang thực hiện', number(tickets.filter((t) => t.status === 'in_progress').length), 'Kỹ thuật đang xử lý', 'wrench', 'blue')}
          
          ${stat('Đã hoàn thành', number(tickets.filter((t) => t.status === 'completed').length), 'Các phiếu đã đóng', 'check')}
          </div>
        <section class="panel">
          ${toolbar('Tìm mã phiếu, căn hộ hoặc nội dung mô tả…', ['pending', 'in_progress', 'completed'])}
          
          ${table([['Yêu cầu', (r) => view`
            <span class="primary-cell">#${esc(r.ticket_id)} · ${esc(label(r.type))}</span>
            <span class="sub-cell">${esc(r.description?.slice(0, 75))}</span>
          `], ['Căn hộ', (r) => esc(ticketApartment(r))], ['Phụ trách', (r) => esc(r.technician_name || 'Chưa phân công')], ...(resident() ? [] : [['Ưu tiên', (r) => badge(r.priority)]]), ['Trạng thái', (r) => badge(r.status)], ['Ngày tạo', (r) => esc(date(r.created_at))], ['', (r) => button(tech() || admin() ? 'Cập nhật' : 'Chi tiết', 'ticket-edit', '', 'link', `data-id="${r.ticket_id}"`)]], tickets, { search: (r) => `#${r.ticket_id} ${r.ticket_id} ${ticketApartment(r)} ${r.description || ''}` })}
          </section>
      `
    );
  },
  async services() {
    const rows = await items('/api/billing/services');
    const overdue = rows.filter((r) => r.status === 'overdue');
    return (
      heading('Quản lý dịch vụ', 'Theo dõi hóa đơn quá hạn, cắt và cấp lại dịch vụ cho căn hộ.') +
      view`
        <div class="stats-grid maintenance-stats">
          ${stat('Hóa đơn quá hạn', number(overdue.length), 'Có thể cắt dịch vụ', 'invoice', 'orange')}

          ${stat('Đang cắt dịch vụ', number(overdue.filter((r) => r.services.some((s) => s.status === 'cut')).length), 'Hóa đơn chưa thanh toán', 'power', 'purple')}

          ${stat('Cần cấp lại', number(rows.length - overdue.length), 'Cư dân đã thanh toán', 'check', 'blue')}
          </div>
        <section class="panel">
          ${toolbar('Tìm mã hóa đơn, căn hộ…', ['overdue', 'paid'])}
          ${table(
        [
          [
            'Hóa đơn',
            (r) => view`
              <span class="primary-cell">${esc(invoiceCode(r.invoice_type, r.invoice_id))}</span>
              <span class="sub-cell">${esc(label(r.invoice_type))} · ${esc(periodText(r.period))}</span>
            `,
          ],
          ['Căn hộ', (r) => esc(r.apartment_code || '—')],
          ['Số tiền', (r) => `<span class="money">${money(r.total_amount)}</span>`],
          ['Hạn thanh toán', (r) => esc(date(r.due_date))],
          ['Trạng thái', (r) => badge(r.status)],
          ['Dịch vụ', (r) => `<div class="service-actions">${r.services.map((s) => serviceControl(r, s)).join('')}</div>`],
        ],
        rows,
        { search: invoiceSearch, emptyTitle: 'Chưa có hóa đơn cần xử lý', emptyDescription: 'Hóa đơn quá hạn sẽ xuất hiện tại đây.' },
      )}
          </section>
      `
    );
  },
  async notifications() {
    const [notices, apartments] = await Promise.all([
      items('/api/notifications'),
      items('/api/apartments').catch(() => state.data.apartments || []),
    ]);
    state.data.notices = notices;
    state.data.apartments = apartments;
    const filter = state.noticeFilter || 'all';
    const displayed = filter === 'all' ? notices : notices.filter((n) => n.type === filter);
    const filterTabs = view`
      <div class="tabs" role="tablist" style="margin-bottom:20px">
        <button class="tab ${filter === 'all' ? 'active' : ''}" data-action="notice-filter" data-filter="all">Tất cả (${notices.length})</button>
      <button class="tab ${filter === 'general' ? 'active' : ''}" data-action="notice-filter" data-filter="general">Thông báo chung (${notices.filter((n) => n.type === 'general').length})</button>
      <button class="tab ${filter === 'private' ? 'active' : ''}" data-action="notice-filter" data-filter="private">Thông báo riêng (${notices.filter((n) => n.type === 'private').length})</button>
      </div>
    `;
    const cards = displayed
      .map(
        (n) =>
          view`
            <article class="panel notice-card clickable ${n.is_read ? 'read-mark' : ''}" data-action="notice-detail" data-id="${n.notification_id}">
            <div class="notification-tag">
              <span class="badge ${n.type === 'private' ? 'purple' : 'green'}">${esc(label(n.type))}</span>
            ${!n.is_read ? '<span class="live-dot" title="Chưa đọc" style="background:var(--red)"></span>' : ''}
            </div>
            <h3 style="margin:14px 0 10px">${esc(n.title)}</h3>
            <footer>
              <span>${esc(dateTime(n.created_at))}
                ${n.related_apartment_id ? ` · Căn hộ ${esc(n.related_apartment_code || apartmentCode(n.related_apartment_id))}` : n.target_apartment_id ? ` · Căn hộ ${esc(apartmentCode(n.target_apartment_id))}` : ''}
                </span>
              ${!n.is_read ? '<span style="color:var(--red);font-weight:600;font-size:11px">Chưa đọc</span>' : '<span class="muted" style="font-size:11px">Đã đọc</span>'}
              </footer>
            </article>
          `,
      )
      .join('');
    return (
      heading('Bảng tin cộng đồng', '', admin() ? button('Soạn thông báo', 'notice-create') : '') +
      pageSpotlight('notifications') +
      view`
        <div class="notification-action">
          ${AnCuPush.active() ? button('Tắt thông báo trình duyệt', 'push-disable', 'bell', 'secondary') : button('Bật thông báo trình duyệt', 'push-enable', 'bell', 'secondary')}
          </div>${filterTabs}
        ${displayed.length ? `<div class="card-list">${cards}</div>` : `<section class="panel">${empty('Chưa có thông báo', 'Không tìm thấy thông báo trong mục này.')}</section>`}
        
      `
    );
  },
  async complaints() {
    const rows = await items('/api/complaints');
    state.data.complaints = rows;
    const response = (r) =>
      r.response
        ? view`
          <span class="response-cell link" data-action="complaint-edit" data-id="${esc(r.complaint_id)}" title="Bấm để xem đầy đủ">${esc(r.response)}</span>
        `
        : '<span class="muted">Chưa có phản hồi</span>';
    return (
      heading(
        'Khiếu nại & đăng ký',
        'Lắng nghe ý kiến. Đồng hành cùng cư dân.',
        resident() ? button('Gửi yêu cầu', 'complaint-create') : '',
      ) +
      view`
        <section class="panel">
          ${toolbar('Tìm mã yêu cầu (VD: YC12) hoặc nội dung…', ['pending', 'processing', 'resolved', 'rejected', 'cancelled'])}
          
          ${table([['Mã yêu cầu', (r) => view`
            <span class="primary-cell">#YC${esc(r.complaint_id)}</span>
            <span class="sub-cell">${esc(label(r.type))}</span>
          `], ...(admin() ? [['Người gửi', (r) => esc(r.resident_name || `Cư dân #${r.resident_id}`)]] : []), ['Nội dung', (r) => view`
            <span class="primary-cell">${esc(r.category)}</span>
            <span class="sub-cell">${esc(r.content?.slice(0, 75))}${r.content?.length > 75 ? '…' : ''}</span>
            ${r.attachments?.length ? `<span class="sub-cell">${number(r.attachments.length)} tài liệu đính kèm</span>` : ''}
            
          `], ['Ngày tạo', (r) => esc(dateTime(r.created_at))], ['Trạng thái', (r) => badge(r.status)], ['Phản hồi của Ban quản lý', response], ['', (r) => button(admin() && r.status !== 'cancelled' ? (r.response ? 'Sửa phản hồi' : 'Phản hồi') : 'Chi tiết', 'complaint-edit', '', 'link', `data-id="${r.complaint_id}"`)]], rows, { search: (r) => `#YC${r.complaint_id} YC${r.complaint_id} ${r.complaint_id} ${r.category || ''} ${r.content || ''}` })}
          </section>
      `
    );
  },
  async reports() {
    const seq = state.sequence,
      year = state.reportYear || thisYear(),
      group = state.reportGroup || 'month';
    const [report, requests] = await Promise.all([
      api(`/api/billing/reports?year=${year}&group=${group}`),
      // Revenue stays readable if the complaint service is unavailable.
      api(`/api/complaints/summary?year=${year}&group=${group}`).catch(() => null),
    ]);
    const requestsByPeriod = Object.fromEntries((requests?.items || []).map((r) => [r.period, r]));
    if (seq === state.sequence) state.data.report = { ...report, year, requestsByPeriod };
    const total = report.totals || {};
    const requestTotal = requests?.totals || {};
    return (
      heading(
        'Báo cáo & thống kê',
        'Dữ liệu thu phí giúp bạn đưa ra quyết định rõ ràng.',
        button('Xuất CSV', 'report-export', 'download', 'secondary'),
      ) +
      view`
        <div class="stats-grid maintenance-stats">
          ${stat('Tổng doanh thu', money(total.revenue_amount), 'Hóa đơn đã thu và vé vãng lai', 'chart', 'blue')}

          ${stat('Tổng phát hành', money(total.billed_amount), `${number(total.invoice_count)} hóa đơn`, 'invoice', 'blue')}

          ${stat('Hóa đơn đã thu', money(total.collected_amount), `${number(total.paid_count)} hóa đơn đã thanh toán`, 'wallet')}

          ${stat('Công nợ còn lại', money(total.outstanding_amount), 'Trong năm được chọn', 'clock', 'orange')}

          ${stat('Thu điện nước', money(total.monthly_collected_amount), 'Hóa đơn hàng tháng', 'wallet', 'blue')}

          ${stat('Thu dịch vụ 6 tháng', money(total.semiannual_collected_amount), 'Dịch vụ chung và gửi xe', 'wallet')}

          ${stat('Thu vé vãng lai', money(total.guest_amount), 'Theo ngày ghi nhận', 'car')}

          ${stat('Khiếu nại', number(requestTotal.complaint_count), `${number(requestTotal.registration_count)} đơn đăng ký · ${number(requestTotal.pending_count)} chờ xử lý`, 'message', 'purple')}
          </div>
        <section class="panel">
          <div class="toolbar">
            <h2>Doanh thu theo kỳ</h2>
            <div class="filter-group">
              <select id="report-year" aria-label="Chọn năm">
                ${Array.from(
        { length: 8 },
        (_, i) => thisYear() - i,
      )
        .map((y) => `<option value="${y}" ${y === Number(year) ? 'selected' : ''}>Năm ${y}</option>`)
        .join(
          '',
        )}
                </select>
              <select id="report-group" aria-label="Nhóm báo cáo">
                <option value="month" ${group === 'month' ? 'selected' : ''}>Theo tháng</option>
              <option value="quarter" ${group === 'quarter' ? 'selected' : ''}>Theo quý</option>
          </select>
        </div>
        </div>
        <div class="chart-wrap report-chart">${revenueChart(
          (report.items || []).map((r) => ({ ...r, collected_amount: r.revenue_amount })),
          280,
        )}<div class="chart-caption">Tổng doanh thu theo kỳ: hóa đơn đã thu và vé vãng lai · Đơn vị: VNĐ</div></div>
        ${table(
        [
          ['Kỳ báo cáo', (r) => `<span class="primary-cell">${esc(r.period)}</span>`],
          ['Tổng doanh thu', (r) => `<span class="money">${money(r.revenue_amount)}</span>`],
          ['Đã phát hành', (r) => money(r.billed_amount)],
          ['Hóa đơn đã thu', (r) => money(r.collected_amount)],
          ['Điện nước đã thu', (r) => money(r.monthly_collected_amount)],
          ['6 tháng đã thu', (r) => money(r.semiannual_collected_amount)],
          ['Vé vãng lai', (r) => money(r.guest_amount)],
          ['Còn phải thu', (r) => money(r.outstanding_amount)],
          ['Hóa đơn đã thanh toán', (r) => `${number(r.paid_count)} / ${number(r.invoice_count)}`],
          ['Khiếu nại', (r) => number(requestsByPeriod[r.period]?.complaint_count)],
        ],
        report.items || [],
      )}
        </section>
      `
    );
  },
  async users() {
    const tab = state.tab.users || 'users';
    const [users, technicians] = await Promise.all([items('/api/auth/users'), items('/api/maintenance/technicians')]);
    Object.assign(state.data, { users, technicians });
    return (
      heading(
        'Nhân sự & tài khoản',
        'Phân quyền truy cập và quản lý đội ngũ kỹ thuật.',
      ) +
      tabs('users', [
        ['users', 'Tài khoản hệ thống'],
        ['technicians', 'Nhân sự kỹ thuật'],
      ]) +
      view`
        <section class="panel">${toolbar('Tìm tên, tài khoản…')}
          ${tab === 'users'
          ? table(
              [
                [
                  'Tài khoản',
                  (r) =>
                    `<span class="primary-cell">${esc(r.username)}</span><span class="sub-cell">#${r.user_id}</span>`,
                ],
                [
                  'Vai trò',
                  (r) =>
                    view`
            <span class="badge ${r.role === 'admin' ? 'purple' : r.role === 'technician' ? 'blue' : 'green'}">${esc(roleNames[r.role] || r.role)}</span>
          `,
                ],
                ['Email', (r) => esc(r.email || '—')],
                ['Trạng thái', (r) => badge(r.status)],
                ['Ngày tạo', (r) => esc(date(r.created_at))],
                ['', (r) => (r.user_id === state.user.user_id ? '' : button('Cập nhật', 'user-edit', '', 'link', `data-id="${r.user_id}"`))],
              ],
              users,
            )
          : table(
              [
                [
                  'Kỹ thuật viên',
                  (r) =>
                    `<span class="primary-cell">${esc(r.full_name)}</span><span class="sub-cell">#${r.technician_id}</span>`,
                ],
                ['Chuyên môn', (r) => esc(r.specialty === 'general' ? 'Kỹ thuật tổng hợp' : label(r.specialty))],
                ['Tài khoản', (r) => esc(users.find((u) => u.user_id === r.user_id)?.username || `#${r.user_id}`)],
                ['Công việc đang mở', (r) => number(r.open_tickets)],
                ['', (r) => button('Cập nhật', 'technician-edit', '', 'link', `data-id="${r.technician_id}"`)],
              ],
              technicians,
            )}
          </section>
      `
    );
  },
  async chatbot() {
    const tab = state.tab.chatbot || 'chat';
    const top =
      heading(
        'Trợ lý cư dân',
        'Tra cứu thông tin từ kho kiến thức chính thức của chung cư.',
        admin() && tab !== 'chat'
          ? button(tab === 'faqs' ? 'Thêm chính sách' : 'Thêm tiện ích', tab === 'faqs' ? 'faq-create' : 'location-create')
          : '',
      ) +
      tabs('chatbot', [
        ['chat', 'Trò chuyện'],
        ['faqs', 'Chính sách & câu hỏi'],
        ['locations', 'Vị trí tiện ích'],
      ]);
    if (tab === 'faqs') {
      const faqs = await items('/api/chatbot/faqs');
      state.data.faqs = faqs;
      return (
        top +
        (faqs.length
          ? view`
            <div class="grid-two">
              ${faqs.map((f) => view`
                <article class="panel notice-card">
                  <span class="inline-meta">${icon('message')}${esc(f.category || 'Thông tin chung')}</span>
                  <h3>${esc(f.question)}</h3>
                  <p>${esc(f.answer)}</p>
                  ${admin() ? `<footer>${button('Chỉnh sửa', 'faq-edit', 'edit', 'link', `data-id="${f.faq_id}"`)}${button('Xóa', 'faq-delete', '', 'link', `data-id="${f.faq_id}"`)}</footer>` : ''}
                  </article>
              `).join('')}
              </div>
          `
          : view`
            <section class="panel">
              ${empty('Chưa có nội dung chính sách', 'Ban quản lý sẽ cập nhật kho kiến thức tại đây.')}
              </section>
          `)
      );
    }
    if (tab === 'locations') {
      const locations = await items('/api/chatbot/locations');
      state.data.locations = locations;
      return (
        top +
        (locations.length
          ? view`
            <div class="card-list">
              ${locations.map((l) => view`
                <article class="panel notice-card">
                  <div class="notice-symbol">${icon('location')}</div>
                  <h3>${esc(l.name)}</h3>
                  <div class="inline-meta">Tòa ${esc(l.block || '—')} · Tầng ${esc(l.floor || '—')}</div>
                  <p style="margin-top:12px">${esc(l.description)}</p>
                  ${admin() ? `<footer>${button('Chỉnh sửa', 'location-edit', 'edit', 'link', `data-id="${l.location_id}"`)}</footer>` : ''}
                  </article>
              `).join('')}
              </div>
          `
          : view`
            <section class="panel">
              ${empty('Chưa có thông tin tiện ích', 'Vị trí và chỉ dẫn tiện ích sẽ được cập nhật tại đây.')}
              </section>
          `)
      );
    }
    const suggestions = await items('/api/chatbot/suggestions').catch(() => []);
    if (!state.chat.length)
      state.chat.push({
        role: 'bot',
        text: 'Xin chào! Tôi là trợ lý An Cư. Tôi có thể giúp bạn tra cứu chính sách, nội quy và vị trí tiện ích của chung cư. Bạn cần tìm thông tin gì?',
      });
    return (
      top +
      view`
        <section class="panel chat-container">
          <div class="panel-header">
            <div class="apartment-pill">
              <span>${icon('bot')}</span>
              <div>
                <h2>Trợ lý An Cư</h2>
                <p>Giải đáp chính sách & tiện ích</p>
              </div>
            </div>
            <span class="badge green">Sẵn sàng hỗ trợ</span>
          </div>
          <div id="chat-messages" class="chat-window" role="log" aria-live="polite">${state.chat.map(chatMessage).join('')}</div>
          <div class="chat-suggestions">
            ${suggestions.map((q) => `<button data-action="chat-suggest" data-question="${esc(q)}">${esc(q)}</button>`).join('')}
            </div>
          <form id="chat-form" class="chat-compose">
            <input name="question" aria-label="Câu hỏi cho trợ lý" placeholder="Nhập điều bạn muốn hỏi…" required maxlength="1500" autocomplete="off">
            <button class="button primary" type="submit" aria-label="Gửi câu hỏi">${icon('send')} Gửi</button>
          </form>
        </section>
      `
    );
  },
};
function ticketApartment(r) {
  return r.apartment_id == null ? r.location || 'Khu vực chung' : r.apartment_code || apartmentCode(r.apartment_id);
}
function serviceControl(invoice, service) {
  const name = label(service.service).toLowerCase();
  const attrs = `data-id="${invoice.invoice_id}" data-kind="${invoice.invoice_type}" data-service="${service.service}"`;
  if (service.status === 'restored') return `<span class="badge green">Đã cấp lại ${esc(name)}</span>`;
  if (service.status === 'cut')
    return invoice.status === 'paid'
      ? button(`Cấp lại ${name}`, 'service-restore', 'refresh', 'link', attrs)
      : `<span class="badge red">Đã cắt ${esc(name)}</span>`;
  return invoice.status === 'overdue' ? button(`Cắt ${name}`, 'service-cut', 'power', 'link', attrs) : '';
}
function serviceStatusText(invoice, service) {
  if (service.status === 'restored') return `Đã cấp lại lúc ${dateTime(service.restored_at)}`;
  if (service.status === 'cut')
    return invoice.status === 'paid' ? 'Chưa cấp lại' : `Đã cắt lúc ${dateTime(service.cut_at)}`;
  return invoice.status === 'paid' ? 'Không bị cắt' : 'Chưa cắt';
}
function quick(text, route, glyph) {
  return `<button class="quick-action" data-action="navigate" data-route="${route}">${icon(glyph)}${text}</button>`;
}
const billStep = (b) => ({
  warn: b.status === 'overdue',
  when: b.status === 'overdue' ? 'Quá hạn' : `Hạn ${date(b.due_date)}`,
  title: `Thanh toán ${invoiceCode(b.invoice_type, b.invoice_id)}`,
  detail: money(b.total_amount),
  route: 'billing',
});
const ticketStep = (t) => ({
  warn: t.status === 'pending',
  when: label(t.status),
  title: `Phiếu #${t.ticket_id} · ${label(t.type)}`,
  detail: t.description,
  route: 'maintenance',
});
const requestStep = (r) => ({
  warn: r.status === 'pending',
  when: label(r.status),
  title: label(r.type),
  detail: r.content,
  route: 'complaints',
});
const noticeStep = (n) => ({ when: date(n.created_at), title: n.title, detail: n.content, route: 'notifications' });
function todayPanel(steps) {
  const day = new Intl.DateTimeFormat('vi-VN', { weekday: 'long', day: 'numeric', month: 'numeric' }).format(
    new Date(),
  );
  const rows = steps
    .map(
      (s) =>
        view`
          <li>
            <a class="today-step${s.warn ? ' warn' : ''}" href="#${s.route}">
            <small>${esc(s.when)}</small>
            <strong>${esc(s.title)}</strong>${s.detail ? `<span>${esc(s.detail)}</span>` : ''}</a>
          </li>
        `,
    )
    .join('');
  return view`
    <aside class="today-panel" aria-labelledby="today-title">
      <div class="today-head">
        <h2 id="today-title">Hôm nay</h2>
        <span>${esc(day)}</span>
      </div>
      ${rows ? `<ol class="today-list">${rows}</ol>` : '<p class="today-empty">Hôm nay chưa có thông báo nào</p>'}
      </aside>
  `;
}
function overviewBoard(main, steps) {
  return `<div class="overview-board"><div class="overview-main">${main}</div>${todayPanel(steps)}</div>`;
}
function chatMessage(message) {
  return view`
    <div class="chat-message ${message.role === 'user' ? 'user' : 'bot'}">${esc(message.text)}${message.source ? `<small>Nguồn: ${esc(message.source)}</small>` : ''}</div>
  `;
}

Object.assign(statusLabels, { ownership: 'Sở hữu', rental: 'Thuê', locked: 'Đã khóa' });

async function apartmentForm(id) {
  const row = id ? state.data.apartments.find((r) => r.apartment_id === Number(id)) : {};
  formModal(
    id ? 'Cập nhật căn hộ' : 'Thêm căn hộ',
    field('code', 'Mã căn hộ', 'text', row.code || '', 'required maxlength="30" placeholder="Ví dụ: A101"') +
      field('block', 'Tòa nhà', 'text', row.block || '', 'required maxlength="30"') +
      field(
        'floor',
        'Tầng',
        'text',
        row.floor ?? '',
        'required inputmode="numeric" pattern="[1-9][0-9]{0,2}" maxlength="3" title="Tầng là số nguyên dương, ví dụ 12"',
      ) +
      field('area', 'Diện tích (m²)', 'number', row.area ?? '', 'required min="0.01" max="10000" step="0.01"'),
    (data) => saved(id ? patch(`/api/apartments/${id}`, data) : post('/api/apartments', data)),
  );
}
async function apartmentDetail(id) {
  const [row, allContracts] = await Promise.all([api(`/api/apartments/${id}`), items('/api/contracts')]);
  const contracts = allContracts.filter((c) => Number(c.apartment_id) === Number(id));
  const body = detail([
    ['Căn hộ', row.code],
    ['Vị trí', `Tòa ${row.block} · Tầng ${row.floor}`],
    ['Diện tích', row.area == null ? 'Chưa cập nhật' : `${row.area} m²`],
    ['Trạng thái', label(row.status)],
    ['Chủ sở hữu', row.owner_name || 'Chưa có'],
    ['SĐT chủ sở hữu', row.owner_phone || 'Chưa có'],
    ['Cư dân hiện tại', row.current_resident || 'Chưa có'],
    ['Hình thức', label(row.contract_type)],
    ['Bắt đầu', date(row.start_date)],
    ['Kết thúc', date(row.end_date)],
    ['Thời gian còn lại', row.remaining_days != null ? `${number(row.remaining_days)} ngày` : 'Không xác định'],
  ]);
  openModal(
    `Căn hộ ${row.code}`,
    view`
      <div class="modal-body">${body}<hr class="detail-separator">
        <h3 class="detail-title">Lịch sử sở hữu / thuê</h3>
        ${table(
      [
        ['Cư dân', (r) => esc(r.full_name || `#${r.resident_id}`)],
        ['Loại', (r) => esc(label(r.contract_type))],
        ['Thời hạn', (r) => `${esc(date(r.start_date))} → ${esc(date(r.end_date))}`],
        ['Trạng thái', (r) => badge(r.effective_status || r.status)],
      ],
      contracts,
      { count: false, emptyTitle: 'Chưa có hợp đồng' },
    )}
        </div>
    `,
    `<div class="modal-footer">${button('Đóng', 'close-modal', '', 'secondary')}${button('Cập nhật thông tin căn hộ', 'apartment-edit', 'edit', 'primary', `data-id="${id}"`)}</div>`,
  );
}
async function residentForm(id) {
  const [users, residents] = await Promise.all([items('/api/auth/users'), items('/api/residents')]);
  const row = residents.find((r) => r.resident_id === Number(id));
  const eligible = users.filter(
    (u) =>
      ['resident', 'technician', 'admin'].includes(u.role) &&
      (!residents.some((r) => r.user_id === u.user_id) || row.user_id === u.user_id),
  );
  formModal(
    'Cập nhật hồ sơ cư dân',
    field('full_name', 'Họ và tên', 'text', row.full_name || '', 'required maxlength="120"') +
      field(
        'registered_apartment_code',
        'Căn hộ đăng ký',
        'text',
        row.registered_apartment_code || '',
        'maxlength="30" placeholder="Ví dụ: A101"',
      ) +
      field('phone', 'Số điện thoại', 'tel', row.phone || '', 'maxlength="20"') +
      field('id_card', 'CCCD / giấy tờ định danh', 'text', row.id_card || '', 'maxlength="30"') +
      select(
        'relation_type',
        'Quan hệ',
        [
          ['owner', 'Chủ sở hữu'],
          ['tenant', 'Người thuê'],
        ],
        row.relation_type || 'tenant',
      ) +
      select(
        'user_id',
        'Liên kết tài khoản',
        eligible.map((u) => [u.user_id, `${u.username} (${roleNames[u.role] || u.role})`]),
        row.user_id || '',
        false,
      ),
    (data) => {
      if (!data.user_id) data.user_id = null;
      if ('registered_apartment_code' in data && !data.registered_apartment_code) data.registered_apartment_code = null;
      return saved(patch(`/api/residents/${id}`, data));
    },
    'Lưu hồ sơ',
    'Liên kết đúng tài khoản với hồ sơ cư dân. Sau đó xác nhận căn hộ hoặc lập hợp đồng để cư dân xem hóa đơn và sử dụng tiện ích của căn hộ.',
  );
}
async function residentDetail(id) {
  const [row, users] = await Promise.all([api(`/api/residents/${id}`), items('/api/auth/users')]);
  const account = users.find((u) => u.user_id === row.user_id);
  // After a lease ends, management locks the apartment's accounts here and reopens them in person.
  const accountAction =
    account?.status === 'locked'
      ? button('Mở khóa tài khoản', 'resident-unlock', 'refresh', 'secondary', `data-id="${id}"`)
      : account && row.lease_ended
        ? button('Khóa tài khoản căn hộ', 'resident-lock', 'shield', 'secondary', `data-id="${id}"`)
        : '';
  openModal(
    row.full_name,
    view`
      <div class="modal-body">
        ${detail([
      ['Mã cư dân', `#${row.resident_id}`],
      ['Tài khoản', row.user_id ? `#${row.user_id}` : 'Chưa liên kết'],
      ['Trạng thái tài khoản', account ? label(account.status) : 'Chưa liên kết'],
      ...(account?.status === 'locked' && account.lock_reason ? [['Lý do khóa', account.lock_reason]] : []),
      ['Họ và tên', row.full_name],
      ['Số điện thoại', row.phone],
      ['CCCD / giấy tờ', row.id_card],
      ['Quan hệ', label(row.relation_type)],
      ['Căn hộ đăng ký', row.registered_apartment_code || 'Chưa đăng ký'],
      [
        'Căn hộ đã xác nhận',
        row.apartment_codes?.join(', ') ||
          (row.apartment_ids || []).map(apartmentCode).join(', ') ||
          'Chưa xác nhận căn hộ',
      ],
    ])}
        </div>
    `,
    view`
      <div class="modal-footer">${button('Đóng', 'close-modal', '', 'secondary')}
        ${accountAction}
        ${button('Xác nhận căn hộ', 'resident-apartments', 'building', 'secondary', `data-id="${id}"`)}

        ${button('Cập nhật', 'resident-edit', 'edit', 'primary', `data-id="${id}"`)}
        </div>
    `,
  );
}
async function residentLock(id) {
  if (!admin()) throw new Error('Chỉ Ban quản lý được khóa tài khoản.');
  const row = await api(`/api/residents/${id}`);
  formModal(
    'Khóa tài khoản căn hộ',
    `<div class="field wide">${detail([
      ['Cư dân', row.full_name],
      ['Căn hộ', row.apartment_codes?.join(', ') || 'Chưa xác định'],
    ])}</div>`,
    () =>
      saved(
        post(`/api/residents/${id}/lock-apartment`),
        'Đã khóa các tài khoản của căn hộ. Căn hộ chuyển sang còn trống.',
      ),
    'Khóa tài khoản',
    'Hợp đồng thuê của căn hộ đã hết hạn và chưa gia hạn. Mọi tài khoản cư dân của căn hộ sẽ bị khóa và đăng xuất ngay; khi đăng nhập, họ thấy thông báo hợp đồng thuê đã quá hạn. Người còn hợp đồng đang hiệu lực với căn hộ, như chủ sở hữu, không bị khóa. Muốn mở lại, cư dân gặp trực tiếp Ban quản lý.',
  );
}
async function residentUnlock(id) {
  if (!admin()) throw new Error('Chỉ Ban quản lý được mở khóa tài khoản.');
  const row = await api(`/api/residents/${id}`);
  formModal(
    'Mở khóa tài khoản',
    `<div class="field wide">${detail([
      ['Cư dân', row.full_name],
      ['Căn hộ', row.apartment_codes?.join(', ') || 'Chưa xác định'],
    ])}</div>`,
    () => saved(post(`/api/residents/${id}/unlock`), 'Đã mở khóa tài khoản. Cư dân có thể đăng nhập lại.'),
    'Mở khóa',
    'Chỉ mở khóa sau khi cư dân đã gặp Ban quản lý, ví dụ đã gia hạn hợp đồng thuê. Liên kết căn hộ được giữ nguyên nên cư dân dùng lại được ngay.',
  );
}
async function residentApartments(id) {
  if (!admin()) throw new Error('Chỉ Ban quản lý được xác nhận căn hộ cho cư dân.');
  const [row, apartments] = await Promise.all([api(`/api/residents/${id}`), items('/api/apartments')]);
  const registered = String(row.registered_apartment_code || '')
    .trim()
    .toUpperCase();
  const selected = apartments.find((a) => String(a.code).toUpperCase() === registered)?.apartment_id || '';
  const confirmed = Array.isArray(row.verified_apartments) ? row.verified_apartments : [];
  const contracts = (row.contract_apartment_ids || []).map(
    (aid) => apartments.find((a) => Number(a.apartment_id) === Number(aid))?.code || `#${aid}`,
  );
  const confirmedList = table(
    [
      ['Căn hộ', (r) => esc(r.code || apartmentCode(r.apartment_id))],
      ['Ngày xác nhận', (r) => esc(date(r.confirmed_at))],
      [
        '',
        (r) =>
          button(
            'Gỡ xác nhận',
            'resident-apartment-remove',
            '',
            'link',
            `data-id="${id}" data-apartment="${esc(r.apartment_id)}"`,
          ),
      ],
    ],
    confirmed,
    {
      count: false,
      emptyTitle: 'Chưa có xác nhận riêng',
      emptyDescription: 'Bạn có thể xác nhận cư dân đang ở cùng căn hộ mà không cần tạo thêm hợp đồng.',
    },
  );
  formModal(
    `Xác nhận căn hộ · ${row.full_name}`,
    view`
      <div class="field wide">
        ${detail([
      ['Cư dân', row.full_name],
      ['Căn hộ đăng ký', row.registered_apartment_code || 'Chưa đăng ký'],
      ['Căn hộ theo hợp đồng đang hiệu lực', contracts.join(', ') || 'Chưa có'],
    ])}
        </div>
    ` +
      select('apartment_id', 'Căn hộ cần xác nhận', [['', 'Chọn căn hộ'], ...apartmentOptions(apartments)], selected) +
      view`
        <div class="field wide">
          <h3 class="detail-title">Các căn hộ được xác nhận riêng</h3>${confirmedList}<p class="muted" style="margin-top:12px">Gỡ xác nhận chỉ xóa liên kết được xác nhận riêng. Quyền truy cập từ hợp đồng đang hiệu lực vẫn được giữ.</p>
        </div>
      `,
    (data) =>
      saved(
        post(`/api/residents/${id}/apartments`, data),
        'Đã xác nhận căn hộ. Cư dân có thể đăng nhập lại hoặc tải lại trang để xem hóa đơn.',
      ),
    'Xác nhận căn hộ',
    'Chỉ xác nhận sau khi đã kiểm tra thông tin cư trú. Cư dân sẽ được xem hóa đơn, nhận thông báo và sử dụng tiện ích của căn hộ; thao tác này không tạo hoặc thay đổi hợp đồng.',
    'vertical',
  );
}
async function residentApartmentRemove(id, apartmentId) {
  if (!admin()) throw new Error('Chỉ Ban quản lý được gỡ xác nhận căn hộ cho cư dân.');
  const row = await api(`/api/residents/${id}`);
  const confirmed = row.verified_apartments?.find((a) => Number(a.apartment_id) === Number(apartmentId));
  if (!confirmed) throw new Error('Không tìm thấy liên kết căn hộ được xác nhận riêng.');
  formModal(
    'Gỡ xác nhận căn hộ',
    view`
      <div class="field wide">
        ${detail([
      ['Cư dân', row.full_name],
      ['Căn hộ', confirmed.code || apartmentCode(apartmentId)],
    ])}
        </div>
    `,
    () =>
      saved(
        api(`/api/residents/${id}/apartments/${encodeURIComponent(apartmentId)}`, { method: 'DELETE' }),
        'Đã gỡ xác nhận căn hộ.',
      ),
    'Gỡ xác nhận',
    'Cư dân sẽ không còn quyền truy cập từ liên kết này. Hợp đồng không bị thay đổi; nếu cư dân vẫn có hợp đồng đang hiệu lực với căn hộ, quyền truy cập theo hợp đồng vẫn còn.',
  );
}
async function contractForm(id) {
  const [apartments, residents] = await Promise.all([items('/api/apartments'), items('/api/residents')]);
  const row = id ? state.data.contracts.find((c) => c.contract_id === Number(id)) : {};
  const sameName = (a, b) => a.trim().toLowerCase() === b.trim().toLowerCase();
  // Names are not unique: people who share one are told apart by their record number.
  const residentChoice = (r) =>
    residents.filter((other) => sameName(other.full_name, r.full_name)).length > 1
      ? `${r.full_name} (#${r.resident_id})`
      : r.full_name;
  const current = row.resident_id ? residents.find((r) => r.resident_id === row.resident_id) : null;
  // Plain text: the name must belong to a resident who registered an account.
  const residentField = field(
    'resident_name',
    'Cư dân',
    'text',
    current ? residentChoice(current) : '',
    'required maxlength="120" placeholder="Nhập họ tên cư dân đã đăng ký" autocomplete="off"',
  );
  const statusField = id
    ? select(
        'status',
        'Trạng thái',
        [
          ['active', 'Đang hoạt động'],
          ['expired', 'Hết hạn'],
        ],
        row.status === 'expired' ? 'expired' : 'active',
      )
    : '';

  formModal(
    id ? 'Cập nhật hợp đồng' : 'Tạo hợp đồng',
    select('apartment_id', 'Căn hộ', apartmentOptions(apartments), row.apartment_id || '') +
      residentField +
      select(
        'contract_type',
        'Loại hợp đồng',
        [
          ['rental', 'Thuê căn hộ'],
          ['ownership', 'Sở hữu căn hộ'],
        ],
        row.contract_type || 'rental',
      ) +
      field('start_date', 'Ngày bắt đầu', 'date', row.start_date || today(), 'required') +
      field('end_date', 'Ngày kết thúc', 'date', row.end_date || '') +
      statusField,
    (data) => {
      if (data.contract_type === 'rental' && !data.end_date)
        throw new Error('Vui lòng nhập ngày kết thúc hợp đồng thuê.');
      if (data.end_date && data.end_date < data.start_date)
        throw new Error('Ngày kết thúc không được trước ngày bắt đầu.');
      if (!data.end_date) data.end_date = null;
      const typed = data.resident_name.trim(),
        tagged = typed.match(/\(#(\d+)\)$/);
      const candidates = tagged
        ? residents.filter((r) => r.resident_id === Number(tagged[1]))
        : residents.filter((r) => sameName(r.full_name, typed));
      if (tagged && !candidates.length) throw new Error(`Không có cư dân mã #${tagged[1]}.`);
      if (candidates.length > 1)
        throw new Error('Có nhiều cư dân trùng tên. Hãy nhập kèm mã hồ sơ, ví dụ: Nguyễn Văn A (#12).');
      if (!candidates.length)
        throw new Error(`Không tìm thấy cư dân "${typed}". Cư dân cần tự đăng ký tài khoản trước khi lập hợp đồng.`);
      data.resident_id = candidates[0].resident_id;
      delete data.resident_name;
      return saved(id ? patch(`/api/contracts/${id}`, data) : post('/api/contracts', data));
    },
    'Lưu hợp đồng',
    'Một căn hộ chỉ có một hợp đồng hoạt động trong cùng khoảng thời gian. Hợp đồng thuê cần có ngày kết thúc. Cư dân phải đã đăng ký tài khoản; nếu trùng tên, nhập kèm mã hồ sơ, ví dụ: Nguyễn Văn A (#12).',
  );
}
function utilityFields(row = {}) {
  return (
    field(
      'electricity_usage',
      'Điện tiêu thụ (kWh)',
      'number',
      row.electricity_usage ?? '',
      'required min="0" max="1000000" step="0.001"',
    ) +
    field(
      'electricity_unit_price',
      'Đơn giá điện (VNĐ/kWh)',
      'number',
      row.electricity_unit_price ?? '',
      'required min="1" max="1000000000" step="1"',
    ) +
    field(
      'water_usage',
      'Nước tiêu thụ (m³)',
      'number',
      row.water_usage ?? '',
      'required min="0" max="1000000" step="0.001"',
    ) +
    field(
      'water_unit_price',
      'Đơn giá nước (VNĐ/m³)',
      'number',
      row.water_unit_price ?? '',
      'required min="1" max="1000000000" step="1"',
    ) +
    '<div class="wide info-box" id="utility-preview" role="status" aria-live="polite"></div>'
  );
}
function updateUtilityPreview() {
  const preview = $('#utility-preview'),
    form = $('#modal-form');
  if (!preview || !form) return;
  const amounts = {};
  for (const utility of ['electricity', 'water']) {
    const usage = form.elements.namedItem(utility + '_usage'),
      price = form.elements.namedItem(utility + '_unit_price');
    if (!usage.value || !price.value || !usage.checkValidity() || !price.checkValidity()) {
      preview.textContent = 'Nhập lượng tiêu thụ và đơn giá để xem tiền điện, tiền nước và tổng hóa đơn.';
      return;
    }
    // Integer thousandths avoid 0.145 × 100 being rounded down by float error.
    const product = Math.round(Number(usage.value) * 1000) * Number(price.value);
    if (product / 1000 > 1000000000) {
      preview.textContent = 'Tiền mỗi khoản không được vượt quá 1 tỷ đồng.';
      return;
    }
    amounts[utility] = Math.floor((product + 500) / 1000);
  }
  preview.innerHTML = view`
    
    ${detail([
    ['Tiền điện', money(amounts.electricity)],
    ['Tiền nước', money(amounts.water)],
    ['Tổng hóa đơn', money(amounts.electricity + amounts.water)],
  ])}
    <p>Mỗi khoản được làm tròn đến đồng.</p>
  `;
}
async function invoiceForm() {
  const kind = state.tab.billing || 'monthly',
    apartments = state.data.apartments || (await items('/api/apartments'));
  const period = kind === 'monthly' ? today().slice(0, 7) : `${thisYear()}-H${new Date().getMonth() < 6 ? '1' : '2'}`;
  const nextDate = new Date();
  nextDate.setDate(nextDate.getDate() + 14);
  const due = nextDate.toLocaleDateString('en-CA');
  formModal(
    kind === 'monthly' ? 'Lập hóa đơn điện & nước' : 'Lập hóa đơn dịch vụ 6 tháng',
    select('apartment_id', 'Căn hộ', apartmentOptions(apartments)) +
      field(
        'period',
        'Kỳ thu',
        kind === 'monthly' ? 'month' : 'text',
        period,
        kind === 'monthly' ? 'required' : 'required pattern="[0-9]{4}-H[12]" placeholder="2026-H2"',
      ) +
      (kind === 'monthly'
        ? utilityFields()
        : field('service_fee', 'Phí dịch vụ chung (VNĐ)', 'number', '0', 'required min="0" step="1"') +
          field(
            'parking_fee',
            'Phí gửi xe (VNĐ, không bắt buộc)',
            'number',
            '',
            'min="0" step="1" placeholder="Tự tính theo kỳ nếu để trống"',
          )) +
      field('due_date', 'Hạn thanh toán', 'date', due, 'required'),
    (data) => saved(post(`/api/billing/invoices/${kind}`, data), 'Đã phát hành hóa đơn.'),
    'Phát hành hóa đơn',
    kind === 'semiannual'
      ? 'Nếu để trống phí gửi xe, hệ thống tính các tháng có đăng ký trong kỳ đã chọn và cộng phí làm thẻ lần đầu 100.000 VNĐ/xe trong kỳ có tháng đăng ký.'
      : 'Nhập lượng điện, nước đã dùng trong kỳ (chỉ số mới trừ chỉ số cũ) và đơn giá áp dụng. Thành tiền = lượng tiêu thụ × đơn giá.',
  );
  updateUtilityPreview();
}
function findInvoice(kind, id) {
  return state.data.invoices?.find((r) => r.invoice_type === kind && Number(r.invoice_id) === Number(id));
}
async function invoiceDetail(kind, id, updatedRow = null) {
  const version = modalVersion,
    user = state.user;
  const row = updatedRow || (await api(`/api/billing/invoices/${kind}/${id}`));
  if (modalVersion !== version || state.user !== user) return;
  if (!row) throw new Error('Không tìm thấy hóa đơn.');
  const paymentConfig = resident()
    ? state.data.paymentConfig || (await api('/api/billing/payment-config').catch(() => null))
    : null;
  if (modalVersion !== version || state.user !== user) return;
  row.invoice_type = kind;
  state.currentInvoice = row;
  if (resident()) state.data.paymentConfig = paymentConfig;
  const entries = [
    ['Mã hóa đơn', `#${kind === 'monthly' ? 'HD' : 'DV'}${String(id).padStart(4, '0')}`],
    ['Căn hộ', apartmentCode(row.apartment_id)],
    ['Kỳ thu', periodText(row.period)],
    ['Trạng thái', label(row.status)],
    ...(kind === 'monthly'
      ? [
          ['Tiền điện', money(row.electricity_fee)],
          ['Tiền nước', money(row.water_fee)],
        ]
      : [
          ['Phí dịch vụ', money(row.service_fee)],
          ['Phí gửi xe', money(row.parking_fee)],
        ]),
    ['Hạn thanh toán', date(row.due_date)],
    ['Tổng cần thanh toán', money(row.total_amount)],
    ['Thời gian lập hóa đơn', dateTime(row.created_at)],
    [
      'Thời gian thanh toán',
      row.paid_at ? dateTime(row.paid_at) : row.status === 'paid' ? 'Chưa ghi nhận' : 'Chưa thanh toán',
    ],
  ];
  if (row.status === 'overdue' || (row.services || []).some((s) => s.status !== 'active'))
    entries.push(...(row.services || []).map((s) => [`Dịch vụ ${label(s.service).toLowerCase()}`, serviceStatusText(row, s)]));
  if (kind === 'monthly' && row.electricity_usage != null)
    entries.splice(
      6,
      0,
      [
        'Cách tính tiền điện',
        `${number(row.electricity_usage)} kWh × ${money(row.electricity_unit_price)}/kWh = ${money(row.electricity_fee)}`,
        true,
      ],
      [
        'Cách tính tiền nước',
        `${number(row.water_usage)} m³ × ${money(row.water_unit_price)}/m³ = ${money(row.water_fee)}`,
        true,
      ],
    );
  const vehicles = row.vehicles || [];
  const vehicleTable = vehicles.length
    ? '<hr class="detail-separator"><h3 class="detail-title">Phương tiện gửi xe trong hóa đơn</h3>' +
      table(
        [
          [
            'Phương tiện',
            (v) => view`
              <span class="primary-cell">${esc(v.plate_number || '—')}</span>
              <span class="sub-cell">${esc(label(v.vehicle_type))}</span>
            `,
          ],
          ['Số tháng đăng ký', (v) => `${number(v.registration_months)} tháng`],
          ['Ngày đăng ký', (v) => esc(date(v.registered_date))],
          [
            'Ngày hết hạn',
            (v) =>
              `${esc(date(v.minimum_end_date))}${v.cancelled_date ? `<span class="sub-cell">Đã hủy từ ${esc(date(v.cancelled_date))}</span>` : ''}`,
          ],
          [
            'Tính phí kỳ này',
            (v) =>
              `${number(v.months)} tháng × ${money(v.monthly_fee)}${Number(v.card_fee) > 0 ? `<span class="sub-cell">Phí làm thẻ ${money(v.card_fee)}</span>` : ''}`,
          ],
        ],
        vehicles,
        { count: false },
      )
    : '';
  const unpaidActions = billingManager()
    ? button('Ghi nhận thu', 'invoice-cash', 'wallet', 'secondary', `data-id="${id}" data-kind="${kind}"`)
    : resident()
      ? button(
          'Thanh toán VietQR',
          'invoice-pay',
          'wallet',
          'primary',
          `data-id="${id}" data-kind="${kind}" ${paymentConfig?.ready ? '' : 'disabled title="Ban quản lý cần hoàn tất cấu hình SePay trước khi thanh toán."'}`,
        )
      : '';
  openModal(
    'Chi tiết hóa đơn',
    view`
      <div class="modal-body">${detail(entries)}${vehicleTable}
        ${row.status === 'overdue' ? view`
          <div class="info-box" style="margin-top:20px">
            ${billingManager() ? `Hóa đơn đã quá hạn. Vui lòng liên hệ cư dân để nhắc thanh toán.${tech() ? ' Cắt dịch vụ tại mục Quản lý dịch vụ.' : ''}` : 'Hóa đơn đã quá hạn. Vui lòng thanh toán hoặc liên hệ Ban quản lý để được hỗ trợ.'}
            </div>
        ` : ''}
        
        ${billingManager() && row.status === 'unpaid' ? view`
          <div style="margin-top:18px">
            ${button('Điều chỉnh số tiền / hạn thanh toán', 'invoice-edit', 'edit', 'link', `data-id="${id}" data-kind="${kind}"`)}
            </div>
        ` : ''}
        
        ${billingManager() && row.active_payment_status === 'awaiting_confirmation' ? view`
          <div class="info-box" style="margin-top:18px">Cư dân đã báo chuyển khoản, ngân hàng chưa xác nhận. Hóa đơn đang bị khóa để tránh thu trùng.<div style="margin-top:10px">
              ${button('Mở khóa phiên thanh toán', 'invoice-release', 'shield', 'link', `data-id="${id}" data-kind="${kind}"`)}
              </div>
          </div>
        ` : ''}
        </div>
    `,
    view`
      <div class="modal-footer">
        ${row.status !== 'paid' ? unpaidActions : button(billingManager() ? 'Xem khoản đã thu' : 'Lịch sử thanh toán', 'payment-history', 'download', 'primary')}
        ${button('Đóng', 'close-modal', '', 'secondary')}</div>
    `,
  );
  $('#modal').dataset.invoiceKind = kind;
  $('#modal').dataset.invoiceId = id;
  $('#modal .modal-body').insertAdjacentHTML(
    'beforeend',
    '<p class="muted" style="margin-top:18px">Thời gian theo giờ Việt Nam (UTC+7).</p>',
  );
}
function invoiceEdit(kind, id) {
  const row = state.currentInvoice || findInvoice(kind, id);
  const monthlyFields =
    row.electricity_usage != null
      ? utilityFields(row)
      : field('electricity_fee', 'Tiền điện (VNĐ)', 'number', row.electricity_fee, 'required min="0" step="1"') +
        field('water_fee', 'Tiền nước (VNĐ)', 'number', row.water_fee, 'required min="0" step="1"');
  formModal(
    'Điều chỉnh hóa đơn',
    (kind === 'monthly'
      ? monthlyFields
      : field('service_fee', 'Phí dịch vụ (VNĐ)', 'number', row.service_fee, 'required min="0" step="1"') +
        field('parking_fee', 'Phí gửi xe (VNĐ)', 'number', row.parking_fee, 'required min="0" step="1"')) +
      field('due_date', 'Hạn thanh toán', 'date', row.due_date, 'required'),
    (data) => saved(patch(`/api/billing/invoices/${kind}/${id}`, data), 'Đã điều chỉnh hóa đơn.'),
    'Lưu điều chỉnh',
  );
  updateUtilityPreview();
}
async function checkout(kind, id) {
  if (!resident()) throw new Error('Thanh toán online dành cho tài khoản cư dân.');
  const order = await post(`/api/billing/invoices/${kind}/${id}/checkout`);
  showPayment(order);
}
const paymentStorageKey = () => `ancu_vietqr_order_${state.user?.user_id}`;
const activePayment = (order) => ['pending', 'awaiting_confirmation'].includes(order.status);
const sessionExpired = (order) =>
  order.status === 'pending' &&
  Number.isFinite(Date.parse(order.expires_at)) &&
  Date.now() >= Date.parse(order.expires_at);
const transferAmount = (order) => (typeof order.remaining_amount === 'number' ? order.remaining_amount : order.amount);
function rememberPayment(order) {
  if (order.mode === 'sepay' && activePayment(order)) sessionStorage.setItem(paymentStorageKey(), order.order_id);
  else if (sessionStorage.getItem(paymentStorageKey()) === order.order_id)
    sessionStorage.removeItem(paymentStorageKey());
}
async function resumePayment() {
  if (!resident()) return;
  const orderId = sessionStorage.getItem(paymentStorageKey());
  if (!orderId || !/^VQR-[A-Za-z0-9_-]{1,100}$/.test(orderId)) return;
  const userId = state.user.user_id;
  try {
    const order = await api(`/api/billing/orders/${encodeURIComponent(orderId)}`);
    if (state.user?.user_id !== userId) return;
    state.route = 'billing';
    state.tab.billing = order.invoice_type;
    history.replaceState(null, '', '#billing');
    renderPage();
    showPayment(order);
  } catch (error) {
    if (state.user?.user_id !== userId) return;
    if ([403, 404].includes(error.status)) sessionStorage.removeItem(paymentStorageKey());
    toast(`Chưa kiểm tra được phiên chuyển khoản. ${error.message}`, true);
  }
}
function paymentFeedback(message, error = false) {
  const box = $('#payment-feedback');
  if (!box) return;
  box.textContent = message;
  box.hidden = !message;
  box.className = error ? 'error-box' : 'info-box';
}
function paymentClock(watch) {
  if (paymentWatch !== watch) return;
  const expired = sessionExpired(watch.order);
  if (expired !== watch.expired) {
    updatePayment(watch.order);
    return;
  }
  const clock = $('#payment-expiry');
  if (!clock) return;
  const remaining = Math.max(0, Math.ceil((Date.parse(watch.order.expires_at) - Date.now()) / 1000));
  clock.textContent = expired
    ? 'Phiên trên web đã hết thời gian. Nếu đã chuyển khoản, hệ thống vẫn tự ghi nhận; không chuyển lần nữa.'
    : `Thời gian giữ phiên: ${Math.floor(remaining / 60)} phút ${String(remaining % 60).padStart(2, '0')} giây. Đây không phải hạn thanh toán hóa đơn.`;
}
function updatePayment(order) {
  const watch = paymentWatch;
  if (!watch || watch.order.order_id !== order.order_id) return;
  const previous = watch.order.status;
  watch.order = order;
  watch.expired = sessionExpired(order);
  rememberPayment(order);
  const success = order.status === 'success',
    pending = order.status === 'pending',
    awaiting = order.status === 'awaiting_confirmation';
  const owner = order.is_owner === true,
    canPay = owner && order.can_pay === true && pending && !watch.expired;
  $('#payment-amount').textContent = money(success ? order.amount : transferAmount(order));
  const title = success
    ? 'Đã xác nhận thanh toán'
    : awaiting
      ? 'Chờ ngân hàng xác nhận'
      : watch.expired || order.status === 'expired'
        ? 'Phiên thanh toán đã hết thời gian'
        : pending
          ? owner
            ? 'Đang chờ chuyển khoản'
            : 'Một thành viên khác đang thanh toán'
          : 'Phiên thanh toán đã hủy';
  const explanation = success
    ? 'Hệ thống đã đối soát khoản nhận. Hóa đơn đã được cập nhật và có thể tải biên nhận.'
    : awaiting
      ? 'Hệ thống đang chờ ngân hàng xác nhận khoản chuyển và sẽ tự cập nhật hóa đơn. Vui lòng không chuyển thêm.'
      : canPay
        ? 'Chỉ một thành viên thanh toán hóa đơn này. Kiểm tra đúng tài khoản, số tiền và giữ nguyên nội dung chuyển khoản. Hóa đơn tự chuyển sang đã thanh toán khi hệ thống nhận đủ tiền.'
        : activePayment(order) && !owner
          ? 'Một thành viên trong căn hộ đang giữ phiên thanh toán. Vui lòng chờ kết quả, không chuyển khoản thêm.'
          : 'Nếu đã chuyển khoản, hệ thống vẫn tự ghi nhận theo nội dung chuyển khoản; không chuyển lại và liên hệ Ban quản lý nếu cần hỗ trợ. Không dùng lại mã QR cũ.';
  $('#payment-status').innerHTML =
    view`
      ${badge(order.status)}<h3 style="margin:12px 0 6px">${esc(title)}</h3>
      <p>${esc(explanation)}</p>${order.message ? `<p>${esc(order.message)}</p>` : ''}
      ${Number(order.paid_amount) > 0 && !success ? view`
        <p>Tổng hóa đơn ${esc(money(order.amount))}; đã nhận ${esc(money(order.paid_amount))}; còn thiếu ${esc(money(order.remaining_amount))}. ${canPay ? 'Chỉ chuyển phần còn thiếu bằng QR mới bên dưới.' : 'Không chuyển thêm khi chưa có hướng dẫn đối soát.'}
          </p>
      ` : ''}
      
    `;
  if (success && order.paid_at)
    $('#payment-status').insertAdjacentHTML(
      'beforeend',
      `<p>Thời gian thanh toán: ${esc(dateTime(order.paid_at))} (giờ Việt Nam).</p>`,
    );
  const options = $('#payment-options'),
    optionKey = canPay
      ? JSON.stringify([order.order_id, order.qr_image_url, order.transfer_content, order.bank, transferAmount(order)])
      : 'hidden';
  if (options && watch.optionKey !== optionKey) {
    watch.optionKey = optionKey;
    if (modalBlob) {
      URL.revokeObjectURL(modalBlob);
      modalBlob = null;
    }
    options.hidden = !canPay;
    options.innerHTML = canPay
      ? view`
        
        ${order.qr_image_url ? '<img id="payment-qr" alt="Mã VietQR thanh toán hóa đơn" hidden>' : ''}
        <div style="text-align:left;margin-top:18px">
          ${detail(
          [
            ['Ngân hàng', order.bank?.name || order.bank?.code],
            ['Số tài khoản', order.bank?.account_number],
            ['Chủ tài khoản', order.bank?.account_name],
            ['Số tiền cần chuyển', money(transferAmount(order))],
            ['Nội dung chuyển khoản', order.transfer_content],
          ],
        )}
          </div>
        <p id="payment-expiry" class="muted" role="timer">
        </p>
        <p class="muted">Hết phiên chỉ ẩn mã trên web, không thu hồi được QR đã lưu. Không chia sẻ QR cho người khác thanh toán cùng lúc.</p>
      `
      : '';
    if (canPay && order.qr_image_url) loadPaymentQr(watch, optionKey);
  }
  $('#payment-actions').innerHTML =
    button('Đóng', 'close-modal', '', 'secondary') +
    (success
      ? (order.payment_id
          ? button(
              'Tải biên nhận',
              'receipt',
              'download',
              'primary',
              `data-id="${esc(order.payment_id)}" data-kind="${esc(order.invoice_type)}"`,
            )
          : '') + button('Lịch sử thanh toán', 'payment-history', '', 'secondary')
      : (canPay && !(Number(order.paid_amount) > 0) ? button('Hủy phiên', 'payment-cancel', '', 'secondary') : '') +
        (['expired', 'cancelled'].includes(order.status)
          ? button(
              'Mở phiên mới',
              'invoice-pay',
              'wallet',
              'primary',
              `data-id="${esc(order.invoice_id)}" data-kind="${esc(order.invoice_type)}"`,
            )
          : ''));
  paymentClock(watch);
  if (!activePayment(order)) {
    clearTimeout(watch.timer);
    clearInterval(watch.clock);
    watch.clock = null;
  } else if (!watch.clock) watch.clock = setInterval(() => paymentClock(watch), 1000);
  if (previous !== order.status && success) {
    renderPage();
    toast('Đã xác nhận thanh toán hóa đơn.');
  }
}
function queuePaymentPoll(watch) {
  if (paymentWatch !== watch || !activePayment(watch.order)) return;
  clearTimeout(watch.timer);
  watch.timer = setTimeout(async () => {
    if (!document.hidden) await checkPayment(watch);
    queuePaymentPoll(watch);
  }, 4000);
}
// The webhook and the server's reconciliation settle the invoice; the page only follows.
// A failed check is shown, and cleared again by the next check that succeeds.
async function checkPayment(watch) {
  if (!watch || paymentWatch !== watch || watch.busy) return;
  watch.busy = true;
  const controller = new AbortController();
  watch.controller = controller;
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const order = await api(`/api/billing/orders/${encodeURIComponent(watch.order.order_id)}`, {
      signal: controller.signal,
    });
    if (paymentWatch !== watch) return;
    updatePayment(order);
    if (watch.checkFailed || order.status === 'success') paymentFeedback('');
    watch.checkFailed = false;
  } catch (error) {
    if (paymentWatch !== watch) return;
    watch.checkFailed = true;
    paymentFeedback(`Chưa cập nhật được trạng thái thanh toán. ${error.message}`, true);
  } finally {
    clearTimeout(timeout);
    watch.controller = null;
    watch.busy = false;
  }
}
function showPayment(order) {
  if (!resident() || order.mode !== 'sepay') return;
  const testing = order.environment === 'test';
  openModal(
    testing ? 'VietQR · SePay Test' : 'Thanh toán VietQR',
    view`
      <div class="modal-body qr-area">
        <div class="notice-symbol" style="margin:auto">${icon('wallet')}</div>
        <div class="amount" id="payment-amount">${money(transferAmount(order))}</div>
        <p>Hóa đơn #${esc(order.invoice_id)} · ${esc(label(order.invoice_type))}</p>
        ${testing ? '<div class="info-box" style="margin-top:18px;text-align:left">Môi trường SePay Test: dùng chức năng gửi giao dịch thử trên SePay để kiểm tra.</div>' : ''}
        <div id="payment-status" role="status" aria-live="polite">
        </div>
        <div id="payment-options">
        </div>
        <div id="payment-feedback" role="status" style="margin-top:18px" hidden>
        </div>
        <p class="muted" style="font-size:10px;margin-top:13px;overflow-wrap:anywhere">Mã phiên: ${esc(order.order_id)}</p>
      </div>
    `,
    `<div class="modal-footer" id="payment-actions" style="flex-wrap:wrap"></div>`,
  );
  const watch = { order, timer: null, clock: null, busy: false };
  paymentWatch = watch;
  updatePayment(order);
  queuePaymentPoll(watch);
}
async function loadPaymentQr(watch, optionKey) {
  try {
    const path = new URL(watch.order.qr_image_url, location.origin);
    if (path.origin !== location.origin || !path.pathname.startsWith('/api/billing/orders/'))
      throw new Error('Đường dẫn mã QR không hợp lệ.');
    const response = await fetch(path.href, { cache: 'no-store', headers: { Authorization: `Bearer ${state.token}` } });
    if (!response.ok) throw new Error('Chưa tải được mã VietQR. Hãy đóng hộp thoại rồi bấm Thanh toán lại.');
    const blob = await response.blob();
    if (paymentWatch !== watch || watch.optionKey !== optionKey) return;
    modalBlob = URL.createObjectURL(blob);
    const image = $('#payment-qr');
    if (image) {
      image.src = modalBlob;
      image.hidden = false;
    }
  } catch (error) {
    if (paymentWatch === watch) paymentFeedback(error.message, true);
  }
}
async function cancelPayment() {
  const watch = paymentWatch;
  if (
    !watch ||
    watch.busy ||
    !watch.order.is_owner ||
    watch.order.status !== 'pending' ||
    Number(watch.order.paid_amount) > 0
  )
    return;
  if (
    !window.confirm(
      'Chỉ hủy khi bạn CHƯA chuyển khoản. Nếu đã chuyển, chọn Hủy bỏ và chờ hệ thống tự xác nhận. Bạn chắc chắn chưa chuyển tiền?',
    )
  )
    return;
  watch.busy = true;
  try {
    const order = await post(`/api/billing/orders/${encodeURIComponent(watch.order.order_id)}/cancel`);
    if (paymentWatch === watch) updatePayment(order);
  } finally {
    watch.busy = false;
  }
}
function resolveBankTransaction(id) {
  if (!billingManager()) throw new Error('Chỉ Ban quản lý và kỹ thuật viên được ghi nhận xử lý giao dịch.');
  const row = state.data.bankTransactions?.find((item) => Number(item.transaction_id) === Number(id));
  if (!row) throw new Error('Không tìm thấy giao dịch.');
  formModal(
    'Ghi nhận xử lý chuyển khoản',
    select(
      'resolution',
      'Kết quả xử lý',
      [
        ['reviewed', 'Đã kiểm tra'],
        ['refunded', 'Đã hoàn trả thực tế'],
        ['retained', 'Đã thống nhất giữ lại'],
      ],
      row.resolution || 'reviewed',
    ) + field('note', 'Ghi chú xử lý', 'textarea', row.resolution_note || '', 'required maxlength="2000"'),
    (data) =>
      saved(post(`/api/billing/sepay/transactions/${encodeURIComponent(id)}/resolve`, data), 'Đã lưu ghi chú xử lý.'),
    'Lưu ghi chú',
    `Khoản nhận ${money(row.amount)}, chưa phân bổ ${money(row.unallocated_amount)}. Thao tác này chỉ lưu sổ theo dõi, không chuyển tiền hoặc hoàn tiền. Chỉ chọn “Đã hoàn trả thực tế” sau khi đã hoàn tiền và kiểm tra chứng từ.`,
  );
}
function cashPayment(kind, id) {
  if (!billingManager()) throw new Error('Chỉ Ban quản lý và kỹ thuật viên được ghi nhận khoản tiền đã nhận.');
  const row = state.currentInvoice || findInvoice(kind, id);
  formModal(
    'Ghi nhận thanh toán đã nhận',
    select('payment_method', 'Hình thức thu', [
      ['cash', 'Tiền mặt'],
      ['bank_transfer', 'Chuyển khoản ngân hàng'],
    ]) + field('transaction_code', 'Mã giao dịch / tham chiếu', 'text', '', 'maxlength="100"'),
    (data) => saved(post(`/api/billing/invoices/${kind}/${id}/pay`, data), 'Đã ghi nhận thanh toán.'),
    'Xác nhận đã nhận tiền',
    `Chỉ xác nhận sau khi đã thực nhận đủ ${money(row?.total_amount)} cho hóa đơn #${id}.`,
  );
}
function releasePayment(kind, id) {
  if (!billingManager()) throw new Error('Chỉ Ban quản lý và kỹ thuật viên được mở khóa phiên thanh toán.');
  formModal(
    'Mở khóa phiên thanh toán',
    field('note', 'Lý do mở khóa', 'textarea', '', 'required maxlength="500"'),
    (data) => saved(post(`/api/billing/invoices/${kind}/${id}/release-payment`, data), 'Đã mở khóa phiên thanh toán.'),
    'Mở khóa phiên',
    'Chỉ dùng khi cư dân báo đã chuyển nhưng ngân hàng không ghi nhận khoản tiền nào. Nếu tiền về sau đó, hệ thống vẫn tự ghi nhận theo mã thanh toán.',
  );
}
async function receipt(kind, id) {
  const data = await api(`/api/billing/payments/${kind}/${id}/receipt`);
  downloadBlob(await receiptImage(data), `bien-nhan-${kind}-${id}.png`);
  toast('Đã tải ảnh biên nhận.');
}
function wrapText(context, text, width) {
  const lines = [''];
  for (const word of String(text).split(/\s+/)) {
    const next = lines[lines.length - 1] ? `${lines[lines.length - 1]} ${word}` : word;
    if (context.measureText(next).width <= width || !lines[lines.length - 1]) lines[lines.length - 1] = next;
    else lines.push(word);
  }
  return lines;
}
async function receiptImage(data) {
  await document.fonts?.ready;
  const family = getComputedStyle(document.body).fontFamily;
  const width = 900,
    pad = 56,
    labelWidth = 310,
    lineHeight = 30,
    canvas = document.createElement('canvas'),
    context = canvas.getContext('2d');
  context.font = `18px ${family}`;
  const valueWidth = width - pad * 2 - labelWidth;
  const rows = data.rows.map(([name, value]) => ({
    name: wrapText(context, name, labelWidth - 24),
    value: wrapText(context, value, valueWidth),
  }));
  const rowHeight = (row) => Math.max(row.name.length, row.value.length) * lineHeight + 26;
  const height = 190 + (data.notice ? 44 : 0) + rows.reduce((sum, row) => sum + rowHeight(row), 0) + 90;
  const scale = 2;
  canvas.width = width * scale;
  canvas.height = height * scale;
  context.scale(scale, scale);
  context.fillStyle = '#fff';
  context.fillRect(0, 0, width, height);
  context.fillStyle = '#1a7350';
  context.fillRect(0, 0, width, 10);
  context.textBaseline = 'top';
  context.fillStyle = '#183d35';
  context.font = `700 34px ${family}`;
  context.fillText(data.title, pad, 56);
  context.font = `18px ${family}`;
  context.fillStyle = '#5b7268';
  context.fillText(data.issuer, pad, 108);
  let y = 150;
  if (data.notice) {
    context.fillStyle = '#b3261e';
    context.font = `600 18px ${family}`;
    context.fillText(data.notice, pad, y);
    y += 44;
  }
  for (const row of rows) {
    context.strokeStyle = '#dfe9e3';
    context.beginPath();
    context.moveTo(pad, y);
    context.lineTo(width - pad, y);
    context.stroke();
    context.font = `600 18px ${family}`;
    context.fillStyle = '#183d35';
    row.name.forEach((line, i) => context.fillText(line, pad, y + 14 + i * lineHeight));
    context.font = `18px ${family}`;
    row.value.forEach((line, i) => context.fillText(line, pad + labelWidth, y + 14 + i * lineHeight));
    y += rowHeight(row);
  }
  context.font = `16px ${family}`;
  context.fillStyle = '#5b7268';
  context.fillText(data.footer, pad, y + 26);
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('Chưa tạo được ảnh biên nhận.'))), 'image/png'),
  );
}
function downloadBlob(blob, name) {
  const url = URL.createObjectURL(blob),
    link = document.createElement('a');
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function vehicleForm(id) {
  const apartments = state.data.apartments || (await items('/api/apartments')),
    row = id ? state.data.vehicles.find((r) => r.vehicle_id === Number(id)) : {};
  const feePaid = id && row.status !== 'cancelled' ? (await api(`/api/billing/vehicle-billing/${id}`)).fee_paid : false;
  if (row.status === 'cancelled') {
    openModal(
      'Phương tiện đã hủy',
      view`
        <div class="modal-body">
          ${detail([
        ['Biển số', row.plate_number],
        ['Căn hộ', apartmentCode(row.apartment_id)],
        ['Loại xe', label(row.vehicle_type)],
        ['Trạng thái', 'Đã hủy'],
      ])}
          </div>
      `,
      `<div class="modal-footer">${button('Đóng', 'close-modal', '', 'secondary')}</div>`,
    );
    return;
  }
  formModal(
    id ? 'Cập nhật phương tiện' : 'Đăng ký phương tiện',
    select('apartment_id', 'Căn hộ', apartmentOptions(apartments), row.apartment_id || '') +
      select('vehicle_type', 'Loại phương tiện', parkingTypes, row.vehicle_type || 'motorbike') +
      field(
        'plate_number',
        'Biển số xe',
        'text',
        row.plate_number || '',
        'maxlength="30" aria-describedby="parking-plate-help"',
      ) +
      `<p id="parking-plate-help" class="muted">${esc(parkingPlateHelp)}</p>` +
      field('monthly_fee', 'Phí hàng tháng (VNĐ)', 'number', parkingFee(row.vehicle_type), 'readonly required') +
      field(
        'registered_date',
        'Ngày đăng ký',
        'date',
        row.registered_date || today(),
        `required ${id ? 'readonly' : ''}`,
      ) +
      field(
        'registration_months',
        'Số tháng đăng ký (tính cả tháng bắt đầu)',
        'number',
        row.registration_months || 2,
        // A one-month renewal stays editable: its own length is the floor, never more than it has.
        `required min="${feePaid ? row.registration_months : Math.min(row.registration_months || Infinity, parkingWindow(row.registered_date || today()).fewest)}" step="1" aria-describedby="parking-months-help"`,
      ) +
      `<p id="parking-months-help" class="muted">${id ? `Đăng ký hiện đến hết ngày ${esc(date(row.minimum_end_date))}. Muốn gửi tiếp, dùng Gia hạn.` : ''}</p>` +
      (id ? select('status', 'Trạng thái', enumOptions(['active', 'cancelled']), row.status) : ''),
    (data) => {
      validateParking(data, !id);
      return saved(id ? patch(`/api/parking/vehicles/${id}`, data) : post('/api/parking/vehicles', data));
    },
    'Lưu thông tin',
    `Thu phí 6 tháng một lần cùng tiền dịch vụ. Phí cấp thẻ lần đầu: 100.000 VNĐ/xe trong tháng đầu; xe từng đăng ký (cùng biển số hoặc mã xe đạp cũ) đã có thẻ nên không thu lại.${id ? ` Phí làm thẻ của đăng ký này: ${Number(row.card_fee) > 0 ? money(row.card_fee) : 'miễn'}.` : ''}${row.minimum_end_date ? ' Có thể hủy từ ngày ' + date(row.minimum_end_date) + '.' : ''}${feePaid ? ' Xe đã đóng phí nên không thể giảm thời gian cam kết.' : ''}`,
  );
  updateParkingFields();
}
function vehicleRenewForm(id) {
  const row = state.data.vehicles.find((r) => r.vehicle_id === Number(id));
  const w = parkingWindow(renewalStart(row), true);
  formModal(
    `Gia hạn xe ${row.plate_number}`,
    `<div class="field wide">${detail([['Căn hộ', apartmentCode(row.apartment_id)], ['Ngày hết hạn hiện tại', date(row.minimum_end_date)]])}</div>` +
      field('months', 'Số tháng gia hạn', 'number', String(w.fewest), `required min="${w.fewest}" max="${w.most}" step="1"`) +
      `<p class="muted">${esc(parkingWindowText(w, 'Gia hạn'))}</p>`,
    (data) => saved(post(`/api/parking/vehicles/${id}/renew`, data), 'Đã gia hạn đăng ký gửi xe.'),
    'Gia hạn',
    'Còn hạn thì phần gia hạn nối tiếp ngay sau ngày hết hạn hiện tại. Đã quá hạn thì đăng ký mới bắt đầu từ hôm nay; những tháng xe không gửi không bị tính phí và không thu lại phí làm thẻ.',
  );
}
async function vehicleSupplementForm(id) {
  const info = await api(`/api/billing/vehicle-billing/${id}`);
  if (!info.available) {
    openModal(
      'Hóa đơn gửi xe bổ sung',
      `<div class="modal-body"><div class="info-box">${esc(info.reason)}</div></div>`,
      `<div class="modal-footer">${button('Đóng', 'close-modal', '', 'secondary')}</div>`,
    );
    return;
  }
  const next = new Date();
  next.setDate(next.getDate() + 14);
  formModal(
    'Lập hóa đơn gửi xe bổ sung',
    `<div class="field wide">${detail([
      ['Biển số', info.plate_number],
      ['Căn hộ', apartmentCode(info.apartment_id)],
      ['Kỳ thu', info.period],
      ['Số tháng tính phí', `${number(info.months)} tháng × ${money(info.monthly_fee)}`],
      ['Phí làm thẻ', money(info.card_fee)],
      ['Tổng tiền', money(info.amount)],
    ])}</div>` + field('due_date', 'Hạn thanh toán', 'date', next.toLocaleDateString('en-CA'), 'required'),
    (data) => saved(post(`/api/billing/vehicle-billing/${id}/supplement`, data), 'Đã phát hành hóa đơn bổ sung.'),
    'Phát hành hóa đơn',
    'Dùng khi xe đăng ký sau lúc đã phát hành hóa đơn dịch vụ của kỳ. Hóa đơn này chỉ thu riêng tiền gửi của xe và cư dân thanh toán như hóa đơn 6 tháng.',
  );
}
function guestForm(id) {
  const row = id ? state.data.guests.find((r) => r.record_id === Number(id)) : {};
  formModal(
    id ? 'Cập nhật doanh thu vãng lai' : 'Ghi nhận doanh thu vé vãng lai',
    field('parking_date', 'Ngày ghi nhận', 'date', row.parking_date || today(), `required max="${today()}"`) +
      field(
        'daily_revenue',
        'Tổng doanh thu trong ngày (VNĐ)',
        'number',
        row.daily_revenue ?? '',
        'required min="0" step="1"',
      ),
    (data) =>
      saved(
        id
          ? api(`/api/parking/guest-daily/${id}`, { method: 'PUT', body: data })
          : post('/api/parking/guest-daily', data),
        'Đã ghi nhận doanh thu vãng lai.',
      ),
    'Lưu doanh thu',
    'Nhập tổng số tiền thu từ khách vãng lai trong ngày. Mỗi ngày được ghi nhận một lần.',
  );
}
async function ticketForm(id) {
  if (id) {
    const row = state.data.tickets.find((r) => r.ticket_id === Number(id));
    const details = detail([
      ['Yêu cầu', `#${id} · ${label(row.type)}`],
      ['Căn hộ', ticketApartment(row)],
      ['Trạng thái', label(row.status)],
      ...(resident() ? [] : [['Ưu tiên', label(row.priority)]]),
      ['Phụ trách', row.technician_name || 'Chưa phân công'],
      ['Ngày tạo', date(row.created_at)],
      ['Nội dung', row.description, true],
    ]);
    if (resident() || row.status === 'completed') {
      openModal(
        'Chi tiết yêu cầu',
        view`
          <div class="modal-body">${details}
            ${row.completed_at ? `<p class="muted" style="font-size:11px;margin-top:18px">Hoàn thành: ${esc(date(row.completed_at))}</p>` : ''}
            </div>
        `,
        `<div class="modal-footer">${button('Đóng', 'close-modal', '', 'secondary')}</div>`,
      );
      return;
    }
    const statuses = row.status === 'pending' ? ['pending', 'in_progress'] : ['in_progress', 'completed'];
    let fields = select('status', 'Trạng thái xử lý', enumOptions(statuses), row.status);
    if (admin()) {
      const technicians = await items('/api/maintenance/technicians');
      fields +=
        select(
          'technician_id',
          'Phân công kỹ thuật viên',
          technicians.map((t) => [
            t.technician_id,
            `${t.full_name} · ${t.specialty === 'general' ? 'Kỹ thuật tổng hợp' : label(t.specialty)}`,
          ]),
          row.technician_id || '',
          true,
        ) +
        select('priority', 'Ưu tiên', enumOptions(['low', 'medium', 'high']), row.priority) +
        field('description', 'Nội dung', 'textarea', row.description, 'required maxlength="10000"');
    }
    formModal(
      `Cập nhật yêu cầu #${id}`,
      fields,
      (data) => saved(patch(`/api/maintenance/tickets/${id}`, data), 'Đã cập nhật tiến độ.'),
      'Lưu tiến độ',
      tech()
        ? row.description
        : 'Chọn kỹ thuật viên trước khi bắt đầu xử lý. Đóng phiếu sau khi công việc đã hoàn tất.',
    );
  } else {
    if (resident()) {
      // Only apartments confirmed by management; the resident API returns just those.
      const apartments = await items('/api/apartments');
      if (!apartments.length)
        throw new Error(
          'Tài khoản chưa được Ban quản lý xác nhận liên kết căn hộ. Vui lòng chờ xác nhận trước khi gửi yêu cầu.',
        );
      // One account, one apartment: shown, not chosen.
      const fields =
        fixedField('Căn hộ', apartments[0].code, 'apartment_id', apartments[0].apartment_id) +
        select('type', 'Loại yêu cầu', [
          ['repair', 'Sửa chữa'],
          ['maintenance', 'Bảo trì'],
        ]) +
        field(
          'description',
          'Mô tả vấn đề',
          'textarea',
          '',
          'required maxlength="10000" placeholder="Mô tả vị trí, hiện trạng và thời gian có thể hỗ trợ…"',
        );
      formModal(
        'Tạo yêu cầu sửa chữa / bảo trì',
        fields,
        (data) => saved(post('/api/maintenance/tickets', data), 'Đã gửi yêu cầu sửa chữa.'),
        'Gửi yêu cầu',
        '',
        'vertical',
      );
    } else {
      const technicians = admin() ? await items('/api/maintenance/technicians') : [];
      formModal(
        'Tạo yêu cầu sửa chữa / bảo trì',
        field(
          'location',
          'Căn hộ / địa điểm',
          'text',
          '',
          'required maxlength="120" autocomplete="off" placeholder="Ví dụ: A101 hoặc Sảnh tòa A"',
        ) +
          select('type', 'Loại yêu cầu', enumOptions(['repair', 'maintenance'])) +
          select('priority', 'Mức độ ưu tiên', enumOptions(['low', 'medium', 'high']), 'medium') +
          (admin()
            ? select(
                'technician_id',
                'Phân công kỹ thuật viên',
                technicians.map((t) => [t.technician_id, t.full_name]),
                '',
                false,
              )
            : '') +
          field(
            'description',
            'Mô tả vấn đề',
            'textarea',
            '',
            'required maxlength="10000" placeholder="Mô tả vị trí, hiện trạng và thời gian có thể hỗ trợ…"',
          ),
        (data) => saved(post('/api/maintenance/tickets', data), 'Đã gửi yêu cầu sửa chữa.'),
        'Gửi yêu cầu',
      );
    }
  }
}
const parkingTypes = [
  ['motorbike', 'Xe máy'],
  ['electric_bike', 'Xe điện (thu phí như xe máy)'],
  ['bicycle', 'Xe đạp'],
];
const vehicleTypeLabel = (type) => (type === 'electric_bike' ? 'Xe điện (máy điện, đạp điện)' : label(type));
const parkingPlateHelp =
  'Xe máy và xe điện phải có biển số. Xe điện chưa có biển phải làm biển nhận dạng theo căn hộ (căn hộ - loại xe - số thứ tự xe trong căn hộ. VD: A101-XD-1). Xe đạp được cấp mã khi duyệt đăng ký.';
const parkingFee = (type) => (type === 'bicycle' ? 50000 : 100000);
// Same rule as Parking Service: at least 2 months, the starting month included, and every month
// must begin within the six-month fee period (June or December ends it). June may run seven months;
// December covers one month, because no registration begins in the next year. Renewing a vehicle
// already registered may add a single month.
function parkingWindow(startIso, renewal = false) {
  const year = Number(String(startIso).slice(0, 4)),
    month = Number(String(startIso).slice(5, 7)),
    last = month >= 6 ? 12 : 6,
    most = last - month + 1;
  return { fewest: renewal ? 1 : Math.min(2, most), most, last, year, month };
}
function parkingWindowText(w, action = 'Đăng ký') {
  const span = w.fewest === w.most ? `đúng ${w.most} tháng` : `từ ${w.fewest} đến ${w.most} tháng`;
  return `${action} bắt đầu tháng ${w.month}/${w.year}: chọn ${span} (tính cả tháng bắt đầu; kỳ thu phí kết thúc tháng ${w.last}/${w.year}).`;
}
// Same rule as Parking Service: calendar months from the start date, like a monthly ticket.
// 20/11 for 2 months runs to the end of 19/01; when the month is shorter, its last day stands in
// for the same day (31/01 + 1 month → 28/02, so the registration runs to the end of 27/02).
function parkingEnd(startIso, months) {
  const [year, month, day] = String(startIso).split('-').map(Number),
    index = year * 12 + month - 1 + months,
    y = Math.floor(index / 12),
    m = index % 12,
    end = new Date(y, m, Math.min(day, new Date(y, m + 1, 0).getDate()));
  end.setDate(end.getDate() - 1);
  return end.toLocaleDateString('en-CA');
}
// The first day after a registration runs out, or today if it already did: where a renewal starts.
function renewalStart(row) {
  const end = new Date(`${row.minimum_end_date}T00:00:00`);
  end.setDate(end.getDate() + 1);
  const next = end.toLocaleDateString('en-CA');
  return next > today() ? next : today();
}
// Where a renewal of `months` ends, as Parking Service extends it: a running registration grows,
// one that already ran out starts again today.
function renewalEnd(row, months) {
  return row.minimum_end_date >= today()
    ? parkingEnd(row.registered_date, row.registration_months + months)
    : parkingEnd(today(), months);
}
// The resident's own running registrations: an application for one of these plates is a renewal.
let parkingRenewals = [];
const plateKey = (plate) =>
  String(plate || '')
    .toUpperCase()
    .replace(/[^0-9A-Z]/g, '');
function parkingRenewal(plate) {
  const key = plateKey(plate);
  return key ? parkingRenewals.find((v) => plateKey(v.plate_number) === key) : undefined;
}
function updateParkingFields() {
  const form = $('#modal-form'),
    type = form?.elements.vehicle_type?.value;
  if (!type) return;
  const plate = form.elements.plate_number;
  plate.required = type !== 'bicycle';
  $('label[for="field-plate_number"]', form).innerHTML =
    `Biển số xe${plate.required ? ' <span class="req-star">*</span>' : ''}`;
  form.elements.monthly_fee.value = parkingFee(type);
  const start = form.elements.registered_date,
    months = form.elements.registration_months,
    help = $('#parking-months-help', form);
  // A resident applying for a plate already registered to the apartment is renewing it.
  const renewal = form.elements.apartment_code && parkingRenewal(plate.value);
  if (renewal && months) {
    const from = renewalStart(renewal),
      w = parkingWindow(from, true),
      chosen = Number(months.value);
    months.min = w.fewest;
    months.max = w.most;
    if (help)
      help.textContent =
        `Xe ${renewal.plate_number} đã đăng ký, đơn này là gia hạn nối tiếp từ ngày ${date(from)}. ` +
        parkingWindowText(w, 'Gia hạn') +
        (Number.isInteger(chosen) && chosen >= w.fewest && chosen <= w.most
          ? ` Gửi đến hết ngày ${date(renewalEnd(renewal, chosen))}.`
          : '');
    return;
  }
  // A saved registration keeps its own limits; Parking Service checks any change.
  if (!start?.value || !months || start.readOnly) return;
  const w = parkingWindow(start.value),
    chosen = Number(months.value);
  months.min = w.fewest;
  months.max = w.most;
  if (help)
    help.textContent =
      parkingWindowText(w) +
      (Number.isInteger(chosen) && chosen >= w.fewest && chosen <= w.most
        ? ` Gửi đến hết ngày ${date(parkingEnd(start.value, chosen))}.`
        : '');
}
function validateParking(data, isNew = true, renewalFrom = null) {
  if (!parkingTypes.some(([value]) => value === data.vehicle_type)) throw new Error('Vui lòng chọn loại xe hợp lệ.');
  if (data.vehicle_type !== 'bicycle' && !data.plate_number?.trim())
    throw new Error('Vui lòng nhập biển số xe máy hoặc xe điện; xe điện chưa có biển cần biển nhận dạng theo căn hộ.');
  if (!Number.isInteger(data.registration_months) || data.registration_months < 1)
    throw new Error('Vui lòng nhập số tháng gửi xe.');
  if (isNew) {
    const w = renewalFrom ? parkingWindow(renewalFrom, true) : parkingWindow(data.registered_date);
    if (data.registration_months < w.fewest || data.registration_months > w.most)
      throw new Error(parkingWindowText(w, renewalFrom ? 'Gia hạn' : 'Đăng ký'));
  }
  data.monthly_fee = parkingFee(data.vehicle_type);
}
function parkingRulesModal() {
  const modal = $('#modal');
  const previous = {
    nodes: [...modal.childNodes],
    submit: modalSubmit,
    scrollTop: modal.scrollTop,
    focus: document.activeElement,
  };
  openModal(
    'Quy định đăng ký gửi xe tại chung cư',
    view`
      <div class="modal-body">
        <ul style="line-height:2.1;padding-left:20px;font-size:14px;color:var(--ink)">
          <li>
            <strong>Thời gian gửi xe:</strong> Tính theo lịch từ ngày bắt đầu, như vé tháng: bắt đầu ngày 20/11, gửi 2 tháng thì được gửi đến hết ngày 19/01. Mỗi lần đăng ký tối thiểu 2 tháng, gia hạn xe đã đăng ký được từ 1 tháng; số tháng tính cả tháng bắt đầu và tối đa đến tháng cuối của kỳ thu phí 6 tháng (tháng 1–6 hoặc tháng 7–12). Đăng ký tháng 6 được chọn đến 7 tháng; đăng ký tháng 12 chỉ 1 tháng. Mỗi tháng gửi được thu trong kỳ có ngày bắt đầu của tháng đó, nên những ngày của tháng cuối lẻ sang kỳ sau đã được tính, kỳ sau không thu thêm. Hết thời gian đăng ký, xe cần được gia hạn mới gửi tiếp. Phí gửi xe được thu 6 tháng một lần cùng tiền dịch vụ của tòa nhà.</li>
          <li>
            <strong>Biểu phí:</strong> Xe đạp: 50.000 VNĐ/xe/tháng. Xe máy: 100.000 VNĐ/xe/tháng. Xe điện (thu phí như xe máy): 100.000 VNĐ/xe/tháng.</li>
          <li>
            <strong>Phí làm thẻ:</strong> Tháng đầu tiên phụ thu 100.000 VNĐ/xe để làm thẻ gửi xe.</li>
          <li>
            <strong>Biển số & thẻ xe:</strong> Xe máy và xe điện bắt buộc khai báo biển số. Xe điện chưa có biển phải làm biển nhận dạng theo căn hộ (căn hộ - loại xe - số thứ tự xe trong căn hộ, VD: A101-XD-1). Xe đạp được cấp mã khi duyệt đăng ký. Không tự ý cho người ngoài tòa nhà mượn thẻ xe.</li>
          <li>
            <strong>Quy định di chuyển & đỗ xe:</strong> Tốc độ tối đa 20 km/h trong khuôn viên hầm xe. Đỗ đúng vị trí cho từng loại phương tiện; không chắn lối đi, lối thoát hiểm hoặc thiết bị PCCC.</li>
        </ul>
        <p style="margin-top:16px;line-height:2.1;font-size:14px;color:var(--ink)">Đơn đăng ký sẽ được xem xét và duyệt trong vòng 48h. Cảm ơn quý cư dân đã tin tưởng. Mọi thắc mắc vui lòng liên hệ trực tiếp với Ban quản lý qua số điện thoại <strong>0228913665</strong>!</p>
      </div>
    `,
    `<div class="modal-footer">${button('Đóng', 'close-modal', '', 'primary')}</div>`,
  );
  modalReturn = previous;
  modalSubmit = null;
  modal.scrollTop = 0;
}
async function parkingRequestForm(draft = {}) {
  const version = ++modalVersion,
    route = state.route;
  const [profile, vehicles] = await Promise.all([
    state.data.personal || api('/api/residents/me'),
    // Only to recognise renewals: the form still works if the list cannot be loaded.
    items('/api/parking/vehicles').catch(() => []),
  ]);
  if (version !== modalVersion || route !== state.route || !state.user) return;
  parkingRenewals = vehicles.filter((v) => v.status === 'active' && v.plate_number);
  const aptDefault = profile.apartment_codes?.[0] || profile.registered_apartment_code || '';
  const fields =
    select('vehicle_type', 'Loại xe', parkingTypes, draft.vehicle_type || 'motorbike') +
    field(
      'plate_number',
      'Biển số xe',
      'text',
      draft.plate_number || '',
      'maxlength="30" aria-describedby="parking-plate-help" placeholder="Ví dụ: 29A-123.45 hoặc A101-XD-1"',
    ) +
    `<p id="parking-plate-help" class="muted">${esc(parkingPlateHelp)}</p>` +
    field('apartment_code', 'Căn hộ', 'text', aptDefault, 'required readonly maxlength="30" title="Căn hộ theo đăng ký của tài khoản"') +
    field('registered_date', 'Ngày bắt đầu gửi xe', 'date', draft.registered_date || today(), 'required') +
    field(
      'registration_months',
      'Số tháng gửi (tính cả tháng bắt đầu)',
      'number',
      draft.registration_months || 2,
      'required min="1" step="1" aria-describedby="parking-months-help"',
    ) +
    '<p id="parking-months-help" class="muted"></p>' +
    field('monthly_fee', 'Phí hàng tháng (VNĐ)', 'number', parkingFee(draft.vehicle_type), 'readonly required') +
    field(
      'notes',
      'Ghi chú thêm',
      'textarea',
      draft.notes || '',
      'maxlength="1000" placeholder="Nhãn hiệu xe, màu sơn hoặc yêu cầu bổ sung…"',
    ) +
    button('Quy định đăng ký gửi xe tại chung cư', 'parking-rules-modal', 'shield', 'link') +
    '<div class="info-box">Thu phí 6 tháng một lần cùng tiền dịch vụ. Xe mới phụ thu 100.000 VNĐ/xe để làm thẻ. Gia hạn xe đã đăng ký: gửi đơn với đúng biển số hoặc mã xe cũ, được gia hạn từ 1 tháng. Đơn được xem xét và duyệt trong vòng 48h. Mọi thắc mắc vui lòng liên hệ Ban quản lý: <strong>0228913665</strong>.</div>';
  formModal(
    'Đơn đăng ký gửi xe',
    fields,
    (data) => {
      const renewal = parkingRenewal(data.plate_number),
        from = renewal ? renewalStart(renewal) : data.registered_date;
      validateParking(data, true, renewal ? from : null);
      const until = renewal
        ? renewalEnd(renewal, data.registration_months)
        : parkingEnd(data.registered_date, data.registration_months);
      // "Thời gian cam kết" stays the label: Complaint Service reads the months from that line.
      const content = `Loại xe: ${label(data.vehicle_type)}\nBiển số: ${data.plate_number || 'Cấp mã theo căn hộ khi duyệt'}\nCăn hộ: ${data.apartment_code}\nNgày bắt đầu: ${from}\nThời gian cam kết: ${data.registration_months} tháng (${renewal ? 'gia hạn ' : ''}đến hết ngày ${date(until)})\nPhí gửi xe: ${money(data.monthly_fee)}/xe/tháng\nPhí làm thẻ lần đầu: 100.000 VNĐ/xe (xe từng đăng ký không thu lại)\nThu phí: 6 tháng một lần cùng tiền dịch vụ\nGhi chú: ${data.notes || 'Không có'}`;
      return saved(
        post('/api/complaints', { type: 'registration', category: 'Đăng ký gửi xe', content }),
        'Đã gửi đơn đăng ký. Ban quản lý sẽ xem xét trong vòng 48h.',
      );
    },
    'Gửi đơn đăng ký',
    '',
    'vertical',
  );
  updateParkingFields();
}
async function noticeDetail(id) {
  const notices = state.data.notices || (await items('/api/notifications'));
  let row = notices.find((n) => Number(n.notification_id) === Number(id));
  if (!row) row = await api(`/api/notifications/${id}`);
  if (!row.is_read) {
    try {
      await post(`/api/notifications/${id}/read`);
      row.is_read = 1;
      pollNotifications();
    } catch (e) {}
  }
  const entries = [
    ['Tiêu đề', row.title],
    ['Phân loại', label(row.type)],
    ['Thời gian thông báo', dateTime(row.created_at)],
    ...(row.related_apartment_id
      ? [['Căn hộ', row.related_apartment_code || apartmentCode(row.related_apartment_id)]]
      : row.target_apartment_id
        ? [['Căn hộ nhận', apartmentCode(row.target_apartment_id)]]
        : []),
    ...(row.invoice_created_at ? [['Thời gian lập hóa đơn', dateTime(row.invoice_created_at)]] : []),
    ...(row.paid_at ? [['Thời gian thanh toán', dateTime(row.paid_at)]] : []),
    ['Nội dung', row.content, true],
  ];
  openModal(
    row.title,
    `<div class="modal-body">${detail(entries)}</div>`,
    `<div class="modal-footer">${button('Đóng', 'close-modal', '', 'secondary')}</div>`,
  );
  if (state.route === 'notifications') renderPage();
}
async function noticeForm() {
  const apartments = await items('/api/apartments');
  formModal(
    'Soạn thông báo',
    select('audience', 'Đối tượng nhận', [
      ['general', 'Thông báo chung đến mọi người'],
      ['admin', 'Thông báo riêng đến Ban quản lý'],
      ...apartments.map((a) => [String(a.apartment_id), `Căn hộ ${a.code}`]),
    ]) +
      field('title', 'Tiêu đề', 'text', '', 'required maxlength="250"') +
      field('content', 'Nội dung thông báo', 'textarea', '', 'required maxlength="10000"'),
    (data) => {
      const audience = data.audience;
      delete data.audience;
      data.type = audience === 'general' ? 'general' : 'private';
      if (audience === 'admin') data.target_role = 'admin';
      else if (audience !== 'general') data.target_apartment_id = Number(audience);
      return saved(post('/api/notifications', data), 'Đã đăng thông báo.');
    },
    'Đăng thông báo',
  );
}
async function complaintForm(id, draft = {}, kind = 'complaint') {
  const version = ++modalVersion,
    route = state.route;
  if (id) {
    const row = state.data.complaints.find((r) => r.complaint_id === Number(id));
    if (!admin() || row.status === 'cancelled') {
      const cancellable = resident() && row.status === 'pending';
      openModal(
        `Yêu cầu #YC${id}`,
        view`
          <div class="modal-body">
            ${detail([
          ['Loại yêu cầu', label(row.type)],
          ['Danh mục', row.category],
          ['Trạng thái', label(row.status)],
          ['Ngày gửi', dateTime(row.created_at)],
          ['Nội dung', row.content, true],
          ['Phản hồi của Ban quản lý', row.response || 'Ban quản lý chưa phản hồi yêu cầu này.', true],
          ['Ngày hoàn tất', date(row.resolved_at)],
        ])}
            ${attachmentList(row.attachments)}
            ${resident() && row.status === 'processing' ? '<div class="info-box" style="margin-top:18px">Đơn đang ở trạng thái đang xử lý không thể huỷ yêu cầu</div>' : ''}
            </div>
        `,
        `<div class="modal-footer">${cancellable ? button('Huỷ yêu cầu', 'complaint-cancel', '', 'secondary', `data-id="${id}"`) : ''}${button('Đóng', 'close-modal', '', 'secondary')}</div>`,
      );
      return;
    }
    const closed = ['resolved', 'rejected'].includes(row.status);
    const statuses = closed
      ? [row.status]
      : row.status === 'processing'
        ? ['processing', 'resolved', 'rejected']
        : ['pending', 'processing', 'resolved', 'rejected'];
    const parkingApproval = row.type === 'registration' && row.category === 'Đăng ký gửi xe' && !closed;
    formModal(
      `Phản hồi yêu cầu #YC${id}`,
      detail([
        ['Loại yêu cầu', label(row.type)],
        ['Người gửi', row.resident_name || `Cư dân #${row.resident_id}`],
        ['Thời gian gửi', dateTime(row.created_at)],
        ['Danh mục / tên thủ tục', row.category],
        ['Nội dung cư dân gửi', row.content, true],
      ]) +
        attachmentList(row.attachments) +
        select('status', 'Trạng thái', enumOptions(statuses), row.status) +
        field(
          'response',
          'Phản hồi của Ban quản lý',
          'textarea',
          row.response || '',
          'required maxlength="10000" placeholder="Nhập câu trả lời và hướng dẫn cụ thể cho cư dân…"',
        ),
      (data) => {
        if (!data.response?.trim()) throw new Error('Vui lòng nhập nội dung phản hồi cho cư dân.');
        return saved(patch(`/api/complaints/${id}`, data), 'Đã lưu phản hồi cho cư dân.');
      },
      row.response ? 'Cập nhật phản hồi' : 'Gửi phản hồi',
      `Cư dân đã gửi yêu cầu sẽ nhận thông báo riêng khi nội dung phản hồi được cập nhật.${parkingApproval ? ' Chọn “Đã giải quyết” để duyệt đơn: hệ thống tự đăng ký phương tiện (xe đạp, xe điện chưa có biển được cấp mã theo căn hộ) và gửi thông báo cho cư dân.' : ''}${closed ? ' Yêu cầu đã hoàn tất; bạn có thể sửa phản hồi.' : ''}`,
      'vertical',
    );
  } else {
    if (version !== modalVersion || route !== state.route || !state.user) return;
    const procedure = kind === 'registration';
    const attachmentField = view`
      <div class="field wide">
        <label for="field-attachments">${procedure ? 'Tài liệu đính kèm' : 'Ảnh hoặc tài liệu đính kèm'}</label>
        <div class="file-picker">
          <input id="field-attachments" class="file-input" name="attachment_files" type="file" multiple accept="image/png,image/jpeg,image/gif,image/webp,application/pdf,text/plain,.doc,.docx,.xls,.xlsx">
          <label for="field-attachments" class="button secondary file-choose">${icon('plus')}Chọn tệp</label>
          <ul class="file-picks" id="attachment-picks"></ul>
        </div>
        <span class="help">Ảnh lớn được tự động thu nhỏ khi gửi. Nhận ảnh, PDF, Word, Excel hoặc tệp văn bản; tối đa 5 tệp, tổng dung lượng khoảng 450 KB.</span>
      </div>
    `;
    const fields =
      select(
        'type',
        'Loại yêu cầu',
        [
          ['complaint', 'Góp ý / Khiếu nại'],
          ['registration', 'Đăng ký thủ tục'],
        ],
        kind,
      ) +
      (procedure
        ? field(
            'category',
            'Danh mục / Tên thủ tục',
            'text',
            draft.category || '',
            'required maxlength="100" placeholder="Ví dụ: Đăng ký tạm trú, chuyển đồ, thi công nội thất…"',
          ) +
          attachmentField +
          field(
            'attachment_links',
            'Liên kết tài liệu (không bắt buộc)',
            'textarea',
            draft.attachment_links || '',
            'maxlength="3000" placeholder="Mỗi dòng một liên kết, ví dụ: https://drive.google.com/…"',
          ) +
          field(
            'content',
            'Nội dung chi tiết',
            'textarea',
            draft.content || '',
            'required maxlength="10000" placeholder="Trình bày nội dung thủ tục, thời gian thực hiện và thông tin liên quan…"',
          )
        : field(
            'category',
            'Danh mục / chủ đề',
            'text',
            draft.category || '',
            'required maxlength="100" placeholder="Ví dụ: Tiếng ồn, an ninh, vệ sinh…"',
          ) +
          field(
            'content',
            'Nội dung chi tiết',
            'textarea',
            draft.content || '',
            'required maxlength="10000" placeholder="Mô tả chi tiết vấn đề và mong muốn được hỗ trợ…"',
          ) +
          attachmentField);
    formModal(
      procedure ? 'Đăng ký thủ tục với Ban quản lý' : 'Gửi yêu cầu đến Ban quản lý',
      fields,
      async (data) => {
        const links = String(data.attachment_links || '')
          .split(/\s+/)
          .filter(Boolean);
        const chosen = [...attachmentPicks];
        if (chosen.length + links.length > 5) throw new Error('Tối đa 5 tài liệu đính kèm (tệp và liên kết).');
        if (links.some((link) => !/^https?:\/\/\S+$/i.test(link)))
          throw new Error('Liên kết đính kèm phải bắt đầu bằng http:// hoặc https://.');
        const files = await shrinkPhotos(chosen);
        if (files.reduce((sum, file) => sum + file.size, 0) > ATTACHMENT_BYTES)
          throw new Error('Tổng dung lượng tệp đính kèm tối đa khoảng 450 KB.');
        data.attachments = [
          ...(await Promise.all(files.map(readAttachment))),
          ...links.map((url) => ({ name: url, url })),
        ];
        delete data.attachment_files;
        delete data.attachment_links;
        return saved(
          post('/api/complaints', data),
          procedure ? 'Đã gửi đăng ký thủ tục đến Ban quản lý.' : 'Đã gửi yêu cầu đến Ban quản lý.',
        );
      },
      procedure ? 'Gửi đăng ký' : 'Gửi yêu cầu',
      procedure ? 'Đăng ký gửi xe vui lòng dùng mục Quản lý gửi xe › Gửi đơn đăng ký.' : '',
      'vertical',
    );
    $('#modal-form').dataset.requestKind = kind;
    renderAttachmentPicks();
  }
}
function renderAttachmentPicks() {
  const list = $('#attachment-picks');
  if (!list) return;
  list.innerHTML = attachmentPicks
    .map(
      (file, index) => view`
        <li>
          <span title="${esc(file.name)}">${esc(file.name)}</span>
          <button type="button" class="icon-button" data-action="attachment-remove" data-index="${index}" aria-label="Xoá tệp ${esc(file.name)}">${icon('close')}</button>
        </li>
      `,
    )
    .join('');
}
// The server limits the encoded upload, which leaves about 450 KB of file content.
const ATTACHMENT_BYTES = 440 * 1024;
let attachmentPicks = [];
async function shrinkPhotos(files) {
  const photos = files.filter((file) => file.type.startsWith('image/'));
  const others = files.reduce((sum, file) => sum + (file.type.startsWith('image/') ? 0 : file.size), 0);
  if (!photos.length) return files;
  const budget = Math.max(30 * 1024, Math.floor((ATTACHMENT_BYTES - others) / photos.length));
  return Promise.all(files.map((file) => (file.type.startsWith('image/') ? shrinkPhoto(file, budget) : file)));
}
async function shrinkPhoto(file, budget) {
  if (file.size <= budget) return file;
  const url = URL.createObjectURL(file);
  try {
    const image = await new Promise((resolve, reject) => {
      const element = new Image();
      element.onload = () => resolve(element);
      element.onerror = reject;
      element.src = url;
    });
    for (const longestSide of [1600, 1280, 1024, 800, 640, 480]) {
      const scale = Math.min(1, longestSide / Math.max(image.naturalWidth, image.naturalHeight));
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(image.naturalWidth * scale);
      canvas.height = Math.round(image.naturalHeight * scale);
      const context = canvas.getContext('2d');
      context.fillStyle = '#fff'; // JPEG has no transparency.
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      for (const quality of [0.8, 0.6, 0.45]) {
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality));
        if (blob && blob.size <= budget) {
          return new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', { type: 'image/jpeg' });
        }
      }
    }
  } catch {
    // An undecodable image is sent unchanged and the size check below decides.
  } finally {
    URL.revokeObjectURL(url);
  }
  return file;
}
function readAttachment(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({ name: file.name, data: String(reader.result) });
    reader.onerror = () => reject(new Error(`Không đọc được tệp ${file.name}.`));
    reader.readAsDataURL(file);
  });
}
function attachmentList(list) {
  if (!list?.length) return '';
  const itemsHtml = list
    .map((item) => {
      if (item.url)
        return view`
          <li>${icon('arrow')}<a href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.name || item.url)}</a>
          </li>
        `;
      const image = /^data:image\/(png|jpeg|gif|webp);base64,/.test(item.data || '');
      return view`
        <li>
          ${image ? `<img src="${esc(item.data)}" alt="${esc(item.name)}">` : icon('download')}
          <a href="${esc(item.data)}" download="${esc(item.name)}">${esc(item.name)}</a>
        </li>
      `;
    })
    .join('');
  return view`
    <div class="field wide" style="margin-top:16px">
      <h3 class="detail-title">Tài liệu đính kèm</h3>
      <ul class="attachment-list">${itemsHtml}</ul>
    </div>
  `;
}
function personalForm() {
  const account = state.data.account || {},
    isResident = resident(),
    row = isResident ? state.data.personal || {} : account;
  // Staff accounts may start without contact details, so these stay optional for them.
  const contactRequired = isResident ? 'required ' : '';
  formModal(
    'Chỉnh sửa thông tin cá nhân',
    (isResident
      ? fixedField('Số căn hộ', residentApartmentLabel(row))
      : fixedField('Vai trò', roleNames[account.role])) +
      field(
        'username',
        'Tên đăng nhập',
        'text',
        account.username,
        'required minlength="3" maxlength="20" pattern="[A-Za-z0-9_.\\-]{3,20}" autocomplete="username"',
      ) +
      field(
        'full_name',
        'Họ và tên',
        'text',
        row.full_name,
        'required minlength="2" maxlength="50" autocomplete="name"',
      ) +
      field(
        'email',
        'Email',
        'email',
        account.email || '',
        `${isResident ? 'required pattern="[A-Za-z0-9]+([.][A-Za-z0-9]+)*@[gG][mM][aA][iI][lL][.][cC][oO][mM]" title="Email phải có đuôi @gmail.com" ' : ''}autocomplete="email"`,
      ) +
      field('phone', 'Số điện thoại', 'tel', row.phone || '', `${contactRequired}maxlength="20" autocomplete="tel"`) +
      field('id_card', 'CCCD', 'text', row.id_card || '', 'maxlength="30"'),
    async (data) => {
      if (isResident) data.phone = data.phone || null;
      data.id_card = data.id_card || null;
      const result = await patch('/api/auth/me', data);
      state.user = { ...result.user, full_name: result.profile.full_name };
      state.token = result.token;
      sessionStorage.setItem('ancu_token', result.token);
      closeModal();
      toast('Đã cập nhật thông tin cá nhân.');
      shell();
    },
    'Lưu thông tin',
    isResident
      ? 'Căn hộ đã đăng ký do Ban quản lý quản lý và không thể tự thay đổi.'
      : 'Vai trò do Ban quản lý cấp và không thể tự thay đổi.',
    'vertical',
    false,
  );
}
function passwordForm() {
  formModal(
    'Đổi mật khẩu',
    field(
      'current_password',
      'Mật khẩu hiện tại',
      'password',
      '',
      'required maxlength="128" autocomplete="current-password"',
    ) +
      field(
        'new_password',
        'Mật khẩu mới',
        'password',
        '',
        'required minlength="6" maxlength="30" autocomplete="new-password"',
      ) +
      field(
        'confirm_password',
        'Nhập lại mật khẩu mới',
        'password',
        '',
        'required minlength="6" maxlength="30" autocomplete="new-password"',
      ),
    (data) => saved(post('/api/auth/me/password', data).then(adoptToken), 'Đã đổi mật khẩu thành công.'),
    'Đổi mật khẩu',
    '',
    '',
    false,
  );
}
function userForm(id) {
  const row = state.data.users.find((u) => u.user_id === Number(id));
  formModal(
    `Cập nhật tài khoản ${row.username}`,
    select('role', 'Vai trò', Object.entries(roleNames), row.role),
    (data) => saved(patch(`/api/auth/users/${id}`, data), 'Đã cập nhật vai trò.'),
    'Lưu vai trò',
    'Vai trò được lưu ngay. Người dùng này sẽ bị đăng xuất và thấy vai trò mới khi đăng nhập lại.',
  );
}
function technicianForm(id) {
  const row = state.data.technicians.find((t) => t.technician_id === Number(id));
  // The account is the one the technician registered with; it is shown, never reassigned here.
  const account = state.data.users.find((u) => u.user_id === row.user_id);
  formModal(
    'Cập nhật kỹ thuật viên',
    fixedField('Tài khoản kỹ thuật viên', account ? account.username : 'Chưa liên kết tài khoản') +
      field('full_name', 'Họ và tên', 'text', row.full_name || '', 'required maxlength="120"') +
      select(
        'specialty',
        'Chuyên môn',
        [
          ['general', 'Kỹ thuật tổng hợp'],
          ['parking', 'Quản lý gửi xe'],
          ['payment', 'Dịch vụ & thanh toán'],
        ],
        row.specialty || 'general',
      ),
    (data) => saved(patch(`/api/maintenance/technicians/${id}`, data)),
  );
}
function faqDelete(id) {
  const row = state.data.faqs.find((f) => f.faq_id === Number(id));
  formModal(
    'Xóa chính sách',
    `<div class="field wide">${detail([['Câu hỏi', row.question, true]])}</div>`,
    () => saved(api(`/api/chatbot/faqs/${id}`, { method: 'DELETE' }), 'Đã xóa. Trợ lý không còn dùng nội dung này.'),
    'Xóa chính sách',
    'Trợ lý sẽ ngừng trả lời theo nội dung này ngay sau khi xóa. Không thể hoàn tác.',
  );
}
function knowledgeForm(kind, id) {
  if (kind === 'faqs') {
    const row = id ? state.data.faqs.find((f) => f.faq_id === Number(id)) : {};
    formModal(
      id ? 'Cập nhật nội dung chính sách' : 'Thêm chính sách',
      field('category', 'Danh mục', 'text', row.category || '', 'maxlength="150"') +
        field('question', 'Câu hỏi', 'text', row.question || '', 'required maxlength="1500"') +
        field('answer', 'Nội dung trả lời', 'textarea', row.answer || '', 'required maxlength="10000"'),
      (data) => saved(id ? patch(`/api/chatbot/faqs/${id}`, data) : post('/api/chatbot/faqs', data)),
      undefined,
      'Trợ lý dùng nội dung này ngay sau khi lưu. Hãy viết câu hỏi theo cách cư dân thường hỏi để trợ lý dễ tìm thấy.',
    );
  } else {
    const row = id ? state.data.locations.find((l) => l.location_id === Number(id)) : {};
    formModal(
      id ? 'Cập nhật tiện ích' : 'Thêm vị trí tiện ích',
      field('name', 'Tên tiện ích', 'text', row.name || '', 'required maxlength="200"') +
        field('block', 'Tòa / khu vực', 'text', row.block || '', 'maxlength="200"') +
        field('floor', 'Tầng', 'text', row.floor ?? '', 'maxlength="200"') +
        field('description', 'Mô tả & chỉ dẫn', 'textarea', row.description || '', 'maxlength="5000"'),
      (data) => saved(id ? patch(`/api/chatbot/locations/${id}`, data) : post('/api/chatbot/locations', data)),
    );
  }
}
function exportReport() {
  if ($('#page')?.getAttribute('aria-busy') === 'true') {
    toast('Vui lòng đợi báo cáo cập nhật xong.');
    return;
  }
  const report = state.data.report;
  if (!report) return;
  const csvCell = (value) =>
    `"${String(value ?? '')
      .replace(/"/g, '""')
      .replace(/^[=+@-]/, "'$&")}"`;
  const rows = [
    [
      'Kỳ báo cáo',
      'Tổng doanh thu (VNĐ)',
      'Đã phát hành (VNĐ)',
      'Hóa đơn đã thu (VNĐ)',
      'Điện nước đã thu (VNĐ)',
      'Dịch vụ 6 tháng đã thu (VNĐ)',
      'Vé vãng lai (VNĐ)',
      'Công nợ (VNĐ)',
      'Số hóa đơn',
      'Đã thanh toán',
      'Số khiếu nại',
    ],
    ...(report.items || []).map((r) => [
      r.period,
      r.revenue_amount,
      r.billed_amount,
      r.collected_amount,
      r.monthly_collected_amount,
      r.semiannual_collected_amount,
      r.guest_amount,
      r.outstanding_amount,
      r.invoice_count,
      r.paid_count,
      report.requestsByPeriod?.[r.period]?.complaint_count ?? 0,
    ]),
  ];
  downloadBlob(
    new Blob(['\uFEFF' + rows.map((r) => r.map(csvCell).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' }),
    `bao-cao-doanh-thu-${report.year || thisYear()}.csv`,
  );
}
async function askChat(question) {
  const value = question.trim();
  if (!value) return;
  const form = $('#chat-form'),
    messages = $('#chat-messages');
  if (!form || !messages) return;
  if (form.dataset.busy === 'true') return;
  form.dataset.busy = 'true';
  state.chat.push({ role: 'user', text: value });
  messages.insertAdjacentHTML('beforeend', chatMessage({ role: 'user', text: value }));
  form.reset();
  const loader = document.createElement('div');
  loader.className = 'chat-message chat-loading';
  loader.textContent = 'Đang tìm thông tin…';
  messages.append(loader);
  messages.scrollTop = messages.scrollHeight;
  $('button', form).disabled = true;
  try {
    const result = await post('/api/chatbot/ask', { question: value });
    const reply = { role: 'bot', text: result.answer, source: result.source_title || result.source };
    state.chat.push(reply);
    loader.outerHTML = chatMessage(reply);
  } catch (error) {
    loader.textContent = error.message;
    state.chat.push({ role: 'bot', text: error.message });
  } finally {
    form.dataset.busy = 'false';
    $('button', form).disabled = false;
    messages.scrollTop = messages.scrollHeight;
    $('input', form).focus();
  }
}
function filterTable() {
  const query = ($('#table-search')?.value || '')
      .trim()
      .replace(/\s+/g, ' ')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase(),
    status = $('#table-status')?.value || '',
    type = $('#table-type')?.value || '';
  let visible = 0;
  // Only the page's list: a table inside an open detail dialog is not filtered by the page search.
  $$('#page .data-table tbody tr').forEach((row) => {
    const search = row.dataset.search
      .replace(/\s+/g, ' ')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();
    row.hidden = !(
      search.includes(query) &&
      (!status || row.dataset.status === status) &&
      (!type || row.dataset.type === type)
    );
    if (!row.hidden) visible++;
  });
  const count = $('#page .row-count');
  if (count) count.textContent = `${visible} bản ghi phù hợp`;
}

document.addEventListener('click', async (event) => {
  if (event.target.closest('.sidebar a[href^="#"]')) closeMenu();
  const target = event.target.closest('[data-action]');
  if (!target || target.disabled) return;
  const action = target.dataset.action,
    id = target.dataset.id,
    kind = target.dataset.kind;
  try {
    switch (action) {
      case 'auth-switch':
        authView(target.dataset.register === 'true');
        break;
      case 'toggle-password': {
        const input = document.getElementById(target.dataset.target);
        if (!input) break;
        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        const text = show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu';
        target.setAttribute('aria-pressed', String(show));
        target.setAttribute('aria-label', text);
        target.title = text;
        target.innerHTML = icon(show ? 'eyeOff' : 'eye');
        input.focus({ preventScroll: true });
        break;
      }
      case 'logout':
        logout();
        break;
      case 'menu':
        $('.sidebar').classList.add('open');
        $('.mobile-scrim').classList.add('open');
        break;
      case 'menu-close':
        closeMenu();
        break;
      case 'navigate':
        if (target.dataset.tab) state.tab[target.dataset.route] = target.dataset.tab;
        navigate(target.dataset.route);
        break;
      case 'refresh':
        await renderPage();
        break;
      case 'close-modal':
        closeModal();
        break;
      case 'tab':
        state.tab[state.route] = target.dataset.tab;
        await renderPage();
        break;
      case 'apartment-create':
        await apartmentForm();
        break;
      case 'apartment-edit':
        await apartmentForm(id);
        break;
      case 'apartment-detail':
        await apartmentDetail(id);
        break;
      case 'profile-edit':
        personalForm();
        break;
      case 'password-edit':
        passwordForm();
        break;
      case 'resident-edit':
        await residentForm(id);
        break;
      case 'resident-lock':
        await residentLock(id);
        break;
      case 'resident-unlock':
        await residentUnlock(id);
        break;
      case 'resident-detail':
        await residentDetail(id);
        break;
      case 'resident-apartments':
        await residentApartments(id);
        break;
      case 'resident-apartment-remove':
        await residentApartmentRemove(id, target.dataset.apartment);
        break;
      case 'contract-create':
        await contractForm();
        break;
      case 'contract-edit':
        await contractForm(id);
        break;
      case 'invoice-create':
        await invoiceForm();
        break;
      case 'invoice-detail':
        await invoiceDetail(kind, id);
        break;
      case 'invoice-edit':
        invoiceEdit(kind, id);
        break;
      case 'invoice-pay':
        target.disabled = true;
        await checkout(kind, id);
        break;
      case 'invoice-cash':
        cashPayment(kind, id);
        break;
      case 'invoice-release':
        releasePayment(kind, id);
        break;
      case 'payment-cancel':
        await cancelPayment();
        break;
      case 'bank-transaction-resolve':
        resolveBankTransaction(id);
        break;
      case 'payment-history':
        closeModal();
        state.tab.billing = 'payments';
        navigate('billing');
        break;
      case 'receipt':
        target.disabled = true;
        await receipt(kind, id);
        break;
      case 'vehicle-create':
        await vehicleForm();
        break;
      case 'vehicle-edit':
        await vehicleForm(id);
        break;
      case 'vehicle-renew':
        vehicleRenewForm(id);
        break;
      case 'vehicle-supplement':
        await vehicleSupplementForm(id);
        break;
      case 'guest-create':
        guestForm();
        break;
      case 'guest-edit':
        guestForm(id);
        break;
      case 'service-cut':
      case 'service-restore': {
        const cut = action === 'service-cut',
          service = label(target.dataset.service).toLowerCase();
        if (!window.confirm(`Xác nhận đã ${cut ? 'cắt' : 'cấp lại'} dịch vụ ${service} cho căn hộ?`)) break;
        target.disabled = true;
        await post(`/api/billing/services/${kind}/${id}`, {
          service: target.dataset.service,
          action: cut ? 'cut' : 'restore',
        });
        toast(cut ? `Đã ghi nhận cắt dịch vụ ${service}.` : `Đã ghi nhận cấp lại dịch vụ ${service}.`);
        await renderPage();
        pollNotifications();
        break;
      }
      case 'parking-request':
        requestDrafts = { complaint: {}, registration: {} };
        await parkingRequestForm();
        break;
      case 'parking-rules-modal':
        parkingRulesModal();
        break;
      case 'ticket-create':
        await ticketForm();
        break;
      case 'ticket-edit':
        await ticketForm(id);
        break;
      case 'notice-create':
        await noticeForm();
        break;
      case 'notice-detail':
        await noticeDetail(id);
        break;
      case 'notice-filter':
        state.noticeFilter = target.dataset.filter;
        await renderPage();
        break;
      case 'complaint-create':
        requestDrafts = { complaint: {}, registration: {} };
        attachmentPicks = [];
        await complaintForm();
        break;
      case 'attachment-remove':
        attachmentPicks.splice(Number(target.dataset.index), 1);
        renderAttachmentPicks();
        break;
      case 'complaint-cancel':
        if (!window.confirm('Bạn chắc chắn muốn huỷ yêu cầu này?')) break;
        target.disabled = true;
        await saved(post(`/api/complaints/${id}/cancel`), 'Đã huỷ yêu cầu.');
        break;
      case 'complaint-edit':
        await complaintForm(id);
        break;
      case 'user-edit':
        userForm(id);
        break;
      case 'technician-edit':
        technicianForm(id);
        break;
      case 'faq-create':
        knowledgeForm('faqs');
        break;
      case 'faq-edit':
        knowledgeForm('faqs', id);
        break;
      case 'faq-delete':
        faqDelete(id);
        break;
      case 'location-create':
        knowledgeForm('locations');
        break;
      case 'location-edit':
        knowledgeForm('locations', id);
        break;
      case 'report-export':
        exportReport();
        break;
      case 'chat-suggest':
        await askChat(target.dataset.question);
        break;
      case 'push-enable':
        target.disabled = true;
        await AnCuPush.enable();
        toast('Đã bật thông báo trình duyệt.');
        await renderPage();
        break;
      case 'push-disable':
        target.disabled = true;
        await AnCuPush.disable();
        toast('Đã tắt thông báo trên trình duyệt này.');
        await renderPage();
        break;
    }
  } catch (error) {
    toast(error.message, true);
  } finally {
    target.disabled = false;
  }
});
document.addEventListener('submit', async (event) => {
  const form = event.target;
  if (!['auth-form', 'modal-form', 'chat-form'].includes(form.id)) return;
  event.preventDefault();
  if (form.id === 'chat-form') {
    await askChat(new FormData(form).get('question') || '');
    return;
  }
  const submit = $('[type="submit"]', form),
    errorBox = $('.form-error', form);
  submit.disabled = true;
  errorBox.hidden = true;
  try {
    const data = formValues(form);
    if (form.id === 'auth-form') {
      const registering = form.dataset.register === 'true';
      const result = await post(registering ? '/api/auth/register' : '/api/auth/login', data);
      if (registering) {
        state.token = null;
        state.user = null;
        sessionStorage.removeItem('ancu_token');
        authView();
        $('#auth-form [name=username]').value = data.username;
        toast('Đăng ký thành công. Vui lòng đăng nhập.');
        $('#auth-form [name=password]').focus();
      } else {
        state.token = result.token;
        state.user = result.user;
        sessionStorage.setItem('ancu_token', result.token);
        history.replaceState(null, '', '#overview');
        shell();
      }
    } else if (modalSubmit) {
      await modalSubmit(data);
    }
  } catch (error) {
    if (form.id === 'auth-form' && error.code === 'ACCOUNT_LOCKED') {
      openModal(
        'Tài khoản đã bị khóa',
        view`
          <div class="modal-body">
            <p>Tài khoản của bạn đã bị khóa.</p>
            ${error.reason ? `<p style="margin-top:12px">Lý do: ${esc(error.reason)}</p>` : ''}
            <p style="margin-top:12px">Vui lòng liên hệ Ban quản lý để được hỗ trợ.</p>
          </div>
        `,
        `<div class="modal-footer">${button('Đã hiểu', 'close-modal', '', 'primary')}</div>`,
      );
    } else {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    }
  } finally {
    submit.disabled = false;
  }
});
document.addEventListener(
  'invalid',
  (event) => {
    const input = event.target;
    if (input.dataset?.secret && input.minLength === 6 && input.value && input.value.length < 6) {
      input.setCustomValidity('Mật khẩu cần ít nhất 6 ký tự.');
    } else if (input.name === 'full_name' && input.minLength === 2 && input.value && input.value.trim().length < 2) {
      input.setCustomValidity('Họ tên phải có từ 2 đến 50 ký tự.');
    }
  },
  true,
);
document.addEventListener('input', (event) => {
  if (event.target.setCustomValidity) event.target.setCustomValidity('');
  if (event.target.id === 'table-search') filterTable();
  if (['electricity_usage', 'electricity_unit_price', 'water_usage', 'water_unit_price'].includes(event.target.name))
    updateUtilityPreview();
});
document.addEventListener('change', async (event) => {
  if (
    ['vehicle_type', 'plate_number', 'registered_date', 'registration_months'].includes(event.target.name) &&
    event.target.closest('#modal-form')
  )
    updateParkingFields();
  if (event.target.id === 'field-attachments') {
    const picked = [...attachmentPicks, ...event.target.files];
    if (picked.length > 5) toast('Tối đa 5 tệp đính kèm.', true);
    attachmentPicks = picked.slice(0, 5);
    event.target.value = '';
    renderAttachmentPicks();
  }
  if (event.target.name === 'type' && event.target.closest('#modal-form')?.dataset.requestKind) {
    const form = event.target.form,
      kind = form.dataset.requestKind,
      data = formValues(form);
    requestDrafts[kind] = data;
    try {
      const next = data.type === 'registration' ? 'registration' : 'complaint';
      delete requestDrafts[kind].attachment_files;
      await complaintForm(
        null,
        { ...requestDrafts[next], ...(data.resident_id ? { resident_id: data.resident_id } : {}) },
        next,
      );
    } catch (error) {
      event.target.value = kind;
      toast(error.message, true);
    }
  }
  if (['table-status', 'table-type'].includes(event.target.id)) filterTable();
  if (event.target.id === 'report-year') {
    state.reportYear = Number(event.target.value);
    renderPage();
  }
  if (event.target.id === 'report-group') {
    state.reportGroup = event.target.value;
    renderPage();
  }
});
window.addEventListener('hashchange', () => {
  if (state.user) {
    state.route = location.hash.slice(1) || 'overview';
    renderPage();
  }
});
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    refreshBilling();
    pollNotifications();
  }
});
$('#modal').addEventListener('click', (event) => {
  if (event.target === $('#modal')) {
    const bounds = event.target.getBoundingClientRect();
    if (
      event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom
    )
      closeModal();
  }
});
$('#modal').addEventListener('cancel', (event) => {
  event.preventDefault();
  closeModal();
});
$('#modal').addEventListener('close', () => {
  stopPaymentWatch();
  modalSubmit = null;
  modalReturn = null;
  if (modalBlob) {
    URL.revokeObjectURL(modalBlob);
    modalBlob = null;
  }
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeMenu();
});
(async () => {
  if (state.token) {
    try {
      const result = await api('/api/auth/me');
      state.user = result.user;
      shell();
      return;
    } catch {
      sessionStorage.removeItem('ancu_token');
      state.token = null;
    }
  }
  authView();
})();

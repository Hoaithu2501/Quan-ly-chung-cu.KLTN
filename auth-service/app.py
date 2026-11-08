"""Auth owns users only; resident profile provisioning uses HTTP."""
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
import jwt
from flask import g, request
from werkzeug.security import check_password_hash, generate_password_hash
from shared.auth import require_auth, auth_or_internal
from shared.config import secret
from shared.db import get_db
from shared.http import call_service
from shared.web import create_app as base_app, APIError, body, required, integer, run

def public_user(row):
    return {k:row[k] for k in ('user_id','username','email','phone','role','status','created_at','lock_reason')}

def validate_username(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{3,20}',value):
        raise APIError('Tên đăng nhập gồm 3–20 chữ cái, số, dấu chấm, gạch dưới hoặc gạch ngang.')

def validate_password(value):
    if not isinstance(value,str) or not 6<=len(value)<=30:
        raise APIError('Mật khẩu cần từ 6 đến 30 ký tự.')

def credentials(data):
    required(data, 'username','password')
    validate_username(data['username'])
    validate_password(data['password'])
    if data.get('email'): validate_email(data['email'])

def validate_email(value):
    if not isinstance(value,str) or len(value)>254 or not re.fullmatch(r'[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*@gmail\.com',value,re.IGNORECASE):
        raise APIError('Email phải là địa chỉ hợp lệ có đuôi @gmail.com.')

def required_phone(value):
    if value is None or isinstance(value,str) and not value.strip():
        raise APIError('Vui lòng nhập số điện thoại.')
    if not isinstance(value,str) or len(value)>20:
        raise APIError('Số điện thoại không hợp lệ (tối đa 20 ký tự).')
    return value.strip()

def session(row):
    now = datetime.now(timezone.utc)
    token = jwt.encode({'sub':str(row['user_id']), 'role':row['role'],'username':row['username'],
                        'iss':'qlcc-auth','iat':now,'exp':now+timedelta(hours=8)},secret('JWT_SECRET'),algorithm='HS256')
    return {'token':token, 'user':public_user(row)}

def create_app():
    app = base_app('auth')
    attempts = defaultdict(deque)
    lock = Lock()

    @app.post('/api/auth/login')
    def login():
        data=body(); required(data,'username','password')
        if not isinstance(data['username'],str) or not isinstance(data['password'],str) or len(data['password']) > 128:
            raise APIError('Thông tin đăng nhập không hợp lệ.',400)
        key=(request.remote_addr, data['username'])
        with lock:
            now=time.monotonic()
            while attempts[key] and attempts[key][0] < now-300:
                attempts[key].popleft()
            if len(attempts[key]) >= 10:
                raise APIError('Đăng nhập sai quá nhiều lần. Thử lại sau 5 phút.',429)
            attempts[key].append(now)
        row=get_db().execute('SELECT * FROM users WHERE username=?',(data['username'],)).fetchone()
        valid=False
        if row and row['password_hash'].startswith(('scrypt:','pbkdf2:')):
            valid=check_password_hash(row['password_hash'],data['password'])
        if not valid:
            raise APIError('Sai tên đăng nhập hoặc mật khẩu, vui lòng kiểm tra lại',401)
        if row['status']=='locked':
            return {'error':'Tài khoản đã bị khóa.','code':'ACCOUNT_LOCKED','reason':row['lock_reason']},403
        with lock:
            attempts.pop(key,None)
        return session(row)

    @app.get('/api/auth/me')
    @require_auth()
    def me():
        row=get_db().execute('SELECT * FROM users WHERE user_id=?',(g.user['user_id'],)).fetchone()
        if row is None or row['status']!='active':
            raise APIError('Tài khoản không còn hoạt động.',401)
        return {'user':public_user(row)}

    @app.post('/api/auth/register')
    def register():
        data=body(); credentials(data); required(data,'full_name','email','apartment_code')
        validate_email(data['email']); data['email']=data['email'].lower()
        data['phone']=required_phone(data.get('phone'))
        if not isinstance(data['full_name'],str) or not 10<=len(data['full_name'].strip())<=50:
            raise APIError('Họ tên phải có từ 10 đến 50 ký tự.')
        if data.get('role','resident')!='resident':
            raise APIError('Đăng ký công khai chỉ dành cho cư dân.',403)
        apartment_code=data['apartment_code']
        if not isinstance(apartment_code,str) or not apartment_code.strip() or len(apartment_code.strip())>30:
            raise APIError('Số căn hộ không hợp lệ (tối đa 30 ký tự).')
        apartments=call_service('resident','/api/apartments',internal=True)['items']
        matched=next((a for a in apartments if a['code'].casefold()==apartment_code.strip().casefold()),None)
        if matched is None: raise APIError('Không tìm thấy căn hộ. Vui lòng kiểm tra lại số căn hộ.')
        db=get_db()
        cursor=db.execute('INSERT INTO users(username,password_hash,email,phone,role,status) VALUES(?,?,?,?,?,?)',
            (data['username'],generate_password_hash(data['password']),data.get('email') or None,data.get('phone'),'resident','locked'))
        user_id=cursor.lastrowid
        db.commit()  # Release SQLite write lock before the other service writes.
        try:
            call_service('resident','/api/residents/provision',method='POST',internal=True,
                         json={'user_id':user_id,'full_name':data['full_name'].strip(),'phone':data.get('phone'),'relation_type':'tenant','registered_apartment_code':matched['code']})
        except APIError:
            # No cross-service deletion: a timeout might have committed a profile. Keep account
            # locked for reconciliation through the administration screen.
            raise APIError('Chưa tạo được hồ sơ cư dân. Tài khoản đã khóa; liên hệ Ban quản lý để hoàn tất.',503)
        db.execute("UPDATE users SET status='active' WHERE user_id=?",(user_id,)); db.commit()
        return session(db.execute('SELECT * FROM users WHERE user_id=?',(user_id,)).fetchone()),201

    @app.patch('/api/auth/me')
    @require_auth('resident')
    def update_me():
        data=body()
        if set(data)-{'full_name','id_card','phone','email','username'}:
            raise APIError('Chỉ được cập nhật thông tin cá nhân.')
        db=get_db(); row=db.execute('SELECT * FROM users WHERE user_id=?',(g.user['user_id'],)).fetchone()
        if row is None or row['status']!='active' or row['role']!='resident':
            raise APIError('Tài khoản không còn hoạt động.',401)
        username=data.get('username',row['username'])
        if 'username' in data: validate_username(username)
        if db.execute('SELECT 1 FROM users WHERE username=? AND user_id<>?',(username,row['user_id'])).fetchone():
            raise APIError('Tên đăng nhập đã được sử dụng.',409)
        email=data.get('email',row['email'])
        if 'email' in data:
            validate_email(email); email=email.lower()
        phone=required_phone(data['phone']) if 'phone' in data else row['phone']
        # Release all local writes until the resident service has saved its profile.
        profile_data={k:v for k,v in data.items() if k in ('full_name','id_card')}
        if 'phone' in data: profile_data['phone']=phone
        resident_profile=call_service('resident','/api/residents/me',method='PATCH',json=profile_data)
        db.execute('UPDATE users SET username=?,email=?,phone=? WHERE user_id=?',(username,email,phone,row['user_id'])); db.commit()
        return {**session(db.execute('SELECT * FROM users WHERE user_id=?',(row['user_id'],)).fetchone()),'profile':resident_profile}

    @app.post('/api/auth/me/password')
    @require_auth('resident')
    def change_password():
        data=body(); required(data,'current_password','new_password','confirm_password')
        validate_password(data['new_password'])
        if data['new_password']!=data['confirm_password']:
            raise APIError('Mật khẩu mới và mật khẩu nhập lại không trùng khớp.')
        if not isinstance(data['current_password'],str) or len(data['current_password'])>128:
            raise APIError('Mật khẩu hiện tại không đúng.')
        db=get_db(); row=db.execute('SELECT * FROM users WHERE user_id=?',(g.user['user_id'],)).fetchone()
        if row is None or row['status']!='active' or row['role']!='resident':
            raise APIError('Tài khoản không còn hoạt động.',401)
        if not row['password_hash'].startswith(('scrypt:','pbkdf2:')) or not check_password_hash(row['password_hash'],data['current_password']):
            raise APIError('Mật khẩu hiện tại không đúng.')
        db.execute('UPDATE users SET password_hash=? WHERE user_id=?',(generate_password_hash(data['new_password']),row['user_id']))
        db.commit(); return {'message':'Đã đổi mật khẩu thành công.'}

    @app.get('/api/auth/users')
    @auth_or_internal('admin')
    def users():
        if g.user['role']=='admin':
            active=get_db().execute("SELECT status,role FROM users WHERE user_id=?",(g.user['user_id'],)).fetchone()
            if not active or active['status']!='active' or active['role']!='admin':
                raise APIError('Tài khoản không còn quyền quản trị.',403)
        return {'items':[public_user(r) for r in get_db().execute('SELECT * FROM users ORDER BY user_id')]}

    def admin_active():
        row=get_db().execute('SELECT * FROM users WHERE user_id=?',(g.user['user_id'],)).fetchone()
        if not row or row['status']!='active' or row['role']!='admin':
            raise APIError('Tài khoản không còn quyền quản trị.',403)

    @app.post('/api/auth/users')
    @require_auth('admin')
    def create_user():
        admin_active()
        data=body(); credentials(data)
        role=data.get('role','resident')
        if role not in ('admin','resident','technician'):
            raise APIError('Vai trò không hợp lệ.')
        db=get_db()
        cur=db.execute('INSERT INTO users(username,password_hash,email,phone,role) VALUES(?,?,?,?,?)',
                       (data['username'],generate_password_hash(data['password']),data.get('email') or None,data.get('phone'),role))
        db.commit()
        return public_user(db.execute('SELECT * FROM users WHERE user_id=?',(cur.lastrowid,)).fetchone()),201

    @app.patch('/api/auth/users/<int:user_id>')
    @require_auth('admin')
    def update_user(user_id):
        admin_active(); data=body(); db=get_db()
        row=db.execute('SELECT * FROM users WHERE user_id=?',(user_id,)).fetchone()
        if row is None: raise APIError('Không tìm thấy tài khoản.',404)
        status=data.get('status',row['status'])
        if status not in ('active','locked'): raise APIError('Trạng thái không hợp lệ.')
        if user_id==g.user['user_id'] and status=='locked': raise APIError('Không thể tự khóa tài khoản.')
        reason=data.get('lock_reason',row['lock_reason'])
        if reason is not None and (not isinstance(reason,str) or len(reason)>500):
            raise APIError('Lý do khóa tối đa 500 ký tự.')
        reason=(reason.strip() or None) if reason and status=='locked' else None
        password_hash=row['password_hash']
        if data.get('password'):
            validate_password(data['password'])
            password_hash=generate_password_hash(data['password'])
        db.execute('UPDATE users SET status=?,password_hash=?,lock_reason=? WHERE user_id=?',(status,password_hash,reason,user_id));db.commit()
        return public_user(db.execute('SELECT * FROM users WHERE user_id=?',(user_id,)).fetchone())

    return app

app=create_app()
if __name__=='__main__': run(app,5001)

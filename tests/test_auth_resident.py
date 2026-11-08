import sqlite3
from concurrent.futures import ThreadPoolExecutor
import requests
import pytest


@pytest.fixture
def registration_payload(service_cluster):
    with sqlite3.connect(service_cluster.db_path) as db:
        apartment_code=db.execute('SELECT code FROM apartments WHERE apartment_id=1').fetchone()[0]
    return {'username':'new_resident','password':'123456','full_name':'Cư dân kiểm thử',
            'email':'new@gmail.com','phone':'0901234567','apartment_code':apartment_code}


def test_login_signup_role_and_profile_provisioning(service_cluster,registration_payload):
    cluster=service_cluster
    auth=cluster.urls['auth']
    assert requests.post(auth+'/api/auth/login',json={'username':'admin01','password':'bad'},timeout=10).status_code==401
    login=requests.post(auth+'/api/auth/login',json={'username':'admin01','password':cluster.password},timeout=10)
    assert login.status_code==200 and login.json()['user']['role']=='admin'
    payload={**registration_payload,'password':'LongPassword!123','phone':' 0901234567 '}
    assert requests.post(auth+'/api/auth/register',json={**payload,'role':'admin'},timeout=10).status_code==403
    response=requests.post(auth+'/api/auth/register',json=payload,timeout=10)
    assert response.status_code==201,response.text
    assert response.json()['user']['role']=='resident'
    headers={'Authorization':'Bearer '+response.json()['token']}
    profile=requests.get(cluster.urls['resident']+'/api/residents/me',headers=headers,timeout=10)
    assert profile.status_code==200
    assert profile.json()['full_name']=='Cư dân kiểm thử' and profile.json()['apartment_ids']==[]
    assert profile.json()['registered_apartment_code']==payload['apartment_code']
    assert response.json()['user']['phone']==profile.json()['phone']=='0901234567'
    assert requests.get(cluster.urls['resident']+'/api/apartments/1',headers=headers,timeout=10).status_code==403
    assert requests.post(auth+'/api/auth/register',json=payload,timeout=10).status_code==409


@pytest.mark.parametrize('changes',[
    {'username':'ab'}, {'username':'a'*21}, {'username':'Ngoc Anh'},
    {'email':'new@example.com'}, {'email':'new@gmail.com.example.com'},
    {'email':''}, {'email':None}, {'password':'12345'}, {'password':'a'*31},
    {'full_name':'a'*9}, {'full_name':'a'*51}, {'apartment_code':''}, {'apartment_code':'UNKNOWN'},
    {'phone':None}, {'phone':''}, {'phone':' \t '}, {'phone':123456789}, {'phone':'0'*21},
])
def test_registration_rejects_invalid_fields(service_cluster,registration_payload,changes):
    response=requests.post(service_cluster.urls['auth']+'/api/auth/register',json={**registration_payload,**changes},timeout=10)
    assert response.status_code==400,response.text


def test_registration_requires_phone(service_cluster,registration_payload):
    c=service_cluster
    payload={key:value for key,value in registration_payload.items() if key!='phone'}
    response=requests.post(c.urls['auth']+'/api/auth/register',json=payload,timeout=10)
    assert response.status_code==400,response.text
    assert response.json()['error']=='Vui lòng nhập số điện thoại.'
    with sqlite3.connect(c.db_path) as db:
        assert db.execute('SELECT 1 FROM users WHERE username=?',(payload['username'],)).fetchone() is None


def test_short_password_required_phone_and_own_profile_edit(service_cluster,registration_payload):
    c=service_cluster
    payload={**registration_payload,'username':'a'*20,'phone':'0987654321'}
    response=requests.post(c.urls['auth']+'/api/auth/register',json=payload,timeout=10)
    assert response.status_code==201,response.text
    login=requests.post(c.urls['auth']+'/api/auth/login',json={'username':payload['username'],'password':'123456'},timeout=10)
    assert login.status_code==200
    headers={'Authorization':'Bearer '+login.json()['token']}
    update={'full_name':'Tên đã chỉnh sửa','email':'updated@gmail.com','phone':'0901234567','id_card':'123456789012'}
    response=requests.patch(c.urls['auth']+'/api/auth/me',headers=headers,json=update,timeout=10)
    assert response.status_code==200,response.text
    assert response.json()['profile']['registered_apartment_code']==payload['apartment_code']
    assert response.json()['profile']['full_name']==update['full_name']
    assert response.json()['user']['email']==update['email']
    assert response.json()['user']['phone']==response.json()['profile']['phone']==update['phone']
    for data in ({'role':'admin'},{'user_id':3},{'email':'bad@example.com'}):
        assert requests.patch(c.urls['auth']+'/api/auth/me',headers=headers,json=data,timeout=10).status_code==400
    assert requests.patch(c.urls['resident']+'/api/residents/me',headers=headers,json={'user_id':3},timeout=10).status_code==400
    for service,path in (('auth','/api/auth/me'),('resident','/api/residents/me')):
        for phone in (None,'',' \t ',123456789,'0'*21):
            invalid=requests.patch(c.urls[service]+path,headers=headers,json={'phone':phone,'full_name':'Không được lưu tên'},timeout=10)
            assert invalid.status_code==400,invalid.text
    saved=requests.get(c.urls['resident']+'/api/residents/me',headers=headers,timeout=10).json()
    assert saved['phone']==update['phone'] and saved['full_name']==update['full_name']
    assert requests.get(c.urls['auth']+'/api/auth/me',headers=headers,timeout=10).json()['user']['phone']==update['phone']
    clear=requests.patch(c.urls['auth']+'/api/auth/me',headers=headers,json={'id_card':None},timeout=10)
    assert clear.status_code==200
    assert clear.json()['profile']['id_card'] is None
    assert clear.json()['profile']['phone']==clear.json()['user']['phone']==update['phone']
    assert c.call('auth','/api/auth/me','PATCH',role='admin',json=update).status_code==403
    for name in ('a'*9,'a'*51):
        assert requests.patch(c.urls['auth']+'/api/auth/me',headers=headers,json={'full_name':name},timeout=10).status_code==400
    for name in ('a'*10,'a'*50):
        assert requests.patch(c.urls['auth']+'/api/auth/me',headers=headers,json={'full_name':name},timeout=10).status_code==200


def test_partial_account_update_preserves_legacy_missing_phone(service_cluster):
    c=service_cluster
    with sqlite3.connect(c.db_path) as db:
        db.execute('UPDATE users SET phone=NULL WHERE user_id=3')
        db.execute('UPDATE residents SET phone=NULL WHERE user_id=3')
    response=c.call('auth','/api/auth/me','PATCH',role='resident',json={'username':'legacy.user'})
    assert response.status_code==200,response.text
    assert response.json()['user']['phone'] is None and response.json()['profile']['phone'] is None


def test_login_error_and_locked_reason(service_cluster):
    c=service_cluster
    with sqlite3.connect(c.db_path) as db:
        username=db.execute('SELECT username FROM users WHERE user_id=3').fetchone()[0]
    def login(password):
        return requests.post(c.urls['auth']+'/api/auth/login',json={'username':username,'password':password},timeout=10)
    assert login('wrong').json()['error']=='Sai tên đăng nhập hoặc mật khẩu, vui lòng kiểm tra lại'
    assert c.call('auth','/api/auth/users/3','PATCH',json={'status':'locked','lock_reason':'Cần xác minh thông tin'}).status_code==200
    assert login('wrong').status_code==401
    blocked=login(c.password)
    assert blocked.status_code==403
    assert blocked.json()['code']=='ACCOUNT_LOCKED' and blocked.json()['reason']=='Cần xác minh thông tin'
    assert c.call('auth','/api/auth/users/3','PATCH',json={'status':'active'}).json()['lock_reason'] is None
    assert login(c.password).status_code==200
    c.call('auth','/api/auth/users/3','PATCH',json={'status':'locked'})
    assert login(c.password).json()['reason'] is None


def test_username_and_password_change(service_cluster):
    c=service_cluster
    response=c.call('auth','/api/auth/me','PATCH',role='resident',json={'username':'renamed.user'})
    assert response.status_code==200,response.text
    headers={'Authorization':'Bearer '+response.json()['token']}
    assert c.call('auth','/api/auth/me','PATCH',role='resident',json={'username':'admin01'}).status_code==409
    for changes in ({'current_password':'wrong'},{'confirm_password':'different'},{'new_password':'12345','confirm_password':'12345'},{'new_password':'a'*31,'confirm_password':'a'*31}):
        payload={'current_password':c.password,'new_password':'123456','confirm_password':'123456',**changes}
        result=requests.post(c.urls['auth']+'/api/auth/me/password',headers=headers,json=payload,timeout=10)
        assert result.status_code==400,result.text
    assert c.call('auth','/api/auth/me/password','POST',role='resident',json={'new_password':'123456'}).status_code==400
    for password in ('a'*30,'123456'):
        result=requests.post(c.urls['auth']+'/api/auth/me/password',headers=headers,json={'current_password':c.password if len(password)==30 else 'a'*30,'new_password':password,'confirm_password':password},timeout=10)
        assert result.status_code==200,result.text
    for password,expected in ((c.password,401),('123456',200)):
        result=requests.post(c.urls['auth']+'/api/auth/login',json={'username':'renamed.user','password':password},timeout=10)
        assert result.status_code==expected
    c.call('auth','/api/auth/users/3','PATCH',json={'status':'locked'})
    assert requests.post(c.urls['auth']+'/api/auth/me/password',headers=headers,json={'current_password':'123456','new_password':'new123','confirm_password':'new123'},timeout=10).status_code==401


def test_locked_account_immediately_loses_domain_access(service_cluster):
    c=service_cluster
    assert c.call('resident','/api/apartments',role='resident').status_code==200
    assert c.call('auth','/api/auth/users/3','PATCH',json={'status':'locked'}).status_code==200
    assert c.call('resident','/api/apartments',role='resident').status_code==401
    assert c.call('auth','/api/auth/users/1','PATCH',json={'status':'locked'}).status_code==400
    assert c.call('auth','/api/auth/users',role='resident').status_code==403


def test_contract_lifecycle_scopes_history_and_occupancy(service_cluster):
    c=service_cluster
    apartment=c.call('resident','/api/apartments','POST',json={'code':'TEST-101','block':'Test','floor':1,'area':85.5})
    assert apartment.status_code==201,apartment.text
    aid=apartment.json()['apartment_id']
    payload={'apartment_id':aid,'resident_id':1,'contract_type':'rental','start_date':'2020-01-01','end_date':'2099-12-31'}
    assert c.call('resident','/api/contracts','POST',role='resident',json=payload).status_code==403
    invalid=c.call('resident','/api/contracts','POST',json={**payload,'end_date':'2019-12-31'})
    assert invalid.status_code==400
    created=c.call('resident','/api/contracts','POST',json=payload)
    assert created.status_code==201,created.text
    assert c.call('resident',f'/api/apartments/{aid}',role='resident').json()['status']=='occupied'
    assert c.call('resident','/api/contracts','POST',json=payload).status_code==409
    cid=created.json()['contract_id']
    assert c.call('resident',f'/api/contracts/{cid}','PATCH',json={'status':'terminated'}).status_code==200
    assert c.call('resident',f'/api/apartments/{aid}').json()['status']=='vacant'
    assert c.call('resident',f'/api/apartments/{aid}',role='resident').status_code==403
    history=c.call('resident','/api/contracts',role='resident').json()['items']
    assert any(row['contract_id']==cid and row['status']=='terminated' for row in history)


def test_concurrent_contracts_only_one_active_and_area_validation(service_cluster):
    c=service_cluster
    payload={'code':'TEST-202','block':'Test','floor':2,'area':0}
    assert c.call('resident','/api/apartments','POST',json=payload).status_code==400
    new=c.call('resident','/api/apartments','POST',json={**payload,'area':90}).json()
    contract={'apartment_id':new['apartment_id'],'resident_id':1,'contract_type':'ownership','start_date':'2020-01-01'}
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:c.call('resident','/api/contracts','POST',json=contract),range(2)))
    assert sorted(response.status_code for response in responses)==[201,409]


def test_internal_routes_cannot_be_called_with_regular_jwt(service_cluster):
    c=service_cluster
    payload={'user_id':3,'full_name':'Forged','relation_type':'owner'}
    assert c.call('resident','/api/residents/provision','POST',json=payload).status_code==401
    assert c.call('resident','/api/residents').status_code==200
    assert c.call('resident','/api/residents',role='resident').status_code==403
    assert c.call('resident','/api/residents',role='technician').status_code==403

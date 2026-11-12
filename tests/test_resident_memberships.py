"""BQL confirmation grants household access without changing legal contracts."""
from datetime import date
import sqlite3

from conftest import TEST_SEPAY_KEY, bank_webhook


def make_apartment(c, code):
    response=c.call('resident','/api/apartments','POST',json={
        'code':code,'block':'TEST','floor':1,'area':70})
    assert response.status_code==201,response.text
    return response.json()['apartment_id']


def register_resident(c, apartment_code, username='membership.user'):
    response=c.call('auth','/api/auth/register','POST',json={
        'username':username,'password':'Membership!2026',
        'full_name':'Cư dân cùng căn hộ','email':username.replace('.','')+'@gmail.com',
        'phone':'0901234567','apartment_code':apartment_code})
    assert response.status_code==201,response.text
    user_id=response.json()['user']['user_id']
    response=c.call('resident','/api/residents/me',role='resident',user_id=user_id)
    assert response.status_code==200,response.text
    return user_id,response.json()


def create_invoice(c, apartment_id, kind):
    fees=({'electricity_fee':52000,'water_fee':1000000,'period':'2026-11'}
          if kind=='monthly' else {'service_fee':3000000,'parking_fee':600000,'period':'2026-H2'})
    response=c.call('billing',f'/api/billing/invoices/{kind}','POST',json={
        'apartment_id':apartment_id,'due_date':'2099-12-31',**fees})
    assert response.status_code==201,response.text
    return response.json()


def test_confirmation_scopes_household_invoices_and_history_and_revocation(service_cluster):
    c=service_cluster
    aid=make_apartment(c,'MEMBER-101')
    other=make_apartment(c,'MEMBER-OTHER')
    uid,profile=register_resident(c,'MEMBER-101')
    rid=profile['resident_id']
    second_uid,second_profile=register_resident(c,'MEMBER-101','membership.second')
    c.release_apartments(3)
    contract_resident=c.call('resident','/api/residents/me',role='resident').json()
    response=c.call('resident','/api/contracts','POST',json={
        'apartment_id':aid,'resident_id':contract_resident['resident_id'],'contract_type':'rental',
        'start_date':'2020-01-01','end_date':'2099-12-31'})
    assert response.status_code==201,response.text
    own={kind:create_invoice(c,aid,kind) for kind in ('monthly','semiannual')}
    unrelated={kind:create_invoice(c,other,kind) for kind in ('monthly','semiannual')}
    scope={'role':'resident','user_id':uid}
    assert profile['registered_apartment_code']=='MEMBER-101'
    assert profile['apartment_ids']==profile['verified_apartment_ids']==[]
    assert c.call('resident',f'/api/apartments/{aid}',**scope).status_code==403
    for kind in own:
        assert c.call('billing',f'/api/billing/invoices/{kind}',**scope).json()['items']==[]
        assert c.call('billing',f'/api/billing/invoices/{kind}/{own[kind]["invoice_id"]}',**scope).status_code==403

    path=f'/api/residents/{rid}/apartments'
    response=c.call('resident',path,'POST',json={'apartment_id':aid})
    assert response.status_code==201,response.text
    assert response.json()['apartment_ids']==response.json()['verified_apartment_ids']==[aid]
    assert response.json()['contract_apartment_ids']==[]
    response=c.call('resident',f'/api/residents/{second_profile["resident_id"]}/apartments','POST',
                    json={'apartment_id':aid})
    assert response.status_code==201,response.text
    household_scopes=[scope,{'role':'resident','user_id':second_uid},{'role':'resident'}]
    for member_scope in household_scopes:
        for kind in own:
            rows=c.call('billing',f'/api/billing/invoices/{kind}',**member_scope).json()['items']
            assert own[kind]['invoice_id'] in [row['invoice_id'] for row in rows]
            assert c.call('billing',f'/api/billing/invoices/{kind}/{own[kind]["invoice_id"]}',
                          **member_scope).status_code==200
    assert c.call('resident',f'/api/apartments/{aid}',**scope).status_code==200
    assert c.call('resident',f'/api/apartments/{other}',**scope).status_code==403
    for kind in own:
        rows=c.call('billing',f'/api/billing/invoices/{kind}',**scope).json()['items']
        assert [row['invoice_id'] for row in rows]==[own[kind]['invoice_id']]
        assert c.call('billing',f'/api/billing/invoices/{kind}?apartment_id={other}',**scope).json()['items']==[]
        assert c.call('billing',f'/api/billing/invoices/{kind}/{own[kind]["invoice_id"]}',**scope).status_code==200
        assert c.call('billing',f'/api/billing/invoices/{kind}/{unrelated[kind]["invoice_id"]}',**scope).status_code==403

    response=c.call('billing',f'/api/billing/invoices/monthly/{own["monthly"]["invoice_id"]}/checkout',
                    'POST',json={},**scope)
    assert response.status_code==201,response.text
    order_id=response.json()['order_id']
    for member_scope in household_scopes:
        # Payment tracking is shared by the verified household, not tied to its creator.
        assert c.call('billing',f'/api/billing/orders/{order_id}',**member_scope).status_code==200
    response=c.call('billing','/api/billing/sepay/webhook','POST',json=bank_webhook(response.json()),
                    headers={'Authorization':'Apikey '+TEST_SEPAY_KEY})
    assert response.status_code==201,response.text
    settled=c.call('billing',f'/api/billing/orders/{order_id}',**scope)
    receipts=[settled.json()['receipt_url']]
    for kind in ('semiannual',):
        response=c.call('billing',f'/api/billing/invoices/{kind}/{own[kind]["invoice_id"]}/pay',
                        'POST',json={'payment_method':'cash'})
        assert response.status_code==201,response.text
        receipt=response.json()['receipt_url']
        receipts.append(receipt)
        assert c.call('billing',receipt,**scope).status_code==200
    response=c.call('billing',f'/api/billing/invoices/monthly/{unrelated["monthly"]["invoice_id"]}/pay',
                    'POST',json={'payment_method':'cash'})
    assert response.status_code==201,response.text
    assert c.call('billing',response.json()['receipt_url'],**scope).status_code==403
    payments=c.call('billing','/api/billing/payments',**scope).json()['items']
    assert len(payments)==2 and {row['apartment_id'] for row in payments}=={aid}
    for member_scope in household_scopes:
        rows=c.call('billing','/api/billing/payments',**member_scope).json()['items']
        assert len([row for row in rows if row['apartment_id']==aid])==2

    response=c.call('resident',f'{path}/{aid}','DELETE')
    assert response.status_code==200,response.text
    assert response.json()['apartment_ids']==response.json()['verified_apartments']==[]
    assert c.call('billing','/api/billing/payments',**scope).json()['items']==[]
    for kind in own:
        assert c.call('billing',f'/api/billing/invoices/{kind}',**scope).json()['items']==[]
        assert c.call('billing',f'/api/billing/invoices/{kind}/{own[kind]["invoice_id"]}',**scope).status_code==403
    for receipt in receipts:
        assert c.call('billing',receipt,**scope).status_code==403
    assert c.call('billing',f'/api/billing/orders/{order_id}',**scope).status_code==403
    # Revoking one person does not remove another household member's access.
    for member_scope in household_scopes[1:]:
        assert c.call('billing',f'/api/billing/orders/{order_id}',**member_scope).status_code==200


def test_only_admin_confirms_membership_with_idempotence_and_audit(service_cluster):
    c=service_cluster
    aid=make_apartment(c,'MEMBER-AUDIT')
    uid,profile=register_resident(c,'MEMBER-AUDIT')
    path=f'/api/residents/{profile["resident_id"]}/apartments'
    for role,user_id in (('resident',uid),('technician',None)):
        assert c.call('resident',path,'POST',role=role,user_id=user_id,json={'apartment_id':aid}).status_code==403
        assert c.call('resident',f'{path}/{aid}','DELETE',role=role,user_id=user_id).status_code==403
    assert c.call('resident',path,'POST',json={'apartment_id':aid,'confirmed_by_user_id':uid}).status_code==400
    assert c.call('resident',path,'POST',json={'apartment_id':True}).status_code==400
    assert c.call('resident',path,'POST',json={'apartment_id':99999999}).status_code==404
    assert c.call('resident','/api/residents/99999999/apartments','POST',json={'apartment_id':aid}).status_code==404

    first=c.call('resident',path,'POST',json={'apartment_id':aid})
    assert first.status_code==201,first.text
    membership=first.json()['verified_apartments'][0]
    assert membership['apartment_id']==aid and membership['code']=='MEMBER-AUDIT'
    assert membership['confirmed_by_user_id']==1 and membership['confirmed_at']
    second=c.call('resident',path,'POST',json={'apartment_id':aid})
    assert second.status_code==200 and second.json()['verified_apartments']==[membership]
    with sqlite3.connect(c.db_path) as db:
        assert db.execute('SELECT COUNT(*) FROM resident_apartment_memberships WHERE resident_id=?',
                          (profile['resident_id'],)).fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM apartment_contracts WHERE resident_id=?',
                          (profile['resident_id'],)).fetchone()[0]==0
    assert c.call('resident',f'{path}/{aid}','DELETE').status_code==200
    assert c.call('resident',f'{path}/{aid}','DELETE').status_code==200


def test_membership_revocation_preserves_current_contract_scope_and_date_boundaries(service_cluster,monkeypatch):
    c=service_cluster
    aid=make_apartment(c,'MEMBER-CONTRACT')
    uid,profile=register_resident(c,'MEMBER-CONTRACT')
    rid=profile['resident_id']
    monkeypatch.setattr(c.modules['resident'],'local_today',lambda:date(2030,1,15))
    response=c.call('resident','/api/contracts','POST',json={
        'apartment_id':aid,'resident_id':rid,'contract_type':'rental',
        'start_date':'2030-01-10','end_date':'2030-01-20'})
    assert response.status_code==201,response.text
    cid=response.json()['contract_id']
    path=f'/api/residents/{rid}/apartments'
    assert c.call('resident',path,'POST',json={'apartment_id':aid}).status_code==201
    response=c.call('resident',f'{path}/{aid}','DELETE')
    assert response.json()['verified_apartment_ids']==[]
    assert response.json()['contract_apartment_ids']==response.json()['apartment_ids']==[aid]
    scope={'role':'resident','user_id':uid}
    assert c.call('resident',f'/api/apartments/{aid}',**scope).status_code==200

    monkeypatch.setattr(c.modules['resident'],'local_today',lambda:date(2030,1,20))
    assert c.call('resident','/api/residents/me',**scope).json()['apartment_ids']==[aid]
    monkeypatch.setattr(c.modules['resident'],'local_today',lambda:date(2030,1,21))
    assert c.call('resident','/api/residents/me',**scope).json()['apartment_ids']==[]
    assert c.call('resident',f'/api/apartments/{aid}',**scope).status_code==403
    monkeypatch.setattr(c.modules['resident'],'local_today',lambda:date(2030,1,9))
    assert c.call('resident','/api/residents/me',**scope).json()['apartment_ids']==[]
    with sqlite3.connect(c.db_path) as db:
        assert db.execute('SELECT status,start_date,end_date FROM apartment_contracts WHERE contract_id=?',
                          (cid,)).fetchone()==('active','2030-01-10','2030-01-20')

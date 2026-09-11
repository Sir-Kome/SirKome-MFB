import uuid
from fastapi.testclient import TestClient
import main
from main import app

client = TestClient(app)

def unique_registration_data(label):
    numeric_suffix = str(uuid.uuid4().int % 100000000).zfill(8)
    return {
        'email': f'{label}-{uuid.uuid4().hex}@example.com',
        'phone': f'080{numeric_suffix}',
        'nin': str(uuid.uuid4().int % 100000000000).zfill(11),
        'bvn': str(uuid.uuid4().int % 100000000000).zfill(11),
    }


def register_verified_user(name, email, password, phone, nin, bvn, pin='1234'):
    setup_response = client.post('/auth/send-verification', json={'email': email})
    print('setup', setup_response.status_code, setup_response.json())
    code = main.issue_verification_code(email)
    verify_response = client.post('/auth/verify-email', json={'email': email, 'code': code})
    print('verify', verify_response.status_code, verify_response.json())
    response = client.post('/auth/register', json={
        'name': name,
        'email': email,
        'password': password,
        'phone': phone,
        'nin': nin,
        'bvn': bvn,
        'pin': pin,
    })
    print('register', response.status_code, response.text)
    return response

admin_response = client.post('/auth/login', json={'email': 'admin@sirkome.com', 'password': 'admin1234'})
admin_token = admin_response.json()['token']
reg = unique_registration_data('custmgmt_debug')
resp = register_verified_user('Customer Management User Debug', **reg, password='Strongpass!123', pin='1234')
customer_id = resp.json()['user']['user_id']
print('customer_id', customer_id)
list_response = client.get('/customers', params={'query': 'Customer Management User Debug', 'page': 1, 'per_page': 10}, headers={'Authorization': f"Bearer {admin_token}"})
print('list status', list_response.status_code)
print(list_response.json())

with main.get_connection() as conn:
    rows = conn.execute('SELECT user_id, name, email, account_number, branch_id, is_frozen FROM users WHERE LOWER(name) LIKE ?', ('%customer management user debug%',)).fetchall()
    print('db rows', [dict(r) for r in rows])

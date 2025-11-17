def test_login(client):
    response = client.post('/auth/login', json={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 200
    assert 'access_token' in response.json

def test_login_invalid_credentials(client):
    response = client.post('/auth/login', json={'username': 'wronguser', 'password': 'wrongpass'})
    assert response.status_code == 401

def test_register(client):
    response = client.post('/auth/register', json={'username': 'newuser', 'password': 'newpass'})
    assert response.status_code == 201
    assert response.json['username'] == 'newuser'

def test_register_existing_user(client):
    client.post('/auth/register', json={'username': 'existinguser', 'password': 'pass'})
    response = client.post('/auth/register', json={'username': 'existinguser', 'password': 'pass'})
    assert response.status_code == 400
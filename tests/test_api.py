from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def test_health():
    response=client.get('/api/health')
    assert response.status_code==200
    assert 'live_qloo_available' in response.json()


def test_home():
    assert 'VowBridge' in client.get('/').text
    assert client.get('/assets/styles.css').status_code == 200
    assert client.get('/assets/app.js').status_code == 200


def test_preview():
    response=client.post('/api/plan',json={'group_a':['Arijit Singh','Diljit Dosanjh'], 'group_b':['Bad Bunny','Karol G'], 'preview':True,'duration':120})
    assert response.status_code==200, response.text
    result=response.json()
    assert result['mode']=='synthetic-preview'
    assert result['verification']['passed']
    assert sum(x['minutes'] for x in result['timeline'])==120


def test_invalid_request():
    response=client.post('/api/plan',json={'group_a':[],'group_b':['Karol G'], 'preview':True})
    assert response.status_code==422


def test_no_key_never_claims_live(monkeypatch):
    from app.main import qloo
    old=qloo.key
    qloo.key=''
    try:
        response=client.post('/api/plan',json={'group_a':['Arijit Singh'],'group_b':['Karol G'], 'preview':False})
        assert response.status_code==503
    finally:
        qloo.key=old

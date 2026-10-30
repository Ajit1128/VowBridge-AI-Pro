import httpx
import pytest

from app.qloo import QlooClient, QlooError


@pytest.mark.asyncio
async def test_real_contract_shape_and_private_header():
    seen = []
    def respond(req):
        seen.append(req)
        assert req.headers['X-Api-Key'] == 'test-private-key'
        assert req.url.host == 'hackathon.api.qloo.com'
        if req.url.path == '/search':
            assert req.url.params['types'] == 'urn:entity:artist'
            return httpx.Response(200, json={'results': [{'name':'KAROL G', 'entity_id':'artist-123', 'types':['urn:entity:artist']}]})
        assert req.url.path == '/v2/insights'
        assert req.url.params['filter.type'] == 'urn:entity:artist'
        assert req.url.params['signal.interests.entities'] == 'artist-123'
        assert req.url.params['feature.explainability'] == 'true'
        return httpx.Response(200, json={'results':{'entities':[{'name':'Test musician','entity_id':'artist-456','query':{'affinity':0.82,'explainability':{'entities':[]}}}]}})
    qloo=QlooClient(api_key='test-private-key', transport=httpx.MockTransport(respond))
    artist=await qloo.resolve_artist('Karol G')
    assert artist['id']=='artist-123'
    recommended=await qloo.insights([artist['id']])
    assert recommended[0]['name']=='Test musician'
    assert recommended[0]['id']=='artist-456'
    assert len(seen)==2
    # A repeat request should be served by the private in-memory cache.
    await qloo.insights([artist['id']])
    assert len(seen)==2


@pytest.mark.asyncio
async def test_no_secret_or_invented_results_on_401():
    qloo=QlooClient(api_key='PRIVATE_KEY', transport=httpx.MockTransport(lambda req: httpx.Response(401, json={'error':'unauthorized'})))
    with pytest.raises(QlooError) as error:
        await qloo.resolve_artist('Karol G')
    assert 'PRIVATE_KEY' not in str(error.value)
    assert 'authentication' in str(error.value).lower()


@pytest.mark.asyncio
async def test_unrecognized_name_is_not_silently_selected():
    qloo=QlooClient(api_key='key', transport=httpx.MockTransport(lambda req: httpx.Response(200, json={'results':[{'name':'Different Artist','entity_id':'other','types':['urn:entity:artist']}]})))
    assert await qloo.resolve_artist('Favorite Artist') is None

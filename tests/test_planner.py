import pytest
from app.planner import build_plan, distribute, verify_slots, PlanError
from app.qloo import FixtureQlooClient


@pytest.mark.parametrize('minutes', list(range(60,241,10)))
@pytest.mark.parametrize('vibe', ['balanced','elegant','high-energy'])
def test_duration_allocation(minutes, vibe):
    arr=distribute(minutes,vibe)
    assert len(arr)==10
    assert sum(arr)==minutes
    assert min(arr)>=5 and all(x%5==0 for x in arr)


@pytest.mark.asyncio
async def test_preview_full_plan():
    data=await build_plan(FixtureQlooClient(), ['Arijit Singh','Diljit Dosanjh'], ['Bad Bunny','Karol G'], 180, [],preview=True)
    assert data['verification']['passed']
    assert data['mode']=='synthetic-preview'
    assert sum(a['minutes'] for a in data['timeline'])==180
    assert any(a['side']=='bridge' for a in data['timeline'])
    assert data['taste_evidence']['shared']


@pytest.mark.asyncio
async def test_banned_removes_artist():
    data=await build_plan(FixtureQlooClient(), ['Arijit Singh','Diljit Dosanjh'],['Bad Bunny','Karol G'],180,['Demo Fusion Ensemble','Arijit Singh'],preview=True)
    assert data['verification']['passed']
    assert 'Arijit Singh' not in [a['artist'] for a in data['timeline']]
    assert 'Demo Fusion Ensemble' not in [a['artist'] for a in data['timeline']]


@pytest.mark.asyncio
async def test_fails_closed_when_group_fully_excluded():
    with pytest.raises(PlanError):
        await build_plan(FixtureQlooClient(), ['Arijit Singh'], ['Karol G'], 180, ['Arijit Singh'],preview=True)


def test_verifier_detects_tampering():
    fake=[{'minutes':30,'artist':'Banned','entity_id':'not-in-evidence','side':'a'}]*10
    check=verify_slots(fake,180,{'banned'}, {'artist-1'})
    assert not check['passed']
    assert len(check['warnings'])>=3

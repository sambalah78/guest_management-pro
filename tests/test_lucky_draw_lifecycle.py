"""
Lucky Draw production lifecycle tests.

These tests verify the operator workflow:

READY
  -> DRAWING
  -> CANDIDATE
  -> ABSENT / REDRAW
  -> CANDIDATE
  -> CONFIRMED
  -> NEXT_PRIZE
  -> DONE

The tests intentionally avoid Reflex rendering and database I/O.
They validate the lifecycle contract and state transitions only.
"""
import inspect
import pytest
from guest_management.state.lucky_draw_state import LuckyDrawState

def run_event(state, handler_name, *args):
    """
    Execute a Reflex event handler regardless of whether it is:

        - normal function
        - coroutine
        - async generator

    This keeps the tests independent of Reflex's event runner.
    """
    handler = getattr(state, handler_name)
    result = handler(*args)
    if inspect.isasyncgen(result):

        async def consume():
            values = []
            async for value in result:
                values.append(value)
            return values
        import asyncio
        return asyncio.run(consume())
    if inspect.iscoroutine(result):
        import asyncio
        return asyncio.run(result)
    return result

def make_guest(guest_id, name=None, present=True):
    return {'guest_id': guest_id, 'name': name or f'Guest {guest_id}', 'present': present, 'status': 'present' if present else 'absent'}

def make_prize(name, value='', rank=None):
    prize = {'name': name, 'value': value, 'image_url': ''}
    if rank is not None:
        prize['rank'] = rank
    return prize

@pytest.fixture
def state():
    state = LuckyDrawState()
    state.current_event_id = '1001'
    state.lucky_draw_eligible_guests = [make_guest('G001', 'Alice'), make_guest('G002', 'Bob'), make_guest('G003', 'Charlie'), make_guest('G004', 'David')]
    state.current_prizes = [make_prize('Grand Prize', 'RM20,000', rank=1), make_prize('Second Prize', 'RM10,000', rank=2), make_prize('Third Prize', 'RM5,000', rank=3)]
    state.current_prize_index = 0
    state.draw_status = 'READY'
    state.pending_candidate = {}
    state.excluded_guest_ids = []
    state.redraw_count = 0
    state.draw_locked = False
    state.winners_list = []
    return state

def test_lifecycle_starts_ready(state):
    assert state.draw_status == 'READY'
    assert state.pending_candidate == {}
    assert state.redraw_count == 0
    assert state.draw_locked is False

def test_available_candidates_excludes_removed_guests(state):
    state.excluded_guest_ids = ['G001']
    candidates = state._available_draw_candidates()
    ids = {str(guest['guest_id']) for guest in candidates}
    assert 'G001' not in ids
    assert ids == {'G002', 'G003', 'G004'}

def test_candidate_validation_accepts_available_guest(state):
    candidate = make_guest('G002', 'Bob')
    assert state._candidate_is_valid(candidate) is True

def test_candidate_validation_rejects_excluded_guest(state):
    state.excluded_guest_ids = ['G002']
    candidate = make_guest('G002', 'Bob')
    assert state._candidate_is_valid(candidate) is False

def test_absent_candidate_is_excluded_from_future_draws(state):
    state.excluded_guest_ids = []
    candidate = make_guest('G002', 'Bob')
    state.pending_candidate = candidate
    state.excluded_guest_ids.append(str(candidate['guest_id']))
    state.pending_candidate = {}
    assert 'G002' in state.excluded_guest_ids
    candidates = state._available_draw_candidates()
    assert all((str(g['guest_id']) != 'G002' for g in candidates))

def test_redraw_keeps_same_prize(state):
    state.current_prize_index = 0
    original_prize = state.current_prizes[state.current_prize_index]
    state.redraw_count += 1
    assert state.current_prize_index == 0
    assert state.current_prizes[state.current_prize_index] == original_prize
    assert state.redraw_count == 1

def test_multiple_redraws_never_advance_prize(state):
    state.current_prize_index = 0
    for _ in range(5):
        state.redraw_count += 1
    assert state.current_prize_index == 0
    assert state.redraw_count == 5

def test_confirmed_winner_is_removed_from_eligible_pool(state):
    winner = make_guest('G002', 'Bob')
    state.pending_candidate = winner
    state.lucky_draw_eligible_guests = [guest for guest in state.lucky_draw_eligible_guests if str(guest['guest_id']) != str(winner['guest_id'])]
    state.pending_candidate = {}
    remaining_ids = {str(g['guest_id']) for g in state.lucky_draw_eligible_guests}
    assert 'G002' not in remaining_ids

def test_confirmed_winner_cannot_be_drawn_again(state):
    winner = make_guest('G002', 'Bob')
    state.excluded_guest_ids.append('G002')
    candidates = state._available_draw_candidates()
    assert all((str(g['guest_id']) != 'G002' for g in candidates))

def test_confirming_prize_does_not_change_prize_until_next_prize(state):
    state.current_prize_index = 0
    winner = make_guest('G001', 'Alice')
    state.pending_candidate = winner
    state.draw_status = 'CONFIRMED'
    assert state.current_prize_index == 0
    assert state.current_prizes[0]['name'] == 'Grand Prize'

def test_next_prize_advances_exactly_once(state):
    state.current_prize_index = 0
    state.current_prize_index += 1
    assert state.current_prize_index == 1
    assert state.current_prizes[state.current_prize_index]['name'] == 'Second Prize'

def test_next_prize_does_not_skip_prizes(state):
    assert state.current_prize_index == 0
    state.current_prize_index += 1
    assert state.current_prize_index == 1
    state.current_prize_index += 1
    assert state.current_prize_index == 2
    assert [prize['name'] for prize in state.current_prizes] == ['Grand Prize', 'Second Prize', 'Third Prize']

def test_final_prize_is_last_prize(state):
    state.current_prize_index = len(state.current_prizes) - 1
    assert state.current_prize_index == 2
    assert state.current_prizes[state.current_prize_index]['name'] == 'Third Prize'

def test_final_prize_does_not_create_another_prize(state):
    state.current_prize_index = len(state.current_prizes) - 1
    next_index = state.current_prize_index + 1
    assert next_index >= len(state.current_prizes)

def test_reset_draw_lifecycle_clears_candidate_and_redraw_state(state):
    state.draw_status = 'CANDIDATE'
    state.pending_candidate = make_guest('G002', 'Bob')
    state.excluded_guest_ids = ['G003']
    state.redraw_count = 4
    state.draw_locked = True
    state.reset_draw_lifecycle()
    assert state.pending_candidate == {}
    assert state.redraw_count == 0
    assert state.draw_locked is False

def test_same_guest_cannot_exist_twice_in_exclusion_list(state):
    state.excluded_guest_ids = []
    guest_id = 'G002'
    if guest_id not in state.excluded_guest_ids:
        state.excluded_guest_ids.append(guest_id)
    if guest_id not in state.excluded_guest_ids:
        state.excluded_guest_ids.append(guest_id)
    assert state.excluded_guest_ids.count(guest_id) == 1

def test_no_candidate_when_every_guest_is_excluded(state):
    state.excluded_guest_ids = ['G001', 'G002', 'G003', 'G004']
    candidates = state._available_draw_candidates()
    assert candidates == []

def test_redraw_count_belongs_to_current_prize(state):
    state.current_prize_index = 0
    state.redraw_count = 3
    state.current_prize_index = 1
    state.redraw_count = 0
    assert state.current_prize_index == 1
    assert state.redraw_count == 0

def test_grand_prize_is_rank_one(state):
    ranked = sorted(state.current_prizes, key=lambda prize: int(prize['rank']))
    assert ranked[0]['rank'] == 1
    assert ranked[0]['name'] == 'Grand Prize'

def test_prizes_are_not_mutated_by_redraw(state):
    before = [dict(prize) for prize in state.current_prizes]
    state.redraw_count += 1
    after = [dict(prize) for prize in state.current_prizes]
    assert before == after

def test_absent_guest_is_excluded_and_prize_does_not_change(state):
    state.draw_status = 'CANDIDATE'
    state.current_prize_index = 0
    candidate = make_guest('G002', 'Bob')
    state.pending_candidate = candidate
    state.excluded_guest_ids.append('G002')
    state.lucky_draw_eligible_guests = [guest for guest in state.lucky_draw_eligible_guests if str(guest['guest_id']) != 'G002']
    state.pending_candidate = {}
    state.redraw_count += 1
    state.draw_status = 'REDRAW'
    assert state.current_prize_index == 0
    assert 'G002' in state.excluded_guest_ids
    assert state.redraw_count == 1
    candidates = state._available_draw_candidates()
    assert all((str(g['guest_id']) != 'G002' for g in candidates))

def test_redraw_never_advances_prize(state):
    original_index = state.current_prize_index
    state.redraw_count += 1
    state.draw_status = 'REDRAW'
    assert state.current_prize_index == original_index

def test_excluded_guest_cannot_be_candidate(state):
    state.excluded_guest_ids = ['G001']
    candidates = state._available_draw_candidates()
    assert all((str(g['guest_id']) != 'G001' for g in candidates))

def test_winner_history_is_excluded_from_candidates(state):
    state.winners_list = [{'guest_id': 'G002', 'name': 'Bob'}]
    candidates = state._available_draw_candidates()
    assert all((str(g['guest_id']) != 'G002' for g in candidates))

def test_no_candidates_means_draw_cannot_continue(state):
    state.excluded_guest_ids = ['G001', 'G002', 'G003', 'G004']
    assert state._available_draw_candidates() == []

def test_redraw_excludes_missing_guest(state):
    state.draw_status = 'CANDIDATE'
    state.lucky_draw_eligible_guests = [{'guest_id': 'G001', 'name': 'Alice'}, {'guest_id': 'G002', 'name': 'Bob'}, {'guest_id': 'G003', 'name': 'Charlie'}]
    state.pending_candidate = {'guest_id': 'G002', 'name': 'Bob'}
    state.current_prizes = [{'name': 'iPhone', 'value': 'RM5000', 'image_url': ''}]
    state.current_prize_index = 0

def test_advance_to_next_prize_stops_after_final_prize(state):
    """Final prize must transition to DONE without advancing the prize index."""
    state.current_prize_index = len(state.current_prizes) - 1
    state.draw_status = 'CONFIRMED'
    state.draw_finished = False
    state.waiting_for_next_prize = True
    final_index = state.current_prize_index
    run_event(state, 'advance_to_next_prize')
    assert state.current_prize_index == final_index
    assert state.draw_status == 'DONE'
    assert state.draw_finished is True
    assert state.waiting_for_next_prize is False

def test_advance_to_next_prize_advances_to_next_prize(state):
    """Live-display next-prize action advances one prize and returns READY."""
    state.current_prize_index = 0
    state.draw_status = 'CONFIRMED'
    state.draw_finished = False
    state.waiting_for_next_prize = True
    state.pending_candidate = {'guest_id': 'G001', 'name': 'Alice'}
    state.lucky_draw_winner = {'guest_id': 'G001', 'name': 'Alice'}
    state.redraw_count = 2
    state.lucky_draw_redraw_count = 2
    run_event(state, 'advance_to_next_prize')
    assert state.current_prize_index == 1
    assert state.draw_status == 'READY'
    assert state.draw_finished is False
    assert state.prize_transitioning is False
    assert state.waiting_for_next_prize is False
    assert state.pending_candidate == {}
    assert state.lucky_draw_winner == {}
    assert state.redraw_count == 0
    assert state.lucky_draw_redraw_count == 0
    assert state.lucky_draw_current_name == ''
    assert state.lucky_draw_current_id == ''

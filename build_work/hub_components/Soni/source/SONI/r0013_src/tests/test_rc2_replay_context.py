from src.core.replay_context import ReplayContext


def test_context_clamps_and_is_single_source_of_truth():
    ctx = ReplayContext()
    ctx.configure_study(8)
    state = ctx.select_sonication(3, frame_count=21, initial_frame=7)
    assert (state.sonication_index, state.frame_index, state.frame_count) == (3, 7, 21)
    assert ctx.select_frame(999).frame_index == 20
    assert ctx.select_frame(-99).frame_index == 0


def test_navigation_stops_or_wraps_explicitly():
    ctx = ReplayContext()
    ctx.configure_study(1)
    ctx.select_sonication(0, frame_count=3, initial_frame=2)
    assert ctx.step_frame(1, wrap=False).frame_index == 2
    assert ctx.step_frame(1, wrap=True).frame_index == 0
    assert ctx.step_frame(-1, wrap=True).frame_index == 2


def test_full_state_is_emitted_for_frame_changes():
    ctx = ReplayContext()
    ctx.configure_study(2)
    ctx.select_sonication(0, frame_count=5, initial_frame=0)
    captured = []
    ctx.frameChanged.connect(captured.append)
    ctx.select_frame(4)
    state = captured[-1]
    assert state.sonication_index == 0
    assert state.frame_index == 4
    assert state.frame_count == 5

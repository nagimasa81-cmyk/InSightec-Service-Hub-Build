from src.core.replay_context import ReplayContext
from src.ui.replay_view_coordinator import ReplayViewCoordinator


def test_context_dispatches_one_selection_to_all_registered_views():
    context = ReplayContext()
    coordinator = ReplayViewCoordinator(context)
    seen = []
    coordinator.register("image", lambda state: seen.append(("image", state.frame_index)))
    coordinator.register("temperature", lambda state: seen.append(("temperature", state.frame_index)))
    coordinator.register("spectrum", lambda state: seen.append(("spectrum", state.frame_index)))
    coordinator.register("acoustic", lambda state: seen.append(("acoustic", state.frame_index)))
    context.configure_study(1)
    seen.clear()
    context.select_sonication(0, frame_count=5, initial_frame=0)
    seen.clear()
    context.select_frame(3)
    assert seen == [("image", 3), ("temperature", 3), ("spectrum", 3), ("acoustic", 3)]


def test_refresh_redraws_without_changing_selection():
    context = ReplayContext()
    coordinator = ReplayViewCoordinator(context)
    seen=[]
    coordinator.register("view", lambda state: seen.append(state))
    context.configure_study(1)
    context.select_sonication(0, 2, 1)
    before=context.selection
    seen.clear()
    context.refresh()
    assert seen == [before]
    assert context.selection == before


def test_duplicate_view_registration_is_rejected():
    context=ReplayContext(); coordinator=ReplayViewCoordinator(context)
    coordinator.register("image", lambda state: None)
    try:
        coordinator.register("image", lambda state: None)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate registration was accepted")


def test_reentrant_render_is_queued_and_latest_state_is_not_lost():
    context = ReplayContext()
    coordinator = ReplayViewCoordinator(context)
    seen = []

    def image(state):
        seen.append(("image", state.frame_index))
        if state.frame_index == 1:
            context.select_frame(2)

    coordinator.register("image", image)
    coordinator.register("spectrum", lambda state: seen.append(("spectrum", state.frame_index)))
    context.configure_study(1)
    context.select_sonication(0, 4, 0)
    seen.clear()
    context.select_frame(1)

    assert seen == [("image", 1), ("spectrum", 1), ("image", 2), ("spectrum", 2)]
    assert context.selection.frame_index == 2

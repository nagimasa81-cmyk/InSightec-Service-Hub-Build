from dataclasses import dataclass

from src.core.replay_context import ReplaySelection
from src.core.replay_snapshot import ReplaySnapshotProvider


@dataclass
class FakeFrame:
    replay_index: int
    magnitude_index: int
    temperature_index: int


class FakeSonication:
    pass


def test_snapshot_decodes_once_and_maps_all_sources_from_one_selection():
    calls = []

    def load(sonication, index):
        calls.append((sonication, index))
        return FakeFrame(index, index // 2, index // 3)

    provider = ReplaySnapshotProvider(
        load,
        lambda index, count: index * 3.4,
        lambda index, replay_count, data_count: round(index * (data_count - 1) / (replay_count - 1)),
    )
    sonication = FakeSonication()
    provider.bind_sonication(2, sonication, 5)
    selection = ReplaySelection(sonication_index=2, sonication_count=4, frame_index=6, frame_count=10)

    first = provider.resolve(selection)
    second = provider.resolve(selection)

    assert first is second
    assert len(calls) == 1
    assert first.frame_data.replay_index == 6
    assert first.magnitude_index == 3
    assert first.temperature_index == 2
    assert first.spectrum_index == 3
    assert first.elapsed_seconds == 20.4


def test_binding_new_sonication_invalidates_old_snapshot_and_rejects_stale_selection():
    provider = ReplaySnapshotProvider(
        lambda sonication, index: FakeFrame(index, index, index),
        lambda index, count: float(index),
        lambda index, replay_count, data_count: index,
    )
    provider.bind_sonication(0, FakeSonication(), 3)
    stale = ReplaySelection(sonication_index=0, sonication_count=2, frame_index=1, frame_count=3)
    old = provider.resolve(stale)
    old_generation = old.source_generation

    provider.bind_sonication(1, FakeSonication(), 2)
    assert provider.resolve(stale) is None

    current = ReplaySelection(sonication_index=1, sonication_count=2, frame_index=1, frame_count=3)
    new = provider.resolve(current)
    assert new.source_generation > old_generation


def test_snapshot_maps_each_spectrum_channel_once():
    provider = ReplaySnapshotProvider(
        lambda sonication, index: FakeFrame(index, index, index),
        lambda index, count: float(index),
        lambda index, replay_count, data_count: round(index * (data_count - 1) / (replay_count - 1)),
    )
    provider.bind_sonication(0, FakeSonication(), {"CH0": 5, "CH3": 9})
    selection = ReplaySelection(sonication_index=0, sonication_count=1, frame_index=5, frame_count=10)
    snapshot = provider.resolve(selection)
    assert snapshot.spectrum_index_for("CH0") == 2
    assert snapshot.spectrum_index_for("CH3") == 4
    assert snapshot.spectrum_count == 9

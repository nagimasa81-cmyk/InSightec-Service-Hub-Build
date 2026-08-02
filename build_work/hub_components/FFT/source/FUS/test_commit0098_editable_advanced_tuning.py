from pathlib import Path

APP = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_group_does_not_disable_children():
    assert 'self.comp_advanced_group.setCheckable(False)' in APP
    assert 'self.comp_advanced_group.setEnabled(True)' in APP
    assert 'self.comp_advanced_group.setChecked(False)' not in APP


def test_presets_and_expert_transition_exist():
    assert '["Conservative", "Balanced", "Aggressive", "Expert"]' in APP
    assert 'def _apply_compensation_tuning_preset' in APP
    assert 'def _advanced_compensation_value_changed' in APP
    assert 'self.comp_tuning_preset_combo.setCurrentText("Expert")' in APP


def test_all_advanced_values_feed_preview():
    for token in (
        'mask_expansion=None if self.comp_mask_expansion_spin.value() < 0',
        'donor_halo=None if self.comp_donor_halo_spin.value() == 0',
        'pass_count=None if self.comp_pass_count_spin.value() == 0',
        'strength_override=None if self.comp_strength_override_spin.value() <= 0.0',
        'structure_preservation=self.comp_structure_preservation_spin.value()',
        'frequency_aware=self.comp_frequency_aware_check.isChecked()',
        'harmonic_poisson=self.comp_poisson_check.isChecked()',
        'hermitian_symmetry=self.comp_hermitian_check.isChecked()',
    ):
        assert token in APP


def test_mask_model_rebuild_uses_overrides():
    assert 'selected_mask_expand = profile["mask_expand"] if self.comp_mask_expansion_spin.value() < 0' in APP
    assert 'selected_donor_halo = profile["donor_halo"] if self.comp_donor_halo_spin.value() == 0' in APP
    assert 'selected_passes = profile["model_passes"] if self.comp_pass_count_spin.value() == 0' in APP
    assert 'mask_expand=selected_mask_expand' in APP
    assert 'donor_halo=selected_donor_halo' in APP
    assert 'model_passes=selected_passes' in APP

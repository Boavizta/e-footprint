"""Generic conservation harness for attribution atom builders.

Conservation is the structural gate of the atom model: Σ atoms of a source per life-cycle phase must equal
the source's eager phase total, and — when a source splits a phase into several streams — Σ atoms per
(phase, stream) must equal that stream's footprint. Every source family's task reuses these helpers on its
own fixture models; a missed cell or share fails them loudly.
"""
from efootprint.abstract_modeling_classes.empty_explainable_object import EmptyExplainableObject
from efootprint.core.attribution import atoms_of
from efootprint.core.lifecycle_phases import LifeCyclePhases


def assert_hourly_quantities_equal(test_case, expected, actual, msg=None):
    """Relative-tolerance equality for explainable values — hourly series (compared via the max absolute
    point-wise difference) or period-total scalars (e.g. node_totals_and_links values)."""
    if isinstance(expected, EmptyExplainableObject) and isinstance(actual, EmptyExplainableObject):
        return
    diff = expected - actual
    if isinstance(diff, EmptyExplainableObject):
        return

    def max_abs_magnitude(explainable):
        abs_value = explainable.abs()
        return (abs_value.max() if hasattr(abs_value, "max") else abs_value).magnitude

    reference = expected if not isinstance(expected, EmptyExplainableObject) else actual
    scale = max(max_abs_magnitude(reference), 1e-9)
    test_case.assertAlmostEqual(0, max_abs_magnitude(diff) / scale, places=4, msg=msg)


def eager_phase_footprint(source, phase: LifeCyclePhases):
    return (source.instances_fabrication_footprint if phase == LifeCyclePhases.MANUFACTURING
            else source.energy_footprint)


def sum_atom_values(source_atoms):
    return sum((atom.value for atom in source_atoms), start=EmptyExplainableObject())


def assert_source_atoms_conserve(test_case, source, stream_footprints_by_phase=None):
    """Σ atoms per phase == the source's eager phase total, and, when ``stream_footprints_by_phase``
    ({phase: {stream: footprint}}) is provided, Σ atoms per (phase, stream) == that stream's footprint."""
    for phase in LifeCyclePhases:
        source_atoms = atoms_of(source, phase)
        assert_hourly_quantities_equal(
            test_case, eager_phase_footprint(source, phase), sum_atom_values(source_atoms),
            msg=f"Atoms of {source.name} don't conserve the {phase.value} phase total")
        if stream_footprints_by_phase and phase in stream_footprints_by_phase:
            for stream, stream_footprint in stream_footprints_by_phase[phase].items():
                stream_atoms = [atom for atom in source_atoms if atom.stream == stream]
                assert_hourly_quantities_equal(
                    test_case, stream_footprint, sum_atom_values(stream_atoms),
                    msg=f"Atoms of {source.name} don't conserve the {phase.value} / {stream} stream footprint")

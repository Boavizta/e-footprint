# Task 1 — Engine keeps dependency links current
Repositories and implementation ranges: e-footprint `14b9da47..fa8c5034`.

## Review pointers
- `invalidate` and `ReactiveSlot._compute` in `reactive_core/graph.py`: the cut and the install in `finally`.
- Brief's "Unverified" item: an audit after every integration object-link scenario's reset (60 runs) found no
  stale computed-dict sub-slot with links. The only surviving slot listing a non-system dependent is
  `user_time_spent` of a shared step read by the rolled-back but not deleted journey of `update_usage_journey`
  (a live, cached object, not a dead slot).
- Doc prose also fixed outside the brief's list because it stated the old retention:
  `recomputation/blocks/reactive-slot.html` (failure behaviour) and `recomputation/blocks/computed-dict.html`
  (old dependency edges).
- New removed/deleted-slot tests live in `test_reactive_core.py` (`TestComputedDict`), not
  `test_modeling_object.py`; the branch-switch test builds the integration simple system.

## Open concerns
- The plan's rollback argument (1.3, "Rollback") says a guard that failed "read `server_type` before raising,
  so its links reach it". Not true: getters do not record plain input reads. Calculus edges to inputs come from
  the returned value's ancestry, so a failed attempt is linked only to the computed-slot and relationship reads it
  made. A rejected `fixed_nb_of_instances_validation` is linked only to `raw_nb_of_instances`, and stays void after
  rollback because the rollback wave cannot reach it. Values stay correct (void slots recompute on pull).
  `lifecycle.html#correctness` now says this.
- Defect that predates this task, seen on both engines: with the simple system,
  `ModelingUpdate([[server.fixed_nb_of_instances, SourceValue(1 * u.concurrent)]])` is rejected once, and then the
  same update is **accepted** when repeated (no eager outputs). Old engine: the failed guard compute never clears
  the input node's wave marker, so the rollback wave and the next wave stop at that node. New engine: the failed guard
  is not linked to the input. Interface eager footprint pulls probably still reject it through `nb_of_instances`.
- Accepted semantics, worth knowing for Task 2: a dependent that indexes a departed computed-dict key keeps
  its link to the pruned sub-slot. A later write to that key's inputs no longer reaches it through the sub-slot.

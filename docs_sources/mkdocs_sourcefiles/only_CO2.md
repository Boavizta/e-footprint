# Why does e-footprint only report CO₂e?

**Short answer.** CO₂-equivalent is where measured data and public policy are most mature today, and for a digital product team the risk of mis-prioritizing by looking at carbon alone is small. Multi-criteria support is a desirable expansion, not a closed door.

## Why CO₂e is a defensible starting point

- **Data and policy coverage.** Carbon has by far the best upstream coverage across the measurement tools e-footprint consumes (Boavizta, EcoLogits, grid mixes) and the clearest regulatory framing. Other categories exist, but their data is sparser and less consistent across sources.
- **Low pollution-transfer risk in digital eco-design.** The eco-design levers a product team actually pulls — less compute, fewer devices, longer device lifetimes, lighter pages — generally move every environmental impact in the same direction. Optimizing CO₂e rarely makes water use or resource depletion worse. This breaks down in industrial settings, where material and process choices can trade off across impacts; there, single-criterion would mislead.
- **Concreteness is already hard.** Turning a CO₂e number into something a team can act on is non-trivial. Adding several more numbers per result before the first one lands well would muddy the signal rather than sharpen it.

## Why it's not the end state

Adding water, rare-earth metals, and other categories is clearly desirable. Doing it well requires both upstream data (`{class:Source}` coverage per category) and new modeling primitives to carry multiple impact figures alongside CO₂e through the dependency graph. Both are tractable; neither is free. Contributions on either side are welcome.

See also `{doc:methodology}` for the iterative, start-coarse posture that frames how to use whichever impacts the model exposes.

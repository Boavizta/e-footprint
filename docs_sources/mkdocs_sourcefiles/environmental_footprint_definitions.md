# Environmental footprint — reference definitions

**Scope: digital / ICT** — the domain e-footprint models. Other sectors (notably buildings)
use the same words with different scopes; one warning below, nothing more.

Quotes verbatim, sources dated.

## Lifecycle phases

1. **Manufacturing** (fabrication) — raw-material extraction through finished product.
   **Upstream transport** (materials between extraction, processing and fab stages) is inside
   the manufacturing factors by construction.
2. **Distribution** (downstream transport) — shipping the *finished* equipment to its
   operating site (data center, office, home). Manufacturer PCF reports (Dell, HP, Apple,
   Lenovo) list it as a separate line from manufacturing.
3. **Use** — electricity consumed in operation.
4. **End of life** — collection, disassembly, shredding (RCP D1/D2.1 convention, without
   recycling credits).

**"Embodied" in digital** = cradle-to-gate: the impacts that come with the flesh of the
object — phase 1 only. It never includes distribution (phase 2) nor end of life (phase 4).
When EcoLogits writes "raw material extraction, manufacturing, transportation (denoted as
embodied impacts)", the transportation is upstream logistics.

- EcoLogits: end of life not covered — "we do not cover the end-of-life phase due to data
  limitations on e-waste recycling."
- BoaviztAPI (bottom-up path, used for servers/components): "For now end of life is not taken
  into account." Its fixed-factors fallback is the exception: "all the life cycle is taken
  into account including end of life" — mind double counting if adding phases on top.

**Cross-field warning:** the buildings sector includes delivery-to-site (RICS upfront
embodied, EN 15978 module A4) and even disposal (Carbon Leadership Forum) in "embodied".
Do not import definitions from a web search without checking the sector.

## Sources

- EcoLogits methodology: https://ecologits.ai/latest/methodology/ (checked 2026-08-20)
- BoaviztAPI embedded methodology: https://doc.api.boavizta.org/Explanations/embedded_methodology/ (checked 2026-08-20)
- Carbon Leadership Forum, Embodied Carbon 101: https://carbonleadershipforum.org/embodied-carbon-101/ (checked 2026-08-20)
- Designing Buildings wiki, Embodied carbon (quotes RICS/UKGBC): https://www.designingbuildings.co.uk/wiki/Embodied_carbon (checked 2026-08-20)
- ADEME Base Empreinte (phase-ventilated factors per equipment): https://base-empreinte.ademe.fr/

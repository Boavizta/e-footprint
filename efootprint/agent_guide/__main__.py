"""Print installed modeling guidance or look up an example, class or topic."""
from efootprint.agent_guide.examples import render_examples
from efootprint.agent_guide.guide import render_guide
from efootprint.agent_guide.reference import render_class_reference
from efootprint.agent_guide.topics import read_topic
from efootprint.narrate import narrate, planned


def main(argv=None) -> int:
    narrate.planned("class-metadata:resolve-class", "The requested class name **resolves to its class** in the documentation lookup set.", changes=("agent-guidance#command:dispatch",))
    planned("agent-guidance#command:dispatch", "Dispatch examples, class names and topics through `render_examples`, `render_class_reference`, `read_topic` and `render_guide`, with helpful unknown-name errors.")
    raise NotImplementedError("planned: agent-guidance#command")


if __name__ == "__main__":
    raise SystemExit(main())

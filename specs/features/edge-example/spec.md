# Edge example

The Industrial IoT starter ships in the package, with a group of devices, so that an edge model has
an example to start from wherever the library is installed.

## Problem

The package ships two example models, an e-commerce service and a machine learning workflow, each
with the script that builds it. Neither is an edge model. An agent given a fleet of devices to model
and the installed package rebuilt the whole chain, from the device to the deployment, out of about
ten source files, and grouped its devices in a way that gave the right numbers without anything to
confirm it was the intended one.

An edge example exists: the Industrial IoT starter of the interface, with factory sensors, a server
they upload to and a dashboard for analysts. It lives in the interface, so nobody who installs the
library has it. It also shows no group of devices, which is how a site holding several devices is
counted.

## The change

The Industrial IoT starter becomes an example of the package, script and file, as the e-commerce
starter already is. It gains a group: the sensors of a site counted together, so that the example
shows a deployment that is a site and not a device.

The interface shows the same starter in its picker, read from the package.

## Rules no screen shows

- **example-in-package** The Industrial IoT example is listed with the package's examples, and its
  script and its file are installed with the library.
- **example-builds** The example's script builds the system its file holds.
- **example-shows-a-group** The example counts the devices of a site through a group, and its
  totals follow the number of devices in the group.
- **starter-unchanged-in-picker** The interface's picker lists the Industrial IoT starter with the
  name, the description and the concepts it shows today, and opens it.

## Not doing

- Moving the interface's other starters, the AI chatbot and the GenAI video. They may follow if
  agents need a GenAI example in the package.
- A new edge scenario. The existing one is extended.
- Groups nested in groups in the example.

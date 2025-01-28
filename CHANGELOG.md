# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [9.0.0] 2025-01-29

### Added
- Introduction of the concept of Services with VideoStreaming, WebApplication and GenAIModel classes, and their associated jobs VideoStreamingJob, WebApplicatioJob and GenAIJob.
- BoaviztaCloudServer class to replace the Boavizta builder functions. This change allows for better calculation graph tracking and to be able to update BoaviztaCloudServer instances attributes and benefit from the recomputation logic.
- GPUServer class with its compute attribute in new unit gpu.
- All e-footprint objects now have default values and a from_defaults method.

### Changed
- Data upload and data download have been suppressed in the Job class and replaced by a single data_transferred attribute. This removes the ambiguity around the notion of data upload and download (is it in reference to the device ? to the server ?) and simplifies the model.
- UserJourney and UserJourneyStep classes have been renamed UsageJourney and UsageJourneyStep to better reflect their generic purpose.
- The notion of cpu needed in jobs and servers has been abstracted to compute to better handle different compute types like cpu and gpu.

## [8.2.1] 2025-01-07

### Fixed
- Wrap ModelingObjects into ContextualModelingObjectAttribute and lists into ListLinkedToModelingObj in json_to_system function so that all ModelingObject attributes inherit from ObjectLinkedToModelingObj class. This change fixes recomputation of ModelingObject or list attributes when the system is loaded from a json file.

## [8.2.0] 2025-01-06

### Changed
- Simulation object changed into ModelingUpdate. This change allows the use of the ModelingUpdate object anywhere the optimized recomputation logic needs to be called + it allows for the possibility to make optimized batch changes on the baseline model. This change will allow greater flexibility in the evolution of e-footprint’s input data structure by removing the need to duplicate the recomputation logic for each input data structure.

## [8.1.0] 2024-12-20

### Added
- Possibility to make simulations of changes in the future. A simulation is a date in the future and the list of changes that will happen at this date. The changes can be the addition of a new object, the deletion of an object, the modification of an object attribute, the addition of a new link between objects, the deletion of a link between objects, the modification of a link between objects. The simulation can be run on a system to see the impact of the changes on the system's carbon footprint.

## [8.0.1] 2024-11-12

### Fixed
- When the fixed_nb_of_instances attribute of an OnPremise server or a Storage object was set to None, the calculation graph wouldn’t be tracked and so no uptstream recomputation was triggered if the fixed_nb_of_instances attribute was updated. Now, the fixed_nb_of_instances attribute is set to EmptyExplainableObject by default, which allows to build the calculation graph and recompute attributes that depend of the fixed_nb_of_instances logic, when the fixed_nb_of_instances attribute is updated.
- OnPremise and Storage’s update_nb_of_instances used to break when raw_nb_of_instances was EmptyExplainableObject. Now fixed.

## [8.0.0] 2024-11-04

### Changed
- A Storage object can now be linked to only one Server object and gets its average_carbon_intensity and power_usage_effectiveness attributes from its server. This change simplifies the hardware part of the model and makes it more realistic.

### Added
- Storage has now an attribute "fixed_nb_of_instances" to specify the number of instances of a storage object like it's already implemented for servers.
- New time builders have been added
- Boavizta builders have been enriched (mainly the Storage part).


## [7.0.1] 2024-10-28

### Fixed
- Object relationship graph. Now links are shown between objects even if there is an ignored object in the chain of links.
- Network energy footprint calculation logic. If a job was linked to a usage pattern not linked to the Network, the calculation would raise a KeyError. Now, the Network energy footprint calculation logic only loops on usage patterns common to jobs and Network and can handle such cases.

### Changed
- Simplify __repr__ method of ModelingObject class to make it return less characters.

## [7.0.0] 2024-10-7
- Storage is now an attribute of server objects. This change simplifies the hardware part of the model and makes it more realistic.

## [6.0.2] 2024-10-02

### Fixed
- Make copies of event duration values before converting them to hour to use them in calculations, not to convert the original value in place.

## [6.0.1] 2024-09-27

### Fixed
- Label has been added in System class to display its calculations in the graph.

## [6.0.0] 2024-09-27

### Added
- Introduce in job Object the attribute "data_stored". This attribute is the amount of data stored by the job in the storage. It can be negative if the job deletes data from the storage.

## [5.0.0] 2024-09-20

### Changed
- Supress Service object and transfer its functions to Server and Storage. Now jobs directly link to servers and storage. This change simplifies e-footprint’s object structure and removes the ambiguity surrounding the term Service.

## [4.0.0] 2024-09-11

### Changed
- Major update: usage is now described as hourly number of user journey starts. This allows for a chronological modeling and later will allow simulation of changes in the future.
- Server electricity consumption now depends on server load.

## [3.0.0] 2024-07-29

### Changed
- Suppress DevicePopulation object and transfer its functions to UsagePattern for simplification of object structure. This change removes an ambiguity around the notion of visits and number of devices: by removing the notion of devices and users from the model, only user journey frequency is kept and there remains no confusion possible between user journey frequency and user journey frequency per user (which has disappeared).
- Minor import order refactoring to comply better with PEP8 guidelines.

### Added
- Content in the documentation.

## [2.1.6] 2024-06-13

### Fixed
- Force ModelingObject and ExplainableObject ids to start with a letter and not contain backslashes.

## [2.1.5] 2024-06-06

### Fixed
- Make ModelingObject and ExplainableObject ids css escaped.

## [2.1.4] 2024-05-17

### Fixed
- System footprints by category and object graph legend aligns to the right if server impact is bigger than devices impact

## [2.1.3] 2024-05-16

### Changed
- Don’t round up the number of users in parallel as it creates very wrong results when there are few users in parallel.

## [2.1.2] 2024-05-16

### Fixed
- "ton" unit to "tonne" because in Pint a ton is equal to 2000 pounds and not 1000 kg.

## [2.1.1] 2024-05-16

### Fixed
- Remove useless title parameter from EmissionPlotter class.

## [2.1.0] - 2024-05-15

### Added
- Possibility to export raw html in plot_footprints_by_category_and_object System method.
- Possibility to resize plot_footprints_by_category_and_object output’s graph.

### Changed
- Improve emission diffs graph and harmonize its colors and legend with the plot_footprints_by_category_and_object graph.

## [2.0.5] - 2024-04-16

### Fixed
- In function json_to_system make sure that System ids don’t change at system loading time.

## [2.0.4] - 2024-04-16

### Fixed
- In function json_to_system make recompute Systems by using their __init__ and after_init methods to make sure that all their internal variables are initialized.

## [2.0.3] - 2024-04-15

### Fixed
- In function json_to_system make sure that all objects unlinked to a system compute their calculated attributes, and not only Services.

## [2.0.2] - 2024-04-15

### Fixed
- Loading of system from json when there is a service that is not linked to a usage pattern (case when a service is installed on a server but doesn’t receive requests).

## [2.0.1] - 2024-04-12

### Fixed
- Setup of previous attribute value for lists at e-footprint object initiation when using the json_to_system function, so that recomputation works fine when list attributes are updated.

## [2.0.0] - 2024-04-06

### Added
- Job object for the encapsulation of request information, to introduce the possibility to have multiple request to services for a single user journey step.
- Job builders from [Boavizta’s ecobenchmark](https://github.com/Boavizta/ecobenchmark-applicationweb-backend) data

## [1.3.2] - 2024-03-20

### Added
- Characterics of objects are now displayed when hovering over a node in an object relationship graph (to create such a graph use the object_relationship_graph_to_file method of the ModelingObject class).

## [1.3.1] - 2024-03-16

### Fixed
- set modeling obj container of ExplainableObjects created through json_to_system function so that accessing their id property doesn’t trigger a ValueError because of a null modeling_obj_container.
- Fixed ExplainableObject’s set_label method so that it doesn’t duplicate "from source.name" when reconstructing the object with the json_to_system function.

## [1.3.0] - 2024-03-15

### Added
- plot_emission_diffs method to System for easy analysis of System changes.
- Tutorial to documentation.
- System changes analysis in tutorial.

## [1.2.2] - 2024-03-08

### Added
- notebook parameter in object and calculus graph generation functions + set cdn_resources=in_line in pyvis Network objects to silence jupyter warning
- to_json, __repr__ and __str__ methods in ExplainableObject subclasses and ModelingObject.

### Changed
- quickstart as jupyter notebook

## [1.2.1] - 2024-02-29

### Added

### Changed

### Fixed
- Possibility to use fixed_nb_of_instances with the on_premise_server_from_config builder.

## [1.2.0] - 2024-02-29

### Added
- Possibility to specify the fixed number of on premise instances through the fixed_nb_of_instances attribute
- Doc generation logic with mkdocs. Here is the link to the [e-footprint documentation](https://publicissapient-france.github.io/e-footprint).

### Changed

### Fixed
- File paths in graphs generating functions

## [1.1.9] - 2024-02-12

### Added
- system_to_json and json_to_system functions in api_utils package in order to be able to save a system as json file and then load it and run computations. Saving of intermediate calculations will be implemented in another release.

### Changed
- calculated_attributes are now a property method instead of an attribute, to facilitate system to json and json to system flow.
- calculated attributes of System class are now properties for a more coherent syntax.
- Countries class is now made of country generator objects to avoid unwanted link between systems that would share a common country.
- System now inherits from ModelingObject

## [1.1.8] - 2024-02-02

### Added
- calculus_graph_to_file function in ExplainableObject to more easily create calculus graphs
- object_relationship_graph_to_file function in ModelingObject to more easily create object relationship graphs
- Generic self_delete method for ModelingObjects

### Changed
- System now inherits from ModelingObject

## [1.1.7] - 2024-01-29

### Added

### Changed
- Put ModelingObject list update logic in ModelingObject __setattr__ method
- Name server CPU capacity cpu_cores instead of nb_of_cpus to make it clearer

### Fixed
- Set input attribute label at attribute setting time and not after. Avoids a bug when the input attribute of a ModelingObject is the result of a calculation and hence has no label.

## [1.1.6] - 2024-01-29

### Added

### Changed
- Put all the naming logic that was in SourceValue and SourceObject classes into ExplainableObject

### Fixed
- Boaviztapi server builders to accommodate for Boaviztapi update. 

## [1.1.5] - 2024-01-18

### Added
- plot_footprints_by_category_and_object method to the System object, to display the CO2 emission breakdown by object type (server, storage, network, end user devices), emission types (from electricity and from fabrication), and by objects within object types (for example, the share of each server within the servers).
- Default object builders that return a new object each time.
- Server builders based on the [Boavizta API](https://github.com/Boavizta/boaviztapi).

### Changed
- Suppress the notion of server_ram_per_data_transferred to simply directly specify the ram_needed for UserJourneyStep objects.
- More explicity quickstart with all attributes explicitely named and set.

### Fixed


## [1.1.4] - 2023-11-13

### Added

### Changed

### Fixed
- Don’t write logs to file by default to avoid unnecessary storage usage + be compliant with Streamlit Cloud security.

## [1.1.3] - 2023-11-13

### Added

### Changed

### Fixed
- Put data folder (for logs) inside module and set default log level to INFO.

## [1.1.2] - 2023-11-10

### Added
- Missing tests.
- Optimisations that can lead to 10x+ improvements in complex systems initiation speed.

### Changed
- Clarification of vocabulary in ExplainableObject class: an ExplainableObject now links to its children, to follow a genealogical logic.
- Graph colors for more color blindness friendliness. Reach out if this is still unsatisfactory !

### Fixed
- Object link recomputation logic: the launch_attributes_computation_chain function in the [ModelingObject class](./efootprint/abstract_modeling_classes/modeling_object.py) now allows for a breadth first exploration of the object link graph to recompute object attributes in the right order. 
 
## [1.1.1] - 2023-11-03

### Added

### Changed
 
### Fixed
- Possibility to have a null service as input for user journey steps (in cases when the user simply uses the device without any service call).
- UserJourney’s add_step method didn’t trigger setattr because of the use of the self.uj_steps.append(new_step) syntax, and hence didn’t trigger the appropriate recomputation logic. Fixed by replacing it with the self.uj_steps = self.uj_steps + [new_step] syntax.
- [graph_tools](./efootprint/utils/graph_tools.py) module doesn’t depend any more on special selenium screenshot functions that are only used during development. Such functions have been moved to the [dev_utils](./efootprint/utils/dev_utils) package that only contains modules not used in the project because they are work in progress or dev helper functions.
- Fixed the [convert_to_utc_test](./tests/abstract_modeling_classes/test_explainable_objects.py) that had broken because of time change  
 
## [1.1.0] - 2023-10-26

State of project at time of open sourcing.

### Added
Full optimization of recomputation whenever an input or object relationship changes.
# OntoRXN-Tools
Diego Garay-Ruiz, 2022

Institute of Chemical Research of Catalonia, Prof. Carles Bo Research group

## Overview
**ontorxn-tools** is a Python library developed to automate the generation of knowledge graphs for reaction networks based on the [OntoRXN](https://gitlab.com/dgarayr/ontorxn) ontology. Both network topology and calculations can be extracted from the Create module of [ioChem-BD](https://www.iochem-bd.org), in the form of *reports*. More details are available on the preprint at [ChemRxiv](https://doi.org/10.26434/chemrxiv-2022-3sqwp).

The bundled **py-ioChem** package handles this ioChem-BD connection, through modules to communicate with the REST API (ReportAPIManager), handle DOT-formatted graphs (GraphManager) and process CML files (CMLtoPy)

Be sure to install **py-ioChem** *first* in order to fulfill the dependencies of ontorxn-tools.

Additionally, the **ontorxn-user** accompanying module provides assistance tools to build and run SPARQL queries over knowledge graphs.

## Basic usage
A command-line interface is provided, through the `ontorxn_cli.py` script.

```bash
$python ontorxn_cli.py --ontofile ONTO --graphfile GRAPH --reportid RID --loginfile LOGIN
```

The arguments are:
- *--ontofile*. Path to the *OntoRXN.owl* file is stored.

- *--graphfile*. Path to the DOT file containing the graph downloaded from ioChem-BD.

- *--reportid*. Identifier for the report in ioChem-BD.

- *--loginfile*. INI file containing login details for the REST API and URLs for the endpoints.

	```INI
	[URL]
	
	URL_REST_REPORT = ENDPOINT/api/report/ 
	
	URL_REST_CALC = ENDPOINT/api/calculation/
	
	[ioChem]
	
	my_iochem_passwd = user-email:user-password  [base64 encoding]
	```

- *--fetchfiles*. When present, download the CML files embedded in the report.
- *--collapse*. When present, unify all nodes that have the same name.
- *--reasoner*. When present, run the default reasoner in owlready2 on the KG.

The wrapper function `knowledge_graph_gen()` is called with the CLI arguments to generate the KG.

## Detailed usage
If CLI options are not enough, it is possible to get more control by building a custom Python script. The required steps are:

### Graph processing
- `GraphManager.graph_read_split()` takes the DOT graph from ioChem-BD, cleans up and formats the fields it contains (as most information will be indeed fetched from the report) and, if several disconnected subgraphs are present, splits them accordingly.
- A `ReportAPIManager.ReportHandler()` object is passed the report ID and the login details to fetch all properties in the report. Then, `GraphManager.formula_mapper()` uses these properties to map the formulas in the report to the graph.
- If requested, `ReportHandler.batch_cml_dump()` downloads all CML files associated with the report, named after their calcId.

### Ontology management
- An `OntoRXNWrapper()` object is instantiated to load the *OntoRXN.owl* file from the provided route.

### Knowledge graph generation
- `calc_instantiation()` goes along all the calculations in the report and instantiates a **CompCalculation** for each. XSL stylesheets are used to fetch requested fields from the CML file and add them to the CompCalculations.
  - The `CMLtoPy.xslt_parsing()` function is employed. By now only the CML-Gaussian stylesheet is provided, but in the future the stylesheet shall be chosen according to the program specified in the CML.
  - For simple fields, CML/OntoRXN field binding is specified in the `resources/parsing_rules.dat` file, specifying **ontology_property*, **cml_field_name**, *data_type*, **cml_unit_field**.
  - More complex fields are hard-coded: e.g. method and basis are set up in an *InitializationModule* object, molecules are generated as *gc.Molecule* entities containing *gc.Atom* individuals with X, Y and Z positions, etc.
- In the same function, the *names* of the calculations (corresponding to the name in the report specification) are used to identify unique species, generating the corresponding **ChemSpecies** entities.
- `structure_generator()` goes along the graph(s) read from the DOT file, first generating **NetworkStage** entities for every *node* in the graph. For these nodes, the *formula* field is checked to map every stage with all the pre-generated **ChemSpecies** that belong to it.
- In the same function, *edges* are then traversed, generating the **ReactionStep** entities, that are directly mapped to the stages of the connected nodes. Also, if a TS structure is associated to the edge, the corresponding **NetworkStage** for the TS is built and mapped to the step via *hasTS*.
- The `OntoRXNWrapper.construct_query_applier()` wrapper applies CONSTRUCT SPARQL queries over the knowledge graph to explicitly add relationships that are not well defined just by OWL statements, such as the connectivity between steps or the mapping of InChIs to species instead of calculations.

Some aspects of the workflow are still under development (e.g. specific CML - ontology mappings, addition of new fields...), but the general function structure explained in this section shall remain consistent.

## Query management with ontorxn-user
The additional **ontorxn-user** module provides some tools to simplify SPARQL querying on the OntoRXN-based knowledge graphs. The `QueryCore()` class supplies a Python-like interface to query building, including *Select*, *Where* and *Prefix* attributes to handle, respectively, the SELECT, WHERE and PREFIX keywords. Additionally, an *After* argument allows to add GROUP BY, LIMIT, ORDER BY... arguments that are specified *after* selection of results.

Therefore, clauses can be handled as strings (SELECT) or lists of strings (WHERE, PREFIX and any after clause), with the class managing the eventual transformation to a valid SPARQL string that can be run against a RDF database. In the *ontorxn-tools* workflow, this database is accessed through the *OntoRXNWrapper.MainWorld* attribute, with the `.query()` function accepting directly the SPARQL string.

Additionally, the `QueryManager()` class provides some convenience function and dictionaries for specific, common queries on OntoRXN-based KGs, like mapping properties stored as calculation results or pre-assigning the OntoRXN and Gainesville Core (rxn and gc) namespaces.

Other functions in the module aim to directly run queries regarding energies or connectivities of a knowledge graph on the instantiated `OntoRXNWrapper()`, or directly reconstruct the 'basic' network graph from the KG information.

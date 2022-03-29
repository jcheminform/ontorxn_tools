# OntoRXN-Tools
Diego Garay-Ruiz, 2022

Institute of Chemical Research of Catalonia, Prof. Carles Bo Research group

## Overview
**ontorxn-tools** is a Python library developed to automate the generation of knowledge graphs for reaction networks based on the [OntoRXN](https://gitlab.com/dgarayr/ontorxn) ontology. Both network topology and calculations can be extracted from the Create module of [ioChem-BD](https://www.iochem-bd.org), in the form of *reports*. More details are available on the preprint at [ChemRxiv](https://doi.org/10.26434/chemrxiv-2022-3sqwp).

The bundled **py-ioChem** package handles this ioChem-BD connection, through modules to communicate with the REST API (ReportAPIManager), handle DOT-formatted graphs (GraphManager) and process CML files (CMLtoPy)

Be sure to install **py-ioChem** *first* in order to fulfill the dependencies of ontorxn-tools.

Additionally, the **ontorxn-user** accompanying module provides assistance tools to build and run SPARQL queries over knowledge graphs.

## Core functionalities
### Network definition
Direct reading and processing of the DOT-formatted graphs generated for reports in ioChem-BD.
### Calculation mapping
The REST API of ioChem-BD is employed to link and extract the calculations pertaining to the report in which the network is defined, by passing the corresponding reportId parameter.
### Property extraction
XSL stylesheets (in `stylesheets/`) take requested fields from CML files in ioChem, which are then translated to properties in the *CompCalculation* entities of the knowledge graph through a set of parsing rules (in `resources/`)
### KG input/output
The `OntoRXNWrapper()` class can be used to facilitate both the generation of new knowledge graphs and the processing of existing KG entities (e.g. SPARQL querying)
### Command-line interface
The `ontorxn_cli` script can be used to run simple knowledge graph generation directly from the command line, providing the directory containing the OntoRXN ontology, the DOT graph, the report ID and a file with login data for the REST API.

'''Diego Garay-Ruiz, 2022
Collection of Python functions to manage and generate OntoRXN-compliant knowledge
graphs.'''

from py_iochem import ReportHandler
from py_iochem import CMLtoPy as cml
from py_iochem import GraphManager
import re
import os.path
import networkx as nx
from networkx.drawing.nx_pydot import read_dot
from owlready2 import *
import rdflib
from rdflib.extras.external_graph_libs import rdflib_to_networkx_digraph
from operator import itemgetter

# SPARQL queries for linking entities that cannot be directly inferred

ontorxn_queries = {
	"step_linker":"""
	PREFIX rxn: <http://www.semanticweb.com/OntoRxn#>
	CONSTRUCT { ?stepA rxn:isConnectedWith ?stepB .
	?stepB rxn:isConnectedWith ?stepA }
	WHERE { ?stepA rxn:hasNode ?nodeX .
			?stepB rxn:hasNode ?nodeX .
			FILTER (?stepA != ?stepB)}
	""",
	"inchi_mapper":"""
	PREFIX rxn: <http://www.semanticweb.com/OntoRxn#>
	CONSTRUCT { ?spcX rxn:hasInChI ?inchiX }
	WHERE { SELECT ?spcX ?inchiX WHERE {
		?spcX rxn:hasCalculation ?calcX .
		?calcX rxn:hasInChI ?inchiX }
	GROUP BY ?spcX }
	"""}

class OntoRXNWrapper:
	'''Class to simplify I/O on ontology processing, handling the owlready2.Ontology object, the rdflib World (which can
	be queried directly) and the namespaces'''
	
	def __init__(self,ontology=None):
		self.Ontology = ontology
		# Namespace dependencies
		self.Namespace = {}

	def process_onto(self):
		'''Basic processing for OntoRXN (clean ontology or instantiated graphs): prepare imports,
		namespaces and RDFLib world'''
		set_datatype_iri(float, "http://www.w3.org/2001/XMLSchema#float") 
		occ = self.Ontology.imported_ontologies[0].load()
		mop = self.Ontology.imported_ontologies[1].load()
		self.OntoCompChem = occ
		# Prepare namespaces
		namespace_dict = {
			"gc":occ.get_namespace("http://purl.org/gc/"),
			"osp":occ.get_namespace("http://theworldavatar.com/ontology/ontospecies/OntoSpecies.owl#"),
			"pt":occ.get_namespace("http://www.daml.org/2003/01/periodictable/PeriodicTable.owl"),
			"term":occ.get_namespace("http://purl.org/dc/terms/"),
			"qudt":occ.get_namespace("http://data.nasa.gov/qudt/owl/qudt#"),
			"occ":occ,
			"onto":self.Ontology
		}
		self.Namespace.update(namespace_dict)
		self.MainClassList = list(self.Ontology.classes())
		return None
		
	def load_ontorxn(self,ontology_path):
		'''Custom function to load a clean instance OntoRXN and its local imports.
		Input:
		- ontology_path. String, full path to the OntoRXN instance to load.'''
		onto_path.extend([ontology_path,ontology_path + "/imports"])
		ontology = get_ontology("OntoRXN.owl").load(only_local=True)
		self.Ontology = ontology
		self.process_onto()
		# Also get the corresponding world
		self.MainWorld = default_world.as_rdflib_graph()
		return None

	def load_KG(self,KG_filename):
		''' Function to load a OntoRXN-based knowledge graph from a local file, handling imports and
		the corresponding RDFLib-compatible world.
		Input:
		- KG_filename. String, name of the file to be read.'''
		onto_path.append("")
		# Instantiate a new world
		onto_world = World()
		ontology = onto_world.get_ontology(KG_filename).load(only_local=True)
		self.Ontology = ontology
		self.MainWorld = onto_world.as_rdflib_graph()
		self.process_onto()
		return None


	def construct_query_applier(self,query_list):
		'''For a given ontology, get the corresponding RDFLib world and apply a
		sequence of SPARQL CONSTRUCT queries, passed as a list.
		Input:
		- query_list. List of strings containing valid SPARQL queries'''
		inference_seq = [self.MainWorld.query(qx) for qx in query_list]
		with self.Ontology:
			[self.MainWorld.add(fact) for inference in inference_seq for fact in inference]
		return None

	def nx_graph_generator(self):
		'''Convenience function to wrap the conversion of a RDFLib world graph to a NetworkX
		DiGraph'''
		self.nxGraph = rdflib_to_networkx_digraph(self.MainWorld)
		return None
	
	def node_type_filter(self,blacklist):
		'''Filters the self.nxGraph graph generated from the RDFLib world to exclude nodes
		whose type property corresponds to the types defined in a list.
		Input:
		- blacklist. List of strings, with the names of the types to be removed from the graph.'''
		if (not blacklist):
			return None
		identity_edges = [ed for ed in self.nxGraph.edges(data=True) if ed[2]["name"] == "type"]
		nodes_out = []
		print("Before type filtering, %d nodes" % len(self.nxGraph.nodes))
		# 1st node in the edge is the type/class, 2nd is the entry we are working with :
		for entry in blacklist:
			removed_nodes = [ed[0] for ed in identity_edges if entry in ed[1]]
			nodes_out += removed_nodes
			print("Deleting %d nodes by type (%s)" % (len(removed_nodes),entry))
		self.nxGraph.remove_nodes_from(nodes_out)
		return None

	def node_string_filter(self,blacklist):
		'''Filters the self.nxGraph graph generated from the RDFLib world to exclude nodes
		containing the strings defined in a list.
		Input:
		- blacklist. List of strings, with the strings marking nodes to be removed from the graph.'''

		if (not blacklist):
			return None
		# Remove all nodes whose name (or a part of it) is blacklisted
		working_node_list = self.nxGraph.nodes(data=True)
		print("Before string filtering, %d nodes" % len(working_node_list))
		nodes_out = []
		for entry in blacklist:
			# Check node ID and its "name" attribute. Keeping two lists: nodes to keep and nodes to remove
			kept_nodes = [nd for nd in working_node_list if (entry not in nd[0]) and (entry not in nd[1]["name"])]
			removed_nodes = [nd[0] for nd in working_node_list if (entry in nd[0]) or (entry in nd[1]["name"])]
			nodes_out += removed_nodes
			print("Deleting %d nodes by string (%s)" % (len(removed_nodes),entry))
			working_node_list = kept_nodes
		print("After string filtering, %d nodes" % len(working_node_list))
		self.nxGraph.remove_nodes_from(nodes_out)
		return None

	def set_node_attr_custom(self,node,prop_name,prop_value):
		'''Convenience function to concatenate string node attributes for the graph in
		nxGraph if a given property is already defined, or directly add them otherwise.
		- node. Node from a NetworkX.Graph to be modified.
		- prop_name. String, name of the target property.
		- prop_value. String, new value for the target property.'''
		existing_prop = self.nxGraph.nodes[node].get(prop_name)
		if (existing_prop):
			setting_prop = existing_prop + "\n" + prop_value
		else:
			setting_prop = prop_value
		nx.set_node_attributes(self.nxGraph,{node:{prop_name:setting_prop}})
		return None
	
	def collapse_literals(self):
		'''Check nodes in self.nxGraph that are Literals (corresponding to data properties), set them as
		attributes of their parent node, under the dataprop property, and remove them from the graph.'''
		print("Originally %d nodes" % len(self.nxGraph.nodes))
		nodes_to_remove = []
		for ed in self.nxGraph.edges(data=True):
			nd1,nd2 = ed[0:2]
			if (type(nd2) == rdflib.term.Literal):
				nodes_to_remove.append(nd2)
				literal_string = ed[2]["name"] + ":" + str(nd2.value)
				self.set_node_attr_custom(nd1,"dataprop",literal_string)
			elif (type(nd1) == rdflib.term.Literal):
				nodes_to_remove.append(nd1)
				literal_string = ed[2]["name"] + ":" + str(nd1.value)
				self.set_node_attr_custom(nd2,"dataprop",literal_string)
				
		nodes_to_remove = list(set(nodes_to_remove))
		print("%d literal nodes to be removed" % len(nodes_to_remove))
		self.nxGraph.remove_nodes_from(nodes_to_remove)
		return None
	
	def nx_graph_processor(self,blacklist_info={},collapse_literal_flag=True):
		'''Process the automatically generated NetworkX graph to simplify manipulation, checking basic
		rdflib types (URIRefs, BNodes and Literals).
		typeIds: 1 to general URIRefs, 2, 3, 4 and 5 go for the individuals in each of the OntoRXN main
		classes, 6 to the classes themselves and 7 and 8 correspond to BNodes and Literals.
		Input:
		- blacklist_info. Dictionary mapping filter type keys (type and/or string) to lists of filtering
		strings, to use self.node_type_filter or self.node_string_filter.
		- collapse_literal_flag. Boolean, if True, transform all nodes corresponding to Literal values to
		attributes on their parents via self.collapse_literals()
		'''
		rdflib_types = [rdflib.term.URIRef,rdflib.term.BNode,rdflib.term.Literal]

		# Node processing: text, typeId and name for each possible node type
		for ii,nd in enumerate(self.nxGraph.nodes(data=True)):
			nd[1]["ndx"] = ii
			nd[1]["typeId"] = "0"
			current_type = type(nd[0])
			if (current_type == rdflib.term.URIRef):
				nd[1]["text"] = str(nd[0])
				nd[1]["typeId"] = "1"
				nd[1]["name"] = re.sub("^.*#","",str(nd[0]))

				uri = nd[0]
				target = self.Ontology.search(iri=uri)
				try:
					target_type = target[0].is_a[0]
					matching_type_ndx = self.MainClassList.index(target_type)
					nd[1]["typeId"] = str(matching_type_ndx + 2)
				except:
					pass
				
			elif (current_type == rdflib.term.BNode):
				nd[1]["text"] = str(nd[0])
				nd[1]["typeId"] = "7"
				nd[1]["name"] = "BNode_" + str(nd[0])
			elif (current_type == rdflib.term.Literal):
				nd[1]["text"] = nd[0].value
				nd[1]["typeId"] = "8"
				nd[1]["name"] = "Literal_N" + str(ii)

		# Edge processing
		for ii,ed in enumerate(self.nxGraph.edges(data=True)):
			ed[2]["ndx"] = ii
			# access the triples attribute to get the predicate
			predicate = ed[2]["triples"][0][1]
			try:
				ed[2]["text"] = predicate.value
			except:
				ed[2]["text"] = str(predicate)
			ed[2]["name"] = re.sub("^.*#","",ed[2]["text"])
			ed[2]["name_summ"] = ed[2]["name"].replace(" ","_")

		# Mappings
		node_mapping = {nd[1]["ndx"]:nd for nd in self.nxGraph.nodes(data=True)}
		edge_mapping = {ed[2]["ndx"]:ed for ed in self.nxGraph.edges(data=True)}
		self.nxGraph.graph["node_mapping"] = node_mapping
		self.nxGraph.graph["edge_mapping"] = edge_mapping
		
		# Define a default state for the graph with the main class nodes, for further representation
		default_state = [rdflib.term.URIRef(cls.iri) for cls in self.MainClassList]

		for cls_iri in default_state:
			print(cls_iri,self.nxGraph.nodes[cls_iri])
			self.nxGraph.nodes[cls_iri]["typeId"] = "6"
		self.nxGraph.graph["default_state"] = default_state

		# Collapsing literals
		self.collapse_literals()
		
		# Filtering
		if (blacklist_info):
			self.node_type_filter(blacklist_info.get("type"))
			self.node_string_filter(blacklist_info.get("string"))

		# Locate the most connected nodes via node degree and save in a list
		degree_info = list(self.nxGraph.degree(list(self.nxGraph.nodes())))
		degree_info.sort(key=itemgetter(1),reverse=True)
		self.nxGraph.graph["top_nodes"] = degree_info

		return None
	
	def nx_graph_layout(self,layout_function=nx.spring_layout,passed_positions=[]):
		'''Assign a layout to the nx.Graph in the self.nxGraph attribute'''
		if (not passed_positions):
			print("Finding positions for graph with %d nodes" % (len(self.nxGraph.nodes)))
			posx = layout_function(self.nxGraph)
		else:
			posx = passed_positions
		self.nxGraph.graph["or_positions"] = posx
		return None

	def nx_graph_wrapper(self,blacklist_info,layout_function=None,passed_positions=[]):
		'''Wrapper function to generate a NetworkX graph from the RDFLib graph, processed
		and including layout'''
		self.nx_graph_generator()
		self.nx_graph_processor(blacklist_info)
		self.nx_graph_layout(layout_function,passed_positions)
		return None

def read_property_dict(mapping_file="resources/parsing_rules.dat"):
	'''Generates a dictionary mapping property names in the ontology to tuples with the
	corresponding CML field, the type of the data (Float, String or Vector) and the field for units.
	Input:
	- mapping_file. String, name of a comma-separated file with the corresponding relationships between
	ontology properties and CML fields, as:
	ONTOLOGY_PROPERTY,CML_FIELD_NAME,DATA_TYPE,CML_UNIT_FIELD
	Types can be String, Float or Vector.
	String does not require CML_UNIT_FIELD
	If adding new fields, both CML_FIELD_NAME and CML_UNIT_FIELD must be generated by the corresponding
	XSLT stylesheet.
	Output:
	- property_map_dict. Dictionary mapping property names in the ontology to the tuples specifying
	the CML field, the data type and the unit field
	'''
	base_dir = os.path.dirname(__file__)
	with open(base_dir + "/" + mapping_file,"r") as fmap:
		parse_info = [entry.strip().split(",") for entry in fmap.readlines()]
	property_map_dict = {entry[0]:(entry[1],entry[2],entry[3]) for entry in parse_info}
	return property_map_dict

def atom_instantiator(onto_manager,geometry_block):
	'''Instantiate a gc.Atom object in a given ontology namespace for a XYZ-like cartesian coordinate
	specification
	Input:
	- onto_manager. OntoRXNWrapper object with an OntoRXN instance loaded.
	- geometry_block. String, containing the Cartesian coordinates of a given molecular entity
	Output:
	- mol. gc.Molecule object'''
	gc_space = onto_manager.Namespace["gc"]
	mol = gc_space.Molecule(namespace=onto_manager.Ontology)
	for line in geometry_block.split("\n"):
		at,x,y,z = line.split()
		xyz = [x,y,z]
		atom = gc_space.Atom(symbol=[at],namespace=onto_manager.Ontology)
		vals = [gc_space.FloatValue(hasValue=ii+" a.u.",namespace=onto_manager.Ontology) for ii in xyz]
		atom.hasAtomCoordinateX.append(vals[0])
		atom.hasAtomCoordinateY.append(vals[1])
		atom.hasAtomCoordinateZ.append(vals[2])
		mol.hasAtom.append(atom)
	return mol

def onto_attribute_setter(onto_source,onto_target,property_name):
	'''Access an ontology property and link to the corresponding fetched information,
	managing both functional and non-functional properties, either using setattr directly (functional)
	or mutating the retrieved list (non-functional).
	Input:
	- onto_source. Element in the working ontology to be assigned a new attribute (subject).
	- onto_target. Ontology-based element containing new information which is being matched to the
	source element (object).
	- property_name. Name of the property used to link subject and object (predicate).
	Output:
	- None, modifies the ontology in-place.
	'''
	onto_attr = getattr(onto_source,property_name)
	if (isinstance(onto_attr,list)):
		onto_attr.append(onto_target)
	else:
		setattr(onto_source,property_name,onto_target)
	return None

def set_cml_field(calc_onto,cml_dict,property_name,field_info,namespace,track_units):
	'''Sets a property in the CompCalculation instance if the corresponding CML field
	exists in the dictionary.
	Input:
	- calc_onto. CompCalculation instance in the ontology.
	- cml_dict. Dictionary resulting from XSLT-based parsing of a CML file, via
	py_iochem.CMLtoPy.xslt_parsing()
	- property_name. String, name of the property in the ontology.
	- field_info. Tuple containing strings for field name, field type and unit field name for a given property.
	- namespace. Dict with namespace info taken from OntoRXNWrapper.Namespace
	- track_units. Dict mapping string unit names with pre-defined gc.Value instances for them
	Output:
	- None, modifies calc_onto in-place'''
	# Prepare the gc namespace in here to define FloatValue and VectorValue fields
	gc = namespace["gc"]
	ontology = namespace["onto"]
	value_type_dict = {"Float":gc.FloatValue,"Vector":gc.VectorValue}

	# Access the ontology property and return None if undefined
	try:
		onto_attr = getattr(calc_onto,property_name)
	except:
		# Property undefined in the ontology: cannot assign anything
		print("%s undefined in the ontology" % property_name)
		return None
	
	# Field processing: define the required instances
	field_name,field_type,field_unit = field_info
	field_value = cml_dict.get(field_name)

	if (field_type == "Float" and field_value):
		field_value = float(field_value)

	# Check units that are directly specified on the parsing rules, as r"UnitName" (r and double quotes)
	raw_unit = bool(re.search("r\".*\"",field_unit))
	if (raw_unit):
		unit_value = field_unit[1:].strip("\"")
	else:
		unit_value = cml_dict.get(field_unit)
		
	if (unit_value and unit_value not in track_units.keys()):
		print("ADDING",unit_value)
		unit = gc.Value(name=unit_value,namespace=ontology)
		print(unit)
		track_units[unit_value] = unit
		
	if (not field_value):
		return None
	
	if (field_type == "String"):
		onto_obj = field_value
		onto_attribute_setter(calc_onto,onto_obj,property_name)

	elif (field_type == "Integer"):
		onto_obj = int(field_value)
		onto_attribute_setter(calc_onto,onto_obj,property_name)
		
	elif (field_type == "Float" or field_type == "Vector"):
		target_obj = value_type_dict[field_type](namespace=ontology,hasValue=field_value,
												 hasUnit=track_units[unit_value])
		result_obj = gc["CalculationResult"](namespace=ontology)
		onto_attribute_setter(result_obj,target_obj,property_name)
		onto_attribute_setter(calc_onto,result_obj,"hasResult")
	else:
		return None

	return None

# Go through calculations and instantiate CompCalculation & ChemSpecies entities
def calc_instantiation(onto_manager,calcinfo,report_id):
	'''Generate all CompCalculation and ChemSpecies individuals required for a Reaction Energy Profile report.
	Information is fetched from the CML files named according to every calcId in the profile.
	ChemSpecies are generated by the unique names of these calculations.
	Input:
	- onto_manager. OntoRXNWrapper object with an OntoRXN instance loaded.
	- calcinfo. List of dicts containing calculation information as obtained from the JSON dump of ReportHandler.get_report_calcs()
	- namespaces. Dict matching string tags to valid namespaces to be used in the ontology. Must contain "gc" mapping to Gainesville Core.
	- report_id. Integer, ID of the report used in KG generation (to build stage and step IDs)
	Output:
	- track_calcs. Dictionary matching cN indices (based on calcOrder) to the unique identifiers generated for CompCalculation objects in the KG.
	- track_species. Dictionary matching cN indices (based on calcOrder) to the unique identifiers generated for ChemSpecies objects in the KG.
	cN is used for simplicity, but several cN can match to the same name.
	- Input ontology is modified in-situ.
	'''
	# We need the Gainesville Core (gc) and the OntoCompChem (occ) namespaces
	gc = onto_manager.Namespace["gc"]
	occ = onto_manager.Namespace["occ"]
	# Read prop. mapping dict
	property_map_dict = read_property_dict()
	# Dicts and lists for instance tracking
	track_calcs = {}
	track_species = {}
	molecule_names = {}
	track_units = {}
	for calc in calcinfo:
		# Extract properties
		cid = calc["calcId"]
		molname = calc["title"]
		cN = "c%d" % calc["calcOrder"]
		cmlfile = "calc_%d.cml" % cid
		# Entity instantiation
		calcname = "CALC_%d" % cid
		compcalc = onto_manager.Ontology["CompCalculation"](calcname,namespace=onto_manager.Ontology)
		note = "%s;c%d;%d" % (molname,calc["calcOrder"],cid)
		compcalc.hasAnnotation.append(note)
		# Fetch properties from the CML file and add them to the individual: consider only the 2nd item by now (frequency job!)
		cmldump = cml.xslt_parsing(cmlfile)[1]
		# Basic properties, direct assignment
		for k,v in property_map_dict.items():
			set_cml_field(calc_onto=compcalc,cml_dict=cmldump,property_name=k,
						  field_info=v,namespace=onto_manager.Namespace,track_units=track_units)
		# More complex properties: initialization object, molecule...
		mol = atom_instantiator(onto_manager,cmldump["geometry"])
		compcalc.hasMolecule.append(mol)
		init = occ["InitializationModule"]("init_%d" % cid,namespace=onto_manager.Ontology)
		compcalc.hasInitialization = [init]
		basis = gc["BasisSet"]("basis_set_%d" % cid,namespace=onto_manager.Ontology,
							   hasBasisSet=cmldump["basis"])
		level = occ["LevelOfTheory"]("level_of_theory_%d" % cid,namespace=onto_manager.Ontology)
		level.hasLevelOfTheory = [cmldump["method"]]
		init.hasParameter = [basis,level]
		# Save to dictionary for tracking
		track_calcs[cN] = calcname
		# Species: check whether the "name" of the calculation has yet been observed or not
		# If not, new species. Else, two or more calcs are pointing to a single species
		# For the ID, use the reportId & the calcOrder of the FIRST appearance
		if (molname in molecule_names.keys()):
			# Get the FIRST species with this name and fetch the name of the already generated individual
			code = molecule_names[molname][0]
			spcname = track_species[code]
			# And link with the corresponding calculation
			calcname = track_calcs[cN]
			onto_manager.Ontology[spcname].hasCalculation.append(onto_manager.Ontology[calcname])
			onto_manager.Ontology[spcname].hasAnnotation.append(cN)
		else:
			molecule_names[molname] = [cN]
			spcid = "%d-spc-%d" % (report_id,calc["calcOrder"])
			spcname = "SPC_%s" % spcid
			spc = onto_manager.Ontology["ChemSpecies"](spcname,namespace=onto_manager.Ontology,hasCalculation=[compcalc])
			spc.hasAnnotation.append(cN)
		# In any case, match the cN code with the name of the individual
		track_species[cN] = spcname
	return track_calcs,track_species

def stage_generator(onto_manager,stg_id,element,spc_dict=None):
	'''Wrapper for the generation of a single NetworkStage object in a given ontology.
	- onto_manager. OntoRXNWrapper object with an OntoRXN instance loaded.
	- stg_id. String identifier to name the NetworkStage entity.
	- element. Node or edge from a nx.Graph object as generated by read_iochem_graph()
	- spc_dict. Dictionary matching cN codes (based on calcOrder) to the name of their corresponding ChemSpecies individual
	Output:
	- stage. NetworkStage object instantiated in the input ontology
	'''
	stg_name = "STAGE_%s" % stg_id
	stage = onto_manager.Ontology["NetworkStage"](stg_name,namespace=onto_manager.Ontology)
	stage.hasAnnotation.append(element[-1]["name"])
	# Now we need to check the formula to match species
	# Add "+" to beginning and end of string to allow regex matching
	# only keep species preceded by +
	formula = "+" + element[-1]["formula"] + "-"
	matches = re.findall(r"[+](\w+)",formula)
	print(stg_id,"==>",element[:-1],"==>",matches)
	# fetch the calculations: cN to name and name to individual
	if (spc_dict):
		splist = [onto_manager.Ontology[spc_dict[code]] for code in matches]
		stage.hasSpecies = splist
	return stage

def structure_generator(onto_manager,G_list,track_species,report_id):
	'''For a given list of nx.Graph objects generated via read_iochem_graph(), generate the corresponding
	NetworkStage objects for nodes and TSs and amtch them to the existing ChemSpecies. Then, build & link
	ReactionSteps.
	Input:
	- G_list. List of nx.Graph objects as generated by read_iochem_graph()
	- track_species. Dictionary matching cN codes (based on calcOrder) to the name of their corresponding ChemSpecies individual
	- report_id. Integer, ID of the report used in KG generation (to build stage and step IDs)
	Output:
	- track_stages. Dict matching node/edge names to the corresponding stages
	- Input ontology is modified in-place
	'''
	counter = 0
	track_stages = {}
	for ig,G in enumerate(G_list):
		current_series = G.graph["SerieNames"]
		# Iterate along nodes: each one must have an unique stage
		for nd in G.nodes(data=True):
			ndname = nd[1]["name"]
			stgid = "%d-stg-%d" % (report_id,counter)
			counter += 1
			stage = stage_generator(onto_manager,stgid,nd,track_species)
			track_stages[ndname] = stage.get_name()
		
		# Go along edges: TS stages and steps
		for ie,ed in enumerate(G.edges(data=True)):
			# Create the reaction step and assign the nodes
			nodenames = [track_stages[ndname] for ndname in ed[0:2]]
			nodestages = [onto_manager.Ontology[track_stages[ndname]] for ndname in ed[0:2]]
			rxid = "%d-stp-%d" % (report_id,ie)
			rxname = "STEP_%s" % rxid
			rstep = onto_manager.Ontology["ReactionStep"](rxname,namespace=onto_manager.Ontology)
			rstep.hasNode.extend(nodestages)
			# Stage creation when there is a TS
			tsname = ed[2]["name"]
			if ("missing" in tsname or "closing" in tsname):
				# nothing to define the stage: just match the ReactionStep to the nodes
				continue
			# Here, define the stage for the TS and map it to the step
			stgid = "%d-stg-%d" % (report_id,counter)
			counter += 1
			stage = stage_generator(onto_manager,stgid,ed,track_species)
			track_stages[tsname] = stage.get_name()
			rstep.hasTS = stage
		return track_stages

def knowledge_graph_gen(ontology_route,report_id,config_file,graph_file,out_file,
						collapse_graph=False,fetch_files=False,use_reasoner=False):
	'''Wrapper for KG generation based on OntoRXN from an ioChem-BD report.
	Input:
	- ontology_route. String, full path for the current OntoRXN instance.
	- report_id. Integer, ID for the report in ioChem-BD containing the information for the KG.
	- config_file. String, name of the INI-like file containing login data and URLs for the REST API.
	- graph_file. String, name of the DOT file with the ioChem-BD-generated graph.
	- out_file. String, name of the OWL file to be generated.
	- collapse_graph. Boolean, if True contract nodes with the same name when reading the graph.
	- fetch_files. Boolean, if True download the CML files assigned to the report in ioCHem-BD.
	- use_reasoner. Boolean, if True apply the default reasoner in owlready2 to the KG.
	Output:
	- onto_manager. OntoRXNWrapper object with the ontology and additional properties.
	- Generates OWL files for the KG and possibly the KG with inferred facts after reasoning.'''

	### 1. Read the graph (DOT format) and fetch report information (REST API)
	G_list = GraphManager.graph_read_split(graph_file,collapse_nodes=collapse_graph)
	report = ReportHandler(report_id=report_id,config_file=config_file)

	# Fetch all properties in the report and map the corresponding formulas to the list of graphs
	properties,calcs = report.report_dump()
	GraphManager.formula_mapper(G_list,properties)

	# Handle files, with default naming scheme calc_CID.cml
	if (fetch_files):
		report.batch_cml_dump()

	### 2. Ontology management
	# Load our ontology (from local file) and the imports from their default IRI-based names from onto_path
	onto_manager = OntoRXNWrapper()
	onto_manager.load_ontorxn(ontology_route)
	### 3. Generate the KG
	### 3.1 Take calcs and species from the report
	track_calcs,track_species = calc_instantiation(onto_manager,calcs,report_id)
	### 3.2 Generate stages and steps (structure) from the list of graphs
	track_stages = structure_generator(onto_manager,G_list,track_species,report_id)
	### 3.3 Apply SPARQL queries via RDFLib
	onto_manager.construct_query_applier(list(ontorxn_queries.values()))
	onto_manager.Ontology.save(out_file)
	# Optional inference from the default reasoner
	if (use_reasoner):
		with onto_manager.Ontology:
			print("Start reasoner")
			sync_reasoner()
			alt_out_file = out_file.replace(".owl","_inferred.owl")
			onto_manager.Ontology.save(alt_out_file)
	return onto_manager

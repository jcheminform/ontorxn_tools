'''Diego Garay-Ruiz, January 2022
Management of the DOT-formatted graphs generated in ioChem-BD reports'''
import re
import xmltodict
import networkx as nx
from networkx.drawing.nx_pydot import read_dot
from operator import itemgetter
from collections import defaultdict

# Functions for graph processing
def dot_reader(graph_filename):
	'''
	Read a DOT file as a NetworkX.MultiGraph object and parse the comma-separated
	lists of attributes from ioChem into valid Python lists.
	Input:
	- graph_filename. String, name of the DOT file to be read
	Output:
	- Gworking. nx.MultiGraph object with attribute lists for keys.   
	'''
	Gmulti = read_dot(graph_filename)
	series_information = []
	for nd in Gmulti.nodes(data=True):
		# for key and energy, remove leading/trailing quotes and split by comma
		# then remove original entries
		key_list = (nd[1]['key'][1:-1]).split(",")
		nd[1]['key'] = [int(keyval) for keyval in key_list]
		# we only want connectivity and formulas, but we will get the serie names from the tooltip
		tooltip_names = nd[1]["tooltip"][1:-1].strip().split("\\n")
		serie_names = [re.sub(":.*","",tooltip) for tooltip in tooltip_names]
		serie_info = [(key,sname) for key,sname in zip(nd[1]["key"],serie_names)]
		series_information.extend(serie_info)
		del nd[1]['energy']
		del nd[1]['tooltip']
		
	# Processing the series information
	clean_series_info = sorted(list(set(series_information)),key=itemgetter(0))
	series_dict = {key:sname for key,sname in clean_series_info}
	# copy the nodes to a new graph, then add add. info and edges
	Gworking = nx.Graph()
	Gworking.graph["SerieNames"] = series_dict
	Gworking.add_nodes_from(Gmulti.nodes(data=True))
	# we need the keys= argument because we are working with a MultiGraph
	for edge in Gmulti.edges(data=True,keys=True):
		# convert key and energy to valid numbers: key is not in dict, but as multigraph indx
		edge[3]['key'] = int(edge[2][1:-1])
		del edge[3]['energy']
		del edge[3]['labeltooltip']
		# check whether the edge is already there
		edge_known = Gworking.has_edge(edge[0],edge[1])
		if (edge_known == False):
			# direct addition: just transform key to lists
			Gworking.add_edge(edge[0],edge[1])
			attr_dict = edge[3]
			attr_dict['key'] = [attr_dict['key']]
			Gworking.edges[edge[0],edge[1]].update(attr_dict)
		else:
			# if the edge was already present, append key
			ed_dict = Gworking.edges[edge[0],edge[1]]
			ed_dict['key'].append(edge[3]['key'])
	return Gworking

def dot_processor(G_input,used_keys='all'):
	'''
	Transform a parsed MultiGraph from dot_reader() into a valid 
	unique nx.Graph object that can be directly passed to gTOFfee, 
	adding required properties.
	# adaptation workflow
		1. Add "name" to the node properties
		2. Add "formula" to node & edge properties
	Input:
	- G_input. Parsed nx.MultiGraph() from DOT file preprocessing.
	- used_keys. List of integer IDs for the key values to include in the graph. 
	Default is 'all', considering all existing keys
	Output:
	- G_uniq. nx.Graph, filled with all required values.
	'''
	# Some initializations
	closer_list = []

	# Key selection
	if (used_keys == 'all') or (type(used_keys) != list):
		# get the list of all possible key values looping through nodes
		all_key_vals = [item for entry in G_input.nodes(data='key') for item in entry[1]]
		used_keys = list(set(all_key_vals))
	
	# Instantiate a new Graph object
	G_uniq = nx.Graph()
	
	# Process all nodes in the input
	for nd in G_input.nodes(data=True):
		attr_dict = nd[1]
		keys = attr_dict['key']
		G_uniq.add_node(nd[0])
		G_uniq.nodes[nd[0]].update(nd[1])
		# Add name property: these MUST be unique for some functions to work properly
		# to assure, assign 'nameid' as the unique node ID and generate a tag from
		# from label, removing all after newline and the leading quote to allow renaming too
		G_uniq.nodes[nd[0]]['nameid'] = str(nd[0])
		G_uniq.nodes[nd[0]]['name'] = attr_dict['label'].split("\\n")[0][1:]
		G_uniq.nodes[nd[0]]['formula'] = None
		# Prepare calculations
		#
	# Process edges
	for ed in G_input.edges(data=True):
		attr_dict = ed[2]
		keys = attr_dict['key']
		G_uniq.add_edge(ed[0],ed[1])
		# Handle missing and closing edges, which are labeled in the corresponding entry of the MultiGraph
		label_raw = ed[2]['label']
		if ('missing' in label_raw):
			attr_dict["name"] = label_raw[2:-1]
		elif ('Closing' in label_raw):
			attr_dict["name"] = "closing" + str(ed[2]["key"][0])
		else:
			attr_dict["name"] = label_raw.split("\\n")[0][1:]
		# Add properties via .update(), average the energies if repeated
		attr_dict['formula'] = None
		G_uniq.edges[ed[0],ed[1]].update(attr_dict)

	# Select names of current series in the graph
	G_uniq.graph["SerieNames"] = {k:G_input.graph["SerieNames"][k] for k in used_keys}
	return G_uniq

def node_renamer(in_graph):
	'''For every node and edge in the graph, replace the ID by the 'name' field.
	Don't use if names are not valid identifiers (e.g. repeated names).
	Input:
	- in_graph. nx.Graph object to be modified.
	Output:
	- out_graph. nx.Graph object with replaced names.'''
	# Generate a dictionary mapping IDs with nametag
	dict_nodes = {nd[0]:nd[1]['name'] for nd in in_graph.nodes(data=True)}
	out_graph = nx.relabel_nodes(in_graph,mapping=dict_nodes,copy=True)
	
	# check that no information has been lost: if new names are not unique IDs,
	# some nodes may have been overwritten
	Nnodes_in = len(in_graph.nodes)
	Nnodes_out = len(out_graph.nodes)
	valid_id_flag = (Nnodes_in == Nnodes_out)
	if (not valid_id_flag):
		print("The 'name' field did not contain valid, unique identifiers")
		print("Original IDs are kept")
		out_graph = in_graph.copy()
	return out_graph

def node_collapser(in_graph):
	'''For every node and edge in the graph, check the 'name' field, in order to contract
	nodes that share the same name.
	Input:
	- in_graph. nx.Graph object to be modified.
	Output:
	- out_graph. nx.Graph object with contracted nodes'''
	match_dict = defaultdict(list)
	for nd in in_graph.nodes(data=True):
		match_dict[nd[1]["name"]].append(nd[0])

	out_graph = in_graph.copy()
	collapsed_node_dict = {k:v for k,v in match_dict.items() if len(v) > 1}
	for name,nd_ids in collapsed_node_dict.items():
		pairlist = [(nd_ids[0],nd) for nd in nd_ids[1:]]
		for pair in pairlist:
			out_graph = nx.contracted_nodes(out_graph,pair[0],pair[1])
	return out_graph

def read_iochem_graph(graph_filename,used_keys='all',rename_nodes=False):
	'''Wrapper function: read an ioChem-downloaded DOT file to a valid nx.Graph
	object. 
	Input:
	- graph_filename. String, name of the DOT file to be read (downloaded from ioChem-BD).
	- used_keys. List of integers: IDs for the series that should be included in the graph.
	Default value, 'all', automatically fetches all existing keys
	- rename_nodes. Boolean. If True, update node names in nodes and edges by the 'name' property,
	taken from labels.
	- collapse_nodes. Boolean. If True, assume that nodes with the same name are equivalent, and
	set them as a single node.
	Output:
	- G_out. Processed nx.Graph.
	'''
	G_raw = dot_reader(graph_filename)
	G_out = dot_processor(G_raw,used_keys)
	if (rename_nodes):
		G_out = node_renamer(G_out)
	return G_out

def graph_read_split(gfile,rename_nodes=True,collapse_nodes=False):
	'''For a DOT-formatted file from ioChem-BD, check for the presence of unconnected subgraphs,
	and provide a list where each of these entities has been processed to a nx.Graph.
	Input:
	- gfile. String, name of the DOT file to be read, as downloaded from ioChem-BD
	- rename_nodes. Boolean, if True, update node names in nodes and edges by the 'name' property,
	taken from labels
	- collapse_nodes. Boolean. If True, assume that nodes with the same name are equivalent, and
	set them as a single node.
	Output:
	- G_list. List of processed nx.Graph entities for all subgraphs in the input file.
	'''
	# Read the input file, without renaming, and split the resulting graph by connected components
	Gx = read_iochem_graph(gfile,'all')
	G_list_raw = [Gx.subgraph(gs).copy() for gs in nx.connected_components(Gx)]
	# Apply collapsing and renaming over the corresponding subgraphs, if requested
	if (collapse_nodes):
		G_list_raw[:] = [node_collapser(gs) for gs in G_list_raw]
	G_list = [node_renamer(gs) for gs in G_list_raw]
	# Include the corresponding serie names per subgraph
	for Gii in G_list:
		current_keys = [k for nd in Gii.nodes(data="key") for k in nd[1]]
		unique_keys = list(set(current_keys))
		Gii.graph["SerieNames"] = {k:Gx.graph["SerieNames"][k] for k in unique_keys}
	return G_list

def formula_mapper(G_list,property_list):
	'''Helper function to map the formulas defined in the report to the corresponding graph (which does not contain these formulas)
	Input:
	- G_list. List of nx.Graph objects as generated by read_iochem_graph()
	- property_list. List of properties extracted for a report via the JSON dump of ReportHandler.get_report_properties()
	Output:
	- None. Graphs in the list are modified in-place.
	'''
	# Now use report/profile information to build the knowledge graph
	cblock = property_list["configuration"]
	# Transform to an object, access series
	block = xmltodict.parse(cblock)
	series_info = block["configuration"]["parameters"]["series"]["serie"]

	# Go along all existing graphs and match formula information
	for ig,G in enumerate(G_list):
		#And now we can iterate along all defined series
		known_elements = []
		tsdict = {ed[2]:ed[0:2] for ed in G.edges(data="name")}
		for serie in series_info:
			sname = serie['@name']
			elements = serie['step']
			# we want to assign this information to the graph
			for elem in elements:
				name,formula = [elem[key] for key in ["@label","#text"]]
				print(name,formula)
				if (name in known_elements):
					continue
				else:
					known_elements.append(name)
				# Graph update
				if ("TS" in name):
				# fetch the corresponding edge
					edge = tsdict[name]
					G.edges[edge]["formula"] = formula
				else:
					G.nodes[name]["formula"] = formula
	return None

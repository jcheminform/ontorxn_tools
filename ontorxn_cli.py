import argparse
from ontorxn_tools import *

def arg_handling():
	argparser = argparse.ArgumentParser()
	g1 = argparser.add_argument_group("File management")
	g1.add_argument("--ontofile","-o",help="Directory containing the ontology file",type=str,required=True)
	g1.add_argument("--graphfile","-g",help="Route to the graph file (DOT format)",type=str,required=True)
	g1.add_argument("--reportid","-r",help="ID of the report in ioChem-BD",type=int,required=True)
	g1.add_argument("--loginfile","-l",help="Configuration file with login information",type=str,required=True)
	g2 = argparser.add_argument_group("Control options")
	g2.add_argument("--fetchfiles","-f",help="Download CML files associated to the report in ioChem-BD",
					action="store_true")
	g2.add_argument("--collapse","-c",help="Collapse nodes with common names",
					action="store_true")
	g2.add_argument("--reasoner","-rs",help="Run default reasoner on the KG",
					action="store_true")
	try:
		args = argparser.parse_args()
	except:
		print("Some arguments were missing")
		argparser.print_help()
		return None
	return args

def main():
	args = arg_handling()
	print(args)
	if (not args):
		print("Could not generate the knowledge graph")
		return None
	outfile = args.graphfile.replace(".dot",".owl")
	knowledge_graph_gen(ontology_route=args.ontofile,report_id=args.reportid,
						config_file=args.loginfile, graph_file=args.graphfile,
						out_file=outfile,collapse_graph=args.collapse,
						fetch_files=args.fetchfiles,use_reasoner=args.reasoner)

if (__name__ == "__main__"):
	main()

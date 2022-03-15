from setuptools import setup,find_packages
setup(name='ontorxn_tools',
	  version='0.5',
	  author="Diego Garay-Ruiz",
	  author_email="dgaray@iciq.es",
	  description="Generation of knowledge graphs for reaction networks based on the OntoRXN ontology",
	  py_modules=['ontorxn_tools'],
	  install_requires=['networkx','owlready2','rdflib','py_iochem'])

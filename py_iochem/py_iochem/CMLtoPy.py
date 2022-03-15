'''Diego Garay-Ruiz, 2022.
Processing of the CML files generated by ioChem-BD to generate Python dictionaries,
based on XSLT stylesheets.
Default stylesheets for some programs are provided in ../stylesheets, but custom ones
can also be provided.'''

import lxml.etree as ET
import os.path
import importlib.util

def process_xslt_entry(xslt_string,main_separator="#;#"):
	'''Process a single cc:job entry in a CML file, transforming it to a plain text string
	through XSLT and then generates a Python dictionary with all parsed fields, as strings.
	Input:
	- xslt_string. String generated by the XSLT transformation.
	- main_separator. String used in the XSL files to separate different key:value fields. Must match
	the template: provided templates will use the default "#;#" separator
	Output:
	- parsed_dict. Dict containing key:value pairs for all the fields requested by the XSLT,
	with all values being strings.'''
	raw_entries = xslt_string.split(main_separator)
	gen_dict_entries = [entry.split(":") for entry in raw_entries[:-1]]
	gen_dict_clean = [(item[0].strip(),item[1].strip()) for item in gen_dict_entries if
					  item[1].strip()]
	parsed_dict = dict(gen_dict_clean)
	return parsed_dict

def process_xslt_output(batch_xslt_string,job_separator="FETCH_JOB_END\n"):
	'''Direct processing of the output of the XSLT transformation of a CML document, possibly
	containing several cc:job entries.
	Input:
	- batch_xslt_string. String generated by the XSLT transformation.
	- job_separator. String used in the XSL file to separate the output from different cc:job entries.
	Must match the template: provided templates will use the default "FETCH_JOB_END\n" separator.
	Output:
	- proc_job_entries. List of dicts as generated by process_xslt_entry for each cc:job'''
	job_entries = batch_xslt_string.split(job_separator)[:-1]
	proc_job_entries = [process_xslt_entry(entry) for entry in job_entries]
	return proc_job_entries

def xslt_parsing(cml_file,custom_template=False,xslt_template="stylesheets/CML_Gaussian.xsl"):
	'''Direct parsing of CML files via XSLT stylesheets. By default resorts to the ../stylesheets
	folder containing default templates, but a custom XSL can also be passed.
	Input:
	- cml_file. String, name of the CML file to be parsed.
	- custom_template. Boolean, if True do not check the default directory but the path to the requested file,
	else consider the path parent to the module.
	- xslt_template. String, path to the XSL stylesheet.
	Output:
	- job_cml_fields. List of dicts as generated by process_xslt_entry for each cc:job, containing key:value
	pairs for all the fields requested by the XSLT, with all values being strings.'''
	base_dir = os.path.dirname(__file__)
	if (not custom_template):
		# go one level above with another dirname call
		xslt_path = os.path.dirname(base_dir) + "/" + xslt_template
	else:
		xslt_path = xslt_template
	doc = ET.parse(cml_file)
	transform = ET.XSLT(ET.parse(xslt_path))
	doc_transf = transform(doc)
	string_output = str(doc_transf)
	job_cml_fields = process_xslt_output(string_output)
	return job_cml_fields
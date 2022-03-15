'''Diego Garay-Ruiz, 2022
Python interface to the REST API in ioChem-BD's Create module. The ReportHandler class
allows to fetch information from reports, including the calcIds of the corresponding calculations,
and then fetch the files on these calculations or query them. Moreover, it allows the definition
of new reports.'''
from collections import OrderedDict
import configparser
import re
import json
import requests

class ReportHandler:
	'''Management of ioChem-BD's Create module REST API'''
	def __init__(self,report_id=None,config_file=None,verify=True,**kwargs):
		self.rid = report_id
		self.verify = verify
		# Instantiate empty entities for the dict of properties and the list of calculations
		self.property_dict = {}
		self.calc_list = []
		# Read URL & header information
		if (config_file):
			config = configparser.ConfigParser()
			config.read(config_file)
			# Read from ConfigParser
			self.rurl = config['URL']['URL_REST_REPORT']
			self.calcurl = config['URL']['URL_REST_CALC']
			iochem_passwd = config['ioChem']['my_iochem_passwd']
			self.headers = self.iochem_header_generator(iochem_passwd)
		else:
			# take values from kwargs
			report_url = kwargs["report_url"]
			calc_url = kwargs["calc_url"]
			headers = kwargs["headers"]
			self.arg_reader(report_url=report_url,calc_url=calc_url,headers=headers)

	def arg_reader(self,report_url,calc_url,headers):
		'''Convenience function to pass access arguments from command line'''
		self.rurl = report_url
		self.calcurl = calc_url
		self.headers = headers
		return None

	def iochem_header_generator(self,passwd):
		'''Instantiate the required GET, POST and GETB headers from auth data, and return in a dictionary'''
		headers_get = {'Accept':'application/json','Authorization': 'Basic ' + passwd}
		headers_post = {'Content-Type':'application/json','Accept':'application/json','Authorization':'Basic ' + passwd}
		headers_getb = {'Accept':'application/octet-stream','Authorization':'Basic ' + passwd}
		header_dict = {"GET":headers_get, "POST":headers_post, "GETB":headers_getb}
		return header_dict

	# General functions for requests, only requiring an URL (GET) or an URL and data (POST)
	def get_request(self,url_base,url_addition=""):
		'''Build a GET request for a base URL, optionally adding additional arguments'''
		if (url_base):
			url = url_base + url_addition
			request = requests.get(url,headers=self.headers["GET"],verify=self.verify)
			return request
		else:
			return None

	def post_request(self,url_base,pass_data,url_addition=""):
		'''Build a POST request for a base URL and JSON-organized data to be posted,
		optionally adding additional arguments'''
		if (url_base):
			url = url_base + url_addition
			request = requests.post(url,headers=self.headers["POST"],data=pass_data,verify=self.verify)
			return request
		else:
			return None

	# Report-specific functions, using ReportHandler attributes to simplify the syntax of requests
	def get_report_properties(self):
		'''GET request for the properties associated with a report'''
		url = self.rurl + str(self.rid)
		request = requests.get(url, headers=self.headers["GET"], verify=self.verify)
		return request

	def get_report_calcs(self):
		'''GET request for the list of calculations (including calcIds)'''
		url = self.rurl + str(self.rid) + "/calculation"
		request = requests.get(url, headers=self.headers["GET"], verify=self.verify)
		return request

	def get_calc_files(self, calcId):
		'''GET request to obtain information on all files related to a calculation.
		calcId: integer identifier for a calculation
		'''
		url = self.calcurl + str(calcId) + "/file"
		request = requests.get(url, headers=self.headers["GET"],verify=self.verify)
		return request

	def get_file(self, calcId, fileId):
		'''GET request to fetch a specific file from a calculation.
		calcId: integer identifier for a calculation
		fileId: integer identifier for a specific file, obtained from self.get_calc_files()
		'''
		url = self.calcurl + str(calcId) + "/file/" + str(fileId)
		request = requests.get(url, headers=self.headers["GETB"],verify=self.verify)
		return request

	def create_report(self,auto_rid=True):
		'''POST request to instantiate a new report in ioChem-BD, with automatic assignment of a reportId'''
		url = self.rurl
		print(json.dumps(self.property_dict))
		response = requests.post(url,headers=self.headers["POST"],
								 data=json.dumps(self.property_dict),verify=self.verify)
		if (auto_rid):
			resp_json = response.json()
			print(resp_json)
			self.rid = resp_json["id"]
		return response

	def assign_calc_to_report(self, calcData):
		'''POST request to assign a given calculation to a report in ioChem-BD, with the reportId in the self.rid
		property of the ReportHandler.#!/usr/bin/env python
		calcData: JSON-organized string with dict-type data for a calculation, containing.
		- calcId. Integer identifying the calculation in the database.
		- calcOrder. Integer, order of the calculation in the list of calculations
		- title. String, name of the calculation.
		- reportId. Integer, id of the report to which the calculation is assigned.'''
		url = self.rurl + str(self.rid) + "/calculation"
		response = requests.post(url, headers=self.headers["POST"], verify=self.verify, data=calcData)
		return response

	# Simultaneous request & JSON-dump for report properties and calculation information
	def report_dump(self):
		'''Produces JSON dict-like strings for all the properties and calculations in a report'''
		r1 = self.get_report_properties()
		r2 = self.get_report_calcs()
		return r1.json(),r2.json()
	
	def batch_cml_dump(self):
		'''Fetch the CML files for all the calculations associated with a report,
		returning a list of strings with all filenames
		'''
		properties,calculations = self.report_dump()
		print("Fetching %d files" % len(calculations))
		file_list = []
		for calc in calculations:
			cid = calc["calcId"]
			name = calc["title"]
			calcfiles = self.get_calc_files(cid).json()
			# Fetch the identifier for the CML file in the calculation
			ofile_id = [cfile["id"] for cfile in calcfiles if ".cml" in cfile["name"]][0]
			# Get the contents and write to file
			cml = self.get_file(cid,ofile_id).text
			fn = "calc_%d.cml" % cid
			with open(fn,"w") as fcml:
				fcml.write(cml)
			file_list.append(fn)
		return file_list

	# Basic management of query requests through the REST API
	def query_formatter(self,query_list):
		'''Preparation of direct queries for calculations, generating the JSON dict-like nested structure
		queries: query_list, with each query in the list having an id and a XPath-like query'''
		fmt_query_list = [{"id":ii,"query":query} for ii,query in enumerate(query_list)]
		query_dict = {"queries":fmt_query_list}
		query_json = json.dumps(query_dict)
		self.current_query_dict = query_dict
		self.current_query = query_json
		return query_json

	def single_query_execution(self,target_cid,query_json=None,get_result=True):
		'''Execution of formatted queries for a given calculation (with its calcId given as target_cid).
		- target_cid. Integer, calcId to be queried.
		- query_json. String, JSON dict-like query to be passed. If empty, use the current_query attribute which
		is automatically generated after self.query_formatter.
		- get_results. Boolean, if True fetch the result field in the query only'''
		if (not query_json):
			query_json = self.current_query
		target_url = self.calcurl + str(target_cid) + "/query"
		response = self.post_request(target_url, pass_data=query_json)
		query_data = response.json()
		if (get_result):
			query_data = [entry['result'] for entry in query_data['results']]
		return query_data

	def batch_query_execution(self,query_json,get_result=True):
		'''Apply a query to all calculations in the report
		- query_json. String, JSON dict-like query to be passed. If empty, use the current_query attribute
		- get_results. Boolean, if True fetch the result field in the query only
		'''
		calc_list = self.get_report_calcs().json()
		batch_output = OrderedDict()
		for calc in calc_list:
			print("Processing calc. %d (%s)" % (calc["calcId"],calc["title"]))
			query_data = self.single_query_execution(calc["calcId"],query_json,get_result=get_result)
			batch_output[calc["title"]] = query_data
		return batch_output

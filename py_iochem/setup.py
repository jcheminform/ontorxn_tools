from setuptools import setup

package = 'py_ioChem'
version = '0.2'

setup(name=package,
      version=version,
	  author="Diego Garay-Ruiz",
	  author_email="dgaray@iciq.es",
      description="Python functions to manage ioChem-BD results, including CML file processing, DOT-formatted graph I/O and REST API management",
      py_modules=["py_iochem"],
	  install_requires=['lxml','networkx','requests'],
	  data_files=[('stylesheets','stylesheets/*.xsl')])
 

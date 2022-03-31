<xsl:stylesheet
		  xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0"
			xmlns:cc="http://www.xml-cml.org/dictionary/compchem/"
			xmlns:cml="http://www.xml-cml.org/schema"
			xmlns:cmlx="http://www.xml-cml.org/schema/cmlx"
			xmlns:compchem="http://www.xml-cml.org/dictionary/compchem/"
			xmlns:convention="http://www.xml-cml.org/convention/"
			xmlns:g="http://www.iochem-bd.org/dictionary/gaussian/"
			xmlns:nonsi="http://www.xml-cml.org/unit/nonSi/"
			xmlns:nonsi2="http://www.iochem-bd.org/unit/nonSi2/"
			xmlns:si="http://www.xml-cml.org/unit/si/"
			xmlns:xi="http://www.w3.org/2001/XInclude"
			xmlns:xsd="http://www.w3.org/2001/XMLSchema">
	<xsl:output method="text" omit-xml-declaration="yes" indent="no"/>

	<xsl:template name="getDetails" match="//cml:module[@dictRef='cc:initialization']">
		<xsl:variable name="method" select=".//cml:parameter[@dictRef='cc:method']/cml:scalar"/>
		<xsl:variable name="basisset" select=".//cml:parameter[@dictRef='cc:basis']/cml:scalar"/>
		<xsl:variable name="operation" select=".//cml:parameter[@dictRef='g:operation']/cml:scalar"/>
		<xsl:value-of select="concat('method:',$method,'#;#')"/>
		<xsl:value-of select="concat('basis: ',$basisset,'#;#')"/>
		<xsl:value-of select="concat('op: ',$operation,'#;#')"/>
	</xsl:template>

	<xsl:template name="getProcessDetails" match="//cml:module[@dictRef='cc:calculation']">
		<xsl:variable name="solvent" select="(.//cml:scalar[@dictRef='g:solvent'])[1]"/>
		<xsl:variable name="solvEps" select="(.//cml:scalar[@dictRef='g:eps'])[1]"/>
		<xsl:value-of select="concat('solvent:',$solvent,'#;#','solvEps:',$solvEps,'#;#')"/>
	</xsl:template>
	
	<xsl:template name="getEnergies">
		<xsl:variable name="finalEnergy" select=".//cml:module[@dictRef='cc:finalization']//cml:scalar[@dictRef='cc:hfenergy']"/>
		<xsl:variable name="finalEnergyUnits" select=".//cml:module[@dictRef='cc:finalization']//cml:scalar[@dictRef='cc:hfenergy']/@units"/>
		<xsl:value-of select="concat('energy: ',$finalEnergy,'#;#')"/>
		<xsl:value-of select="concat('energyUnits: ',translate($finalEnergyUnits,':','_'),'#;#')"/>
	</xsl:template>

	<xsl:template name="getThermo" match="//cml:module[@dictRef='cc:finalization']">
		<xsl:variable name="Gibbs" select=".//cml:scalar[@dictRef='cc:zpe.sumelectthermalfe']"/>
		<xsl:variable name="gibbsUnits" select=".//cml:scalar[@dictRef='cc:zpe.sumelectthermalfe']/@units"/>
		<xsl:variable name="temperature" select=".//cml:scalar[@dictRef='cc:temp']"/>
		<xsl:variable name="tempUnits" select=".//cml:scalar[@dictRef='cc:temp']/@units"/>
		<xsl:variable name="pressure" select=".//cml:scalar[@dictRef='cc:press']"/>
		<xsl:variable name="pressUnits" select=".//cml:scalar[@dictRef='cc:press']/@units"/>
		<xsl:variable name="symmnumb" select=".//cml:scalar[@dictRef='cc:symmnumber']"/>
		<xsl:variable name="rottemp" select=".//cml:array[@dictRef='cc:rottemp']"/>
		<xsl:variable name="mominertia" select=".//cml:array[@dictRef='cc:moi.eigenvalues']"/>
		<xsl:variable name="molmass" select=".//cml:scalar[@dictRef='cc:molmass']"/>
		<xsl:value-of select="concat('G: ',$Gibbs,'#;#')"/>
		<xsl:value-of select="concat('gibbsUnits: ',translate($gibbsUnits,':','_'),'#;#')"/>
		<xsl:value-of select="concat('temp: ',$temperature,'#;#','tempUnits: ',
							  translate($tempUnits,':','_'),'#;#')"/>
		<xsl:value-of select="concat('pressure: ',$pressure,'#;#',
							  'pressUnits: ', translate($pressUnits,':','_'), '#;#')"/>
		<xsl:value-of select="concat('symmnumb: ',$symmnumb,'#;#',
							  'rottemp: ',$rottemp,'#;#',
							  'mominertia: ',$mominertia,'#;#',
							  'molmass: ',$molmass,'#;#')"/>
	</xsl:template>
	
	<xsl:template name="getMolecule">
		<xsl-text> geometry: </xsl-text>
		<xsl:for-each select=".//cml:module[@dictRef='cc:finalization']/cml:molecule/cml:atomArray/cml:atom">
			<xsl:variable name="xyzAtom" select="concat(@elementType,' ',@x3,' ',@y3,' ',@z3,'&#xa;')"/>
			<xsl:value-of select="$xyzAtom"/>
		</xsl:for-each>
		<xsl:text> #;# </xsl:text>
		<xsl:variable name="inchi" select=".//cml:module[@dictRef='cc:finalization']/cml:molecule/cml:formula[@convention='iupac:inchi']/@inline"/>
		<xsl:variable name="molmass" select=".//cml:property[@dictRef='cml:molmass']/cml:scalar"/>
		<xsl:variable name="molmassUnits" select=".//cml:property[@dictRef='cml:molmass']/cml:scalar/@units"/>
		<xsl:value-of select="concat('inchi:',$inchi,'#;#')"/>
					  
	</xsl:template>

	<xsl:template name="getFrequencies" match="//cml:module[@dictRef='cc:finalization']">
		<xsl:variable name="freqArr" select=".//cml:array[@dictRef='cc:frequency']"/>
		<xsl:value-of select="concat('frequencies: ',$freqArr,'#;#')"/>
		<xsl:text> freqUnits: cm-1 #;# </xsl:text>
	</xsl:template>
	
	<xsl:template match="/">
		<xsl:for-each select=".//cml:module[@dictRef='cc:jobList']/cml:module[@dictRef='cc:job']">
			<xsl:call-template name="getDetails"/>
			<xsl:call-template name="getProcessDetails"/>
			<xsl:call-template name="getEnergies"/>
			<xsl:call-template name="getThermo"/>
			<xsl:call-template name="getMolecule"/>
			<xsl:call-template name="getFrequencies"/>
			<xsl:text> FETCH_JOB_END&#xa;</xsl:text>
		</xsl:for-each>
	</xsl:template>
</xsl:stylesheet>

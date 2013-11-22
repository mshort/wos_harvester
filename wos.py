from suds.client import Client
import sys, urllib
#import base64
#import logging

try:
  from lxml import etree
  print("running with lxml.etree")
except ImportError:
  try:
    # Python 2.5
    import xml.etree.cElementTree as etree
    print("running with cElementTree on Python 2.5+")
  except ImportError:
    try:
      # Python 2.5
      import xml.etree.ElementTree as etree
      print("running with ElementTree on Python 2.5+")
    except ImportError:
      try:
        # normal cElementTree install
        import cElementTree as etree
        print("running with cElementTree")
      except ImportError:
        try:
          # normal ElementTree install
          import elementtree.ElementTree as etree
          print("running with ElementTree")
        except ImportError:
          print("Failed to import ElementTree from any known place")

#logging.basicConfig(level=logging.INFO)
#logging.getLogger('suds.client').setLevel(logging.DEBUG)

def wos_client():

    url_auth = 'http://search.webofknowledge.com/esti/wokmws/ws/WOKMWSAuthenticate?wsdl'

   # username = 'xxxx'
   # password = 'xxxx'

   # base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n','')
   # authenticationHeader = {
   #     'Authorization' : 'Basic %s' % base64string
   # }

    client_auth=Client(url_auth, username='xxxx', password='xxxx')
   # client_auth = Client(url_auth, headers=authenticationHeader)
    cookie = client_auth.service.authenticate()

    url_query='http://search.webofknowledge.com/esti/wokmws/ws/WokSearchLite?wsdl'
    return Client(url_query, headers= { 'Cookie': 'SID=%s' % (cookie)}, retxml=True)

def wos_query(query, record_num):

    global client
    client = wos_client()
    
    queryParameter = client.factory.create('queryParameters')
    queryParameter.databaseId='WOS'
    queryParameter.userQuery= query
    queryParameter.queryLanguage='en'

    retrieveParameter = client.factory.create('retrieveParameters')
    retrieveParameter.firstRecord=1
    retrieveParameter.count= record_num

    return client.service.search(queryParameter, retrieveParameter)

def wos_retrieve(first, record_num):
    
    retrieveParameters = client.factory.create('retrieveParameters')
    retrieveParameters.firstRecord=first
    retrieveParameters.count=record_num

    return client.service.retrieve('1', retrieveParameters)


def wos_transform(results, keep_path, discard_path):
    
    xml = etree.XML(results)
    records = xml.findall('*//records')

    xslt = etree.XML('''\
    <xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
        <xsl:output method="xml" indent="yes" encoding="UTF-8"/>
        <xsl:template match="text()"/>
        <xsl:template match="/">
            <dublin_core schema="dc">
                <xsl:apply-templates/>
            </dublin_core>
        </xsl:template>

        <xsl:template match="uid">
            <dcvalue element='identifier' qualifier='uid'>
                <xsl:value-of select="."/>
            </dcvalue>
        </xsl:template>

        <xsl:template match="/records/title">
            <dcvalue element="title" qualifier="none" language="en_US">
                <xsl:value-of select="./value"/>
            </dcvalue>
        </xsl:template>

        <xsl:template match="/records/authors">
            <xsl:for-each select="./value">
                <dcvalue element="contributor" qualifier="author">
                    <xsl:value-of select="."/>
                </dcvalue>
            </xsl:for-each>
        </xsl:template>

        <xsl:template match="/records/keywords">
            <xsl:for-each select="./value">
                <dcvalue element="subject" qualifier="none" language="en_US">
                    <xsl:value-of select="."/>
                </dcvalue>
            </xsl:for-each>
        </xsl:template>

        <xsl:template match="/records/source">
            <xsl:if test="./label='Published.BiblioYear'">
                <dcvalue element="date" qualifier="issued">
                    <xsl:value-of select="./value"/>
                </dcvalue>
            </xsl:if>
        </xsl:template>

        <xsl:template match="/records/other">
            <xsl:if test="./label='Identifier.Xref_Doi'">
                <dcvalue element="identifier" qualifier="doi">
                    <xsl:value-of select="./value"/>
                </dcvalue>
            </xsl:if>
            <xsl:if test="./label='Identifier.Issn'">
                <dcvalue element="identifier" qualifier="issn">
                    <xsl:value-of select="./value"/>
                </dcvalue>
            </xsl:if>
        </xsl:template>

    </xsl:stylesheet>''')

    transform = etree.XSLT(xslt)

    romeo_dict = {}
    
    for record in records:
           
        dc = transform(record)


        issn_list = dc.xpath('/dublin_core/dcvalue[@element="identifier"][@qualifier="issn"]/text()')

        if issn_list:
            
            issn = issn_list[0]
            romeo_query = urllib.urlopen('http://www.sherpa.ac.uk/romeo/api29.php?issn=%s' % issn)
            romeo_string = romeo_query.read()
            romeo_tree = etree.fromstring(romeo_string)
            romeo = romeo_tree.xpath('/romeoapi/publishers/publisher/romeocolour/text()="green"')
            romeo_result = romeo_tree.xpath('/romeoapi/publishers/publisher/romeocolour/text()')

        else:
            continue

        uid_list = dc.xpath('/dublin_core/dcvalue[@element="identifier"][@qualifier="uid"]/text()')
        uid = uid_list[0]

        romeo_dict[uid]=romeo_result

        if romeo is True:
            
            tmp = file('%s/%s.xml' % (keep_path, uid), 'w')
            string = etree.tostring(dc)
            tmp.write(string)
            tmp.close()
            
        elif romeo is False or not issn_list:
            
            tmp = file('%s/%s.xml' % (discard_path, uid), 'w')
            string = etree.tostring(dc)
            tmp.write(string)
            tmp.close()

    print romeo_dict
            
    #for x, y in romeo_dict.iteritems():
 #       with open ('%s/romeo.txt' % keep_path, 'a') as f:
 #           f.write(x)
 #           f.write(y)

def main(argv):
            
    query = input('Enter your query: ')
    record_num = input('How many records do you want to retrieve? ')
    keep_path = input ('Where do you want to save your green records? ')
    discard_path = input ('Where do you want to save your not-green records? ')

    results = wos_query(query, record_num)

    if not results:
        print("Failed to retrieve records from Web of Science")
        return 1

    try:
        wos_transform(results, keep_path, discard_path)
        print("First pass complete.")
    except:
        print("Transform failed on first pass.")

    xml = etree.XML(results)
    response = xml.findall('*//return')
    r = etree.tostring(response[0])
    r_xml = etree.XML(r)
    records_list = r_xml.xpath('/return/recordsFound/text()')
    records_string = records_list[0]
    records_found = int(records_string)

    print ("%s records will be retrieved." % records_found)

    first = record_num + 1
    counter = record_num
    pass_num = 2
    
    while counter < records_found:

        results = wos_retrieve(first, record_num)

        wos_transform(results, keep_path, discard_path)
        print("Pass #%s complete." % pass_num)

        first += record_num
        counter += record_num
        pass_num += 1

    else:
        print("Done.")

    
if __name__ == '__main__':
    sys.exit(main(sys.argv))

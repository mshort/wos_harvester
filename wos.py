from suds.client import Client
import sys, urllib, json, csv

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


def wos_client():

    url_auth = 'http://search.webofknowledge.com/esti/wokmws/ws/WOKMWSAuthenticate?wsdl'
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


def wos_transform(results):
    
    xml = etree.XML(results)
    records = xml.findall('*//records')
    
    p = []
    t = []
    
    for record in records:
        
        if record.xpath('title/value/text()'):
            title = record.xpath('title/value/text()')[0]
        else:
            title = ''
        if record.xpath('doctype/value/text()'):
            docType = record.xpath('doctype/value/text()')[0]
        else:
            docType = ''
        if record.xpath('source[label="SourceTitle"]/value/text()'):
            journal = record.xpath('source[label="SourceTitle"]/value/text()')[0]
        else:
            journal = ''
        if record.xpath('source[label="Volume"]/value/text()'):
            volume = record.xpath('source[label="Volume"]/value/text()')[0]
        else:
            volume = ''
        if record.xpath('source[label="Issue"]/value/text()'):
            issue = record.xpath('source[label="Issue"]/value/text()')[0]
        else:
            issue = ''
        if record.xpath('source[label="Pages"]/value/text()'):
            pages = record.xpath('source[label="Pages"]/value/text()')[0]
        else:
            pages = ''
        if record.xpath('source[label="Published.BiblioYear"]/value/text()'):
            year = record.xpath('source[label="Published.BiblioYear"]/value/text()')[0]
        else:
            year = ''
        if record.xpath('source[label="Published.BiblioDate"]/value/text()'):
            date = record.xpath('source[label="Published.BiblioDate"]/value/text()')[0]
        else:
            date = ''
            
        author = ''
        if record.xpath('authors/value/text()'):
            authors = record.xpath('authors/value/text()')
            if len(authors) > 1:
                if len(authors) < 5:
                    for au in authors[:-1]:
                        author+= au + "||"
                    author+=authors[-1]
                else:
                    for au in authors[:4]:
                        author+= au + "||"
                    author+=authors[-1] + " + %s others" % len(authors)
                    
            else:
                author+=record.xpath('authors/value/text()')[0]
                
        keyword = ''
        if record.xpath('keywords/value/text()'):
            keywords = record.xpath('keywords/value/text()')
            if len(keywords) > 1:
                for key in keywords[:-1]:
                    keyword+= key + "||"
                keyword+=keywords[-1]
            else:
                keyword+=record.xpath('keywords/value/text()')[0]

        if record.xpath('other[label="Identifier.Issn"]/value/text()'):
            issn = record.xpath('other[label="Identifier.Issn"]/value/text()')[0]
        else:
            issn = ''
        if record.xpath('other[label="Identifier.Eissn"]/value/text()'):
            eissn = record.xpath('other[label="Identifier.Eissn"]/value/text()')[0]
        else:
            eissn = ''
        if record.xpath('other[label="Identifier.Ids"]/value/text()'):
            ids = record.xpath('other[label="Identifier.Ids"]/value/text()')[0]
        else:
            ids = ''
        if record.xpath('other[label="Identifier.Doi"]/value/text()'):
            doi = record.xpath('other[label="Identifier.Doi"]/value/text()')[0]
        else:
            doi = ''
        if record.xpath('uid/text()'):
            uid = record.xpath('uid/text()')[0]
        else:
            uid = ''
        if record.xpath('other[label="Identifier.Xref_Doi"]/value/text()'):
            xref_doi = record.xpath('other[label="Identifier.Xref_Doi"]/value/text()')[0]
        else:
            xref_doi = ''
        
        t.append([title, docType, journal, volume, issue, pages, year, date, author, keyword, issn, eissn, ids, doi, uid, xref_doi])
        
        print issn
        
        if issn:
            
            key='xxx'
    
            romeo = json.load(urllib.urlopen('https://v2.sherpa.ac.uk/cgi/retrieve/cgi/retrieve?item-type=publication&api-key=%s&format=Json&filter=[["issn","equals","%s"]]' % (key, issn)))
            
            if romeo['items']:
                if 'permitted_oa' in romeo['items'][0]['publisher_policy'][0]:
                    
                    version = []
                    
                    for i in romeo['items'][0]['publisher_policy'][0]['permitted_oa']:
                        if ('institutional_repository' or 'non_commercial_institutional_repository' in i['location']['location']):
                            version.append("%s|%s" % (i['article_version'], i['additional_oa_fee']))
                    
                    if 'published|no' in version:
                        for i in romeo['items'][0]['publisher_policy'][0]['permitted_oa']:                           
                            if ('institutional_repository' or 'non_commercial_institutional_repository' in i['location']['location']) and ('published' in i['article_version']):
                                version = 'published'
                                if 'no' in i['additional_oa_fee']:
                                    fee = 'no'
                                else:
                                    fee = 'yes'
                                embargo = ''
                                if 'embargo' in i:
                                    embargo = "%s %s" % (i['embargo']['amount'], i['embargo']['units'])
                                condition = ''
                                if 'conditions' in i:
                                    conditions = i['conditions']
                                    if len(conditions) > 1:
                                        for c in conditions[:-1]:
                                            condition+= c + "||"
                                        condition+=conditions[-1]
                                    else:
                                        condition+=conditions[0]
                                licenseCode = ''
                                if 'license' in i:
                                    licenseCode = i['license'][0]['license']
                                p.append([title, docType, journal, volume, issue, pages, year, date, author, keyword, issn, eissn, ids, doi, uid, xref_doi, condition, embargo, fee, licenseCode, version])
                    else:
                        for i in romeo['items'][0]['publisher_policy'][0]['permitted_oa']:
                            if ('institutional_repository' or 'non_commercial_institutional_repository' in i['location']['location']):
                                if 'published' in i['article_version']:
                                    version = 'published'
                                if 'accepted' in i['article_version']:
                                    version = 'accepted'
                                if 'submitted' in i['article_version']:
                                    version = 'submitted'
                                if 'no' in i['additional_oa_fee']:
                                    fee = 'no'
                                else:
                                    fee = 'yes'
                                embargo = ''
                                if 'embargo' in i:
                                    embargo = "%s %s" % (i['embargo']['amount'], i['embargo']['units'])
                                condition = ''
                                if 'conditions' in i:
                                    conditions = i['conditions']
                                    if len(conditions) > 1:
                                        for c in conditions[:-1]:
                                            condition+= c + "||"
                                        condition+=conditions[-1]
                                    else:
                                        condition+=conditions[0]
                                licenseCode = ''
                                if 'license' in i:
                                    licenseCode = i['license'][0]['license']
                                p.append([title, docType, journal, volume, issue, pages, year, date, author, keyword, issn, eissn, ids, doi, uid, xref_doi, condition, embargo, fee, licenseCode, version])
                    
                else:
                    print "No policy!!"
                    condition = ''
                    embargo = ''
                    fee = ''
                    version = 'no policy'
                    licenseCode = ''
                    p.append([title, docType, journal, volume, issue, pages, year, date, author, keyword, issn, eissn, ids, doi, uid, xref_doi, condition, embargo, fee, licenseCode, version])
        else:
            print "ISSN not found!!"
            condition = ''
            embargo = ''
            fee = ''
            version = 'no policy'
            licenseCode = ''
            p.append([title, docType, journal, volume, issue, pages, year, date, author, keyword, issn, eissn, ids, doi, uid, xref_doi, condition, embargo, fee, licenseCode, version])
            continue
    return p, t

def main(argv):
            
    query = input('Enter your query: ')
    record_num = input('How many records do you want to retrieve? ')

    results = wos_query(query, record_num)

    if not results:
        print("Failed to retrieve records from Web of Science")
        return 1
    
    published= []
    tracking = []
    
    try:
        p, t = wos_transform(results)
        published.append(p)
        tracking.append(t)
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

        p, t = wos_transform(results)
        published.append(p)
        tracking.append(t)
        print("Pass #%s complete." % pass_num)

        first += record_num
        counter += record_num
        pass_num += 1

    else:
        print("Done.")
        
    published_final = []
    
    for pb in published:
        if pb not in published_final:
            published_final.append(pb)
    print published_final
    
    with open("C:/Users/Matt/Documents/wos_2019.csv", 'wb') as csvfile_published:
        csvwriter_published = csv.writer(csvfile_published, delimiter=',', quotechar='"')
        for r in published_final:
            csvwriter_published.writerows(r)
    
    tracking_final = []
    
    for tr in tracking:
        if tr not in tracking_final:
            tracking_final.append(tr)
    
    with open("C:/Users/Matt/Documents/wos_tracking_2019.csv", 'wb') as csvfile_tracking:
        csvwriter_tracking = csv.writer(csvfile_tracking, delimiter=',', quotechar='"')
        for r in tracking_final:
            csvwriter_tracking.writerows(r)

    
if __name__ == '__main__':
    sys.exit(main(sys.argv))

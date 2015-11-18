''' Retrieve tenders info from the Web and save it in csv files.

Data is downloaded from the following domains:
domains = ['westsussex.bravosolution.co.uk','commercialsolutions.bravosolution.co.uk', \
            'etenderwales.bravosolution.co.uk','nhsbt.bravosolution.co.uk', \
            'bbc.bravosolution.co.uk','chelwest.bravosolution.co.uk', \
            'iewm.bravosolution.co.uk','skillsfundingagency.bravosolution.co.uk']

Features of the script:
* works both on Mac/OS and Windows/Linux by automatically
  adapting the commands for opending tabs in the Selenium Firefox Webdriver
* appends logging information to LOGFILE. The file gets overwritten each time the script is run!
* Unicode support. All data is saved with Unicode utf-8 encoding

'''

# -*- coding: utf-8 -*-
import sys
from selenium import webdriver  
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup, element
import re
import datetime
import time
import csv, codecs, cStringIO
import os
import json


# http://selenium-python.readthedocs.org/en/latest/waits.html
# An implicit wait is to tell WebDriver to poll the DOM
# for a certain amount of time when trying to find an element
# or elements if they are not immediately available.
# The default setting is 0. 
IMPLICIT_WAIT = 10

LOGFILE = "tenders.log"

# from https://docs.python.org/2.7/library/csv.html#csv-examples
class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)




def get_project(driver,detail_link):
    logFile.write("Saving tender details for " + detail_link)
    print "Saving tender details for " + detail_link ###debug
    driver.get(detail_link)
    tender_html = driver.page_source
    tender_soup = BeautifulSoup(tender_html,'html.parser')
    source = tender_soup("div", {"class":re.compile("form_question|form_answer")})
    
    project = {"URL":str(detail_link).replace('\xc2\xa0', ' '), \
               "URL_Retrieval_date":datetime.datetime.now().isoformat(), \
               "PDFs":[]} 
    for s in source:
       if (s[u'class'] == [u'form_question']):
         # use it as key and next sibling is value
         key = s.contents[0]
       elif (s[u'class'] == [u'form_answer'] and key != ''):
         project[key] = ' '.join([str(x.encode('utf-8')) for x in s.contents])
         key = ""
    pdf_files_objs = tender_soup.findAll("a", {"class":"detailLink"})
    pdf_files_urls = [link['href'] for link in pdf_files_objs]
    project["PDFs"] = ['https://'+domain+str(file) for file in pdf_files_urls]
   
    project["details"] = []
    for pdf_url in project["PDFs"]:
        noticeId = re.findall(r"noticeId=\d+",pdf_url)[0].split('=')[1]
        opportunityId = re.findall(r"opportunityId=\d+",pdf_url)[0].split('=')[1]
        details_id = 'tender_details_'+domain.split('.')[0] + '_' + opportunityId + '_' + \
                       noticeId 
        project["details"].append(details_id)
   
    if u'Project Title' in project.keys():
        logFile.write(" ("+project[u'Project Title']+")")
    #print project[u'Project Title']
    return project

        

def get_projects (link,domain):
    driver = webdriver.Firefox()
    driver.implicitly_wait(IMPLICIT_WAIT)

    driver.get(link)
    tender_html = driver.page_source
    tender_soup = BeautifulSoup(tender_html,'html.parser')
    next_page = tender_soup("a", {"title":"Forward"})
    page_nr = 1
    projects = []
    while next_page or page_nr==1:
    #while page_nr==1: ##for debugging
      logFile.write("Page " + str(page_nr))
      tenders = driver.find_elements_by_class_name('detailLink')
      nr_tenders = len(tenders)
      #print "Found " + str(nr_tenders) + " tenders"
      logFile.write("Found " + str(nr_tenders) + " tenders")
      details_tenders = []
      main_window = driver.current_window_handle
      #print "opening new tab ..."
      body = driver.find_element_by_tag_name("body") 
      body.send_keys(kc + 't')
      for tender in tenders:
         id = re.findall(r"\D(\d+)\D", tender.get_attribute('onclick'))[0]
         detail_link = "https://"+domain+"/esop/toolkit/opportunity/opportunityDetail.do?opportunityId=" + id
         logFile.write("Detail link: " + str(detail_link))
         details_tenders.append(detail_link)
      for detail_link in details_tenders:
         projects.append(get_project(driver,detail_link))
      if page_nr==1 and not next_page:
        page_nr +=1
        
      # go back to main window
      driver.find_element_by_tag_name('body').send_keys(kc + 'w')
    
      if next_page:
        page_nr +=1
        found = False
        while not found:
          try:
            driver.find_element_by_xpath("//a[@title='Go to page %d']" % page_nr).click()
            found = True
          except NoSuchElementException:     
            p = driver.find_element_by_xpath("//input[@name='listManager.pagerComponent.page']").get_attribute("value")
            if (p==str(page_nr)):
                found = True
            else:
                try:
                  driver.find_element_by_xpath("//a[@title='Forward']").click()
                except NoSuchElementException:
                  found = True
                  next_page = []
                  pass
                
    driver.quit()     ### to debug do not close browser  
    return projects

def retrieve_to_file (links,filename,filename_details):
    resultFile = open(filename,'wb')  
    fieldnames = [u'Project Code', u'Project Title', u'Estimated Value of Contract',  \
                  'URL', 'URL_Retrieval_date', \
                  u'Work Category', u'Web Link',  u'Contract Start Date', \
                  u'Notes', u'Procurement Route', u'Buyer', u'Buyer Email',   \
                  u'Listing Deadline', u'Organisation', u'Contract Duration', \
                  u'Project Description',u'PDFs','details']
    csvWriter = csv.DictWriter(resultFile, fieldnames,delimiter=',')
    csvWriter.writeheader()
    csvUWriter = UnicodeWriter(resultFile, fieldnames,delimiter=',')
    detail_links = []
    for link in links:
        projects = get_projects(link,domain); # grabs the html of a tender page and soups it.
        for project in projects:
            csvWriter.writerow(dict((k, str(v).replace('\xc2\xa0', ' ').replace("\t", ""). \
                                     replace("\r", "").replace("\n", "") or '') for k, v in project.iteritems()))
            for detail_link in project['PDFs']:
                detail_links.append(detail_link)
        #print "done " + str(link)
        logFile.write("done " + str(link))
    print "Wrote tenders to file" + resultFile.name
    logFile.write("Wrote tenders to file" + resultFile.name)
    resultFile.close()

    #print "-------------done"


    
if __name__ == '__main__':
     
    # get platform
    operatingsys = 'Linux/Windows'
    kc = Keys.CONTROL
    if (sys.platform.startswith('darwin') or sys.platform.startswith('os')):
        operatingsys = 'Mac'
        kc = Keys.COMMAND
    logFile = open(LOGFILE,'w')  
    logFile.write("Operating system: " + operatingsys)

    domains = ['westsussex.bravosolution.co.uk','commercialsolutions.bravosolution.co.uk', \
               'etenderwales.bravosolution.co.uk','nhsbt.bravosolution.co.uk', \
               'bbc.bravosolution.co.uk','chelwest.bravosolution.co.uk', \
               'iewm.bravosolution.co.uk','skillsfundingagency.bravosolution.co.uk']
    domains = ['westsussex.bravosolution.co.uk','commercialsolutions.bravosolution.co.uk', \
              'etenderwales.bravosolution.co.uk'] ### works for these
    
    opp_curr = '/esop/guest/go/public/opportunity/current'
    opp_past = '/esop/guest/go/public/opportunity/past'
    
    for domain in domains:
        links = ['https://'+domain+opp_past,'https://'+domain+opp_curr]     
        filename = 'tenders_'+domain.split('.')[0]+'.csv'
        filename_details = 'tenders_details_'+domain.split('.')[0]+'.json'
        retrieve_to_file(links,filename,filename_details)

    logFile.close()
    

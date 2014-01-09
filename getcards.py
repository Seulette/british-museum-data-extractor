import requests 
from bs4 import BeautifulSoup
import json
import csv 

# these are the base urls we will scrape 
# they are urls for search queries for the specific objects we will get 
# this can be generated easily by going to "search collections" on the British Museum's website, entering parameters, 
# and copying the resulting URL 
url_heal_trade_cards = "http://www.britishmuseum.org/research/collection_online/search.aspx?searchText=trade+cards&images=true&from=ad&fromDate=1650&to=ad&toDate=1830&museumno=Heal"
url_banks_trade_cards = "http://www.britishmuseum.org/research/collection_online/search.aspx?searchText=trade+cards&images=true&from=ad&fromDate=1650&to=ad&toDate=1830&museumno=Banks"
search_urls = [url_heal_trade_cards, url_banks_trade_cards]
results_lengths = {url_heal_trade_cards: 13, url_banks_trade_cards: 1} # number of pages of search results = (number of results) mod 100

object_pages = []
object_dicts = []

image_index = 1 # initialize index for files

for search_url in search_urls: 
	# get the text and make it into a python object with BeautifulSoup
	text = ''
	for i in xrange(results_lengths[search_url]): 
		print i+1
		page_url = search_url + "&page=%s"%str(i+1)
		text += requests.get(page_url).text
	cards = BeautifulSoup(text)

	# Each page contains a grid of objects returned by the search query.
	# We need to get information from each object, and the British Museum site 
	# only allows us to get this by going to each individual object's page. 
	# So we get the href url for every object (which has an image) in the search results. 
	# We store these, and will later crawl them one by one and extract data. 
	reference_urls = []
	for div in cards.find_all('div'): 
		if 'grid_12' in div.get('class', []): 
			for a in div.find_all('a'): 
				if 'image' in a.get('class', []): 
					ref_url = 'http://www.britishmuseum.org' + a.get('href')
					print ref_url
					reference_urls.append(ref_url)

	# state the fields to use in the json, and write them in a human-readable form to be written as the header of the csv later
	### NOTE: field and header MUST stay parallel for csv writing at the end to work 
	fields = ['institution', 'object_number', 'title_of_object', 'creation_date', 'description', 'text_on_card', 'keywords', 'image_file', 'link_to_image', 'link_to_object_record', 'notes', 'location']
	header = ['Institution', 'Accession/Object Number', 'Title of Object', 'Creation/Print date','Description', 'Text on Card', 'Keywords', 'Image File Name', 'Link to Image','Link to Object Record','Notes','Location']

	for url in reference_urls: 
		url, trash = url.split("&searchText") # throw away everything after the objectID
		print url
		soup = BeautifulSoup(requests.get(url).text)
		object_pages.append(soup) # append the object so we don't have to scrape it again later in iPython 
		# set up default dictionary 
		obj_dict = {
			'institution': 'British Museum', 
			'object_number': '', 
			'title_of_object': '', 
			'creation_date': '', 
			'description': '', # description, text on card, and notes are blank by default; to be filled in by researcher 
			'text_on_card': '',  
			'keywords': '',
			'image_file': 'None',
			'link_to_image': '', 
			'link_to_object_record': url,
			'notes': '',  
			'location': 'London'
		}
		# fill it in with info as we get it
		for div in soup.find_all('div', class_='grid_12 alpha'): 
			for subdiv in div.find_all('div', class_='objectImage'): 
				obj_dict['link_to_image'] = 'http://www.britishmuseum.org' + subdiv.a.img['src']
		# find the information and build this object's dict
		for x in soup.find_all('h3'):
			# get the museum number
			if u'Museum number' in x.contents: 
				obj_dict['object_number'] = x.find_next_sibling('p').string
			if u'Description' in x.contents: 
				obj_dict['description'] = x.find_next_sibling('p').get_text()
			# idiosyncrasy of the website: sometimes the title is listed under title, sometimes under description
			if u'Title (object)' in x.contents: 
				obj_dict['title_of_object'] = x.find_next_sibling('ul').li.get_text()
			# keywords listed under Subjects
			if u'Subjects' in x.contents: # add these as keywords 
				raw_kws = x.find_next_sibling('ul').li.a.string
				kws = [kw for kw in raw_kws.split(';')]
				for i, kw in enumerate(kws): 
					kws[i] = kw.strip('(?)')
				obj_dict['keywords'] = ','.join(kws)
			if u'Date' in x.contents: 
				obj_dict['creation_date'] = x.find_next_sibling('ul').li.string
			if u'Inscriptions' in x.contents: 
				obj_dict['text_on_card'] = x.find_next_sibling('ul').li.ul.li.get_text()
		# save image to file locally 
		# we simply use an integer for the filename. this number is printed under 'Image File Name' in the csv.
		with open('image_files/%s.jpg' % str(image_index), 'w') as imfile: 
			img = requests.get(obj_dict['link_to_image']).content
			imfile.write(img)
			obj_dict['image_file'] = '%s.jpg' % str(image_index)
			image_index += 1
		# done building this dict
		print obj_dict
		object_dicts.append(obj_dict)
# write out a json file, to keep on hand 
with open('bmdbjson.json', 'w') as jsonfile: 
	json.dump(object_dicts, jsonfile)
# now, write out the csv 
# note that we use 'replace' for converting from unicode to ascii, which means that non-unicode characters will 
# show up as a question mark '?'.
with open('trade_cards.csv', 'w') as csvfile: 
	writer = csv.writer(csvfile, dialect='excel', delimiter=',')
	writer.writerow(header)
	for od in object_dicts:  
		writer.writerow([od[field].encode('ascii', 'replace') for field in fields]) 

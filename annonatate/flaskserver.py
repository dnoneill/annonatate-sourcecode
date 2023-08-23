import requests, os, PyPDF2
from bs4 import BeautifulSoup
from io import BytesIO
import re, time, json
from urllib.parse import urljoin
import concurrent.futures
import sqlite3
CONNECTIONS = 1000
TIMEOUT = 5
missing_urls = ['https://www.lib.ncsu.edu/events/paws-break', 'https://www.lib.ncsu.edu/news/main-news/through-their-gift-libraries-pete-and-theresa-dyke-support-nc-state-students-who-are', 'https://www.lib.ncsu.edu/software/leap-sdk', 'https://www.lib.ncsu.edu/events/tom-regan-visiting-fellowship-awardee-talks-dr-joshua-russell', 'https://www.lib.ncsu.edu/events/reading-and-conversation-jai-chakrabarti-jill-mccorkle', 'https://www.lib.ncsu.edu/citationbuilder/assets/plus-square-solid.svg', 'https://www.lib.ncsu.edu/jobs/shra/university-library-specialist-learning-spaces-services-1', 'https://www.lib.ncsu.edu/software/kinect-sdk', 'https://www.lib.ncsu.edu/events/paws-break-0', 'https://www.lib.ncsu.edu/citationbuilder/assets/minus-square-solid.svg', 'https://www.lib.ncsu.edu/news/main-news/libraries-announces-whitney-barlow-robles-tom-regan-visiting-research-fellow-2023', 'https://www.lib.ncsu.edu/stories/deep-dive-animal-rights-archive', 'https://www.lib.ncsu.edu/archivedexhibits/pams/index.php', 'https://www.lib.ncsu.edu/software/microsoft-access', 'https://www.lib.ncsu.edu/archivedexhibits/textiles/anniversary/content/Images_Centennial/Img_008', 'https://www.lib.ncsu.edu/news/main-news/meet-libraries-and-academic-success-center']
urls = open("seed.txt").read().strip().split("\n")
filters = open("regex-urlfilter.txt").read().strip().split("\n")
filters = list(filter(lambda x: x.startswith('#') == False and x, filters))
negativefilters = list(filter(lambda x: x.startswith('-'), filters))
negativefilters = "|".join(list(map(lambda x: x.strip('-'),negativefilters)))
positivefilters = list(filter(lambda x: x.startswith('+'), filters))
positivefilters = "|".join(list(map(lambda x: x.strip('+'),positivefilters)))
all_data = {}
process_urls = []
processed_urls = []
retry_urls = []

def checkUrl(url):
	#negpattern = re.compile(r'{}'.format(negativefilters))
	negmatch = re.search(r'{}'.format(negativefilters), url)
	positivematch = re.search(r'{}'.format(positivefilters), url)
	if positivematch and negmatch == None and url not in process_urls and url not in processed_urls:
		return True
	else:
		#print(url)
		return False

#print(;fa;dlskfa;lsdkfl;af)
def getContents(url):
	# print('get contents')
	#print(url)
	# print(checkUrl(url))
	#print(url)
	if url in missing_urls:
		print('missing url is getting got: {}'.format(url))
	try:
		response = requests.get(url)
		parseContents(response, url)
	except Exception as e:
		print(e)
		retry_urls.append(url)
		process_urls.remove(url)
		print('problem url {}$$$$$$$'.format(url))
	return 'FALJDFLDAKJFADSLKJFALKDJFALKSJFLKASDJFALSKDJFALKSDJ'
	
def getHTTP(text):
	regex = r"(https?:\S+)(?=\"|'| )"
	text = text if type(text) == str else str(text)
	url = re.findall(regex,text)
	for x in url:
		print('text or doc uri {}'.format(x))
		if checkUrl(x):
			process_urls.append(x)

def parseContents(response, original_url):
	content = ''
	page_urls = None
	title = original_url
	schemamarkup = {}
	metadata = {'description': '', 'keywords':'', 'image': '', 'imagealt': '', 'startDate': '', 'endDate': '', 'duration': '', 'location': '', 'eventStatus': ''}
	if original_url.lower().endswith('.pdf') and response.status_code < 400:
		with BytesIO(response.content) as data:
			read_pdf = PyPDF2.PdfReader(data)
			for page in range(len(read_pdf.pages)):
				if "/Annots" in read_pdf.pages[page]:
					for annot in read_pdf.pages[page]["/Annots"]:
						obj = annot.get_object()
						if '/A' in obj.keys() and '/URI' in obj['/A'].keys():
							uri = obj['/A']['/URI']
							print('pdf uri {}'.format(uri))
							if checkUrl(uri):
								process_urls.append(uri)
				content += read_pdf.pages[page].extract_text()
	elif (original_url.lower().endswith('.doc') or original_url.lower().endswith('.docx')) and response.status_code < 400:
		content = BytesIO(response.content).read()
		print(original_url)
		getHTTP(content)
		#process_urls =  process_urls + getHTTP(content)
	elif (original_url.lower().endswith('.txt')) and response.status_code < 400:
		content = response.content.decode('utf8').replace("\n", " ").replace("\t", " ").replace("\r", "")
		print(original_url)
		getHTTP(content)
		# process_urls += getHTTP(content)
	else:
		parsed_html = BeautifulSoup(response.content, "html.parser" )
		content = parsed_html.body.get_text() if parsed_html.body else 'find me no text'
		title = parsed_html.title.get_text() if parsed_html.title else original_url
		for key in metadata:
			get_content = parsed_html.find("meta",  {"property":"og:{}".format(key)})
			get_content = get_content if get_content else parsed_html.find("meta",  {"property":"{}".format(key)})
			get_content = get_content["content"] if get_content else ''
			metadata[key] = get_content
		page_urls = parsed_html.find_all(href=True)
		schemamarkup = parsed_html.find("script", {"type": "application/ld+json"})
		schemamarkup = schemamarkup.get_text("|", strip=True) if schemamarkup else schemamarkup
		if schemamarkup:
			try:
				schema = json.loads(schemamarkup)
				if 'name' in schema.keys():
					title = schema['name']
				for key in metadata:
					if key in schema.keys():
						metadata[key] = schema[key]
			except:
				pass
		data_url = original_url if response.url == original_url and original_url.replace('https://', '').split('/')[0] not in response.url else response.url
		for index, url in enumerate(page_urls):
			clean_url = url['href']
			print(clean_url)
			if 'http' not in clean_url and re.match(r'{}'.format(negativefilters), clean_url) == None:
				clean_url = urljoin(data_url, clean_url)
			clean_url = clean_url.rstrip('/').strip()
			#print(checkUrl(clean_url) and clean_url not in process_urls and clean_url not in all_data.keys() and any(url in clean_url for url in urls))
			clean_url = clean_url.rsplit("#", 1)[0].strip()
			if clean_url in missing_urls:
				print(clean_url)
				print(checkUrl(clean_url))
				print(clean_url not in process_urls)
				print(clean_url not in processed_urls)
				if clean_url in all_data.keys():
					print('in all data keys')
			if checkUrl(clean_url):
				process_urls.append(clean_url)
				if clean_url in missing_urls:
					print('its in there')
	content = content if type(content) == str else str(content)
	all_data[original_url] = metadata | {'content': content, 'title': title, 'urls_on_page': page_urls,
		'schemamarkup': schemamarkup, 'status_code': response.status_code, 'redirect_url': response.url
	}
	if response.url != original_url:
		all_data[response.url] = all_data[original_url]
	processed_urls.append(original_url)
	processed_urls.append(response.url)
	try:
		process_urls.remove(original_url)
	except Exception as e:
		print('error removign')
		print(e)

for url in urls:
	getContents(url)

while len(process_urls) > 0:
	with concurrent.futures.ThreadPoolExecutor(max_workers=CONNECTIONS) as executor:
		# print([url for url in process_urls[0:CONNECTIONS]])
		# print('100 urls')
		future_to_url = (executor.submit(getContents(url), url, TIMEOUT) for url in process_urls[0:CONNECTIONS])
		time1 = time.time()
		for future in concurrent.futures.as_completed(future_to_url):
			print('all_data {}'.format(len(all_data.keys())))
			pass
			print('process_urls {}'.format(len(process_urls)))
	time2 = time.time()
	# process_urls = list(set(process_urls))
	# print(len(process_urls))
	# if process_urls[0] not in processed_urls:
	# 	getContents(process_urls[0])
	# else:
	# 	print('else statement')
	# 	process_urls.remove(process_urls[0])

conn = sqlite3.connect('crawl_db')
c = conn.cursor()
c.execute('''
          CREATE TABLE IF NOT EXISTS crawls
          ([crawl_url] TEXT PRIMARY KEY, [content] TEXT, [jsondata] TEXT)
          ''')
conn.commit()

for key, value in all_data.items():

	try:
		c.execute('''
	      INSERT OR REPLACE INTO crawls (crawl_url, content, jsondata)
	          VALUES
	            (?, ?, ?)
	    ''', (key, value['content'], json.dumps(value['schemamarkup'])))
		conn.commit()
	except Exception as e:
		print(value['content'])
		print(key)
		print(e)

existing = {k:v for k,v in all_data.items() if v['status_code'] < 400 and 'notfound' not in v['redirect_url']}
print(len(all_data.keys()))
print(list(all_data.keys()))
print(len(existing.keys()))
print(existing.keys())

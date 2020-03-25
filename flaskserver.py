from flask import Flask, jsonify, url_for, session
from flask import request, render_template, redirect
from flask_session import Session

from flask_cors import CORS
import json, os, glob, requests
import base64
from settings import *
from bs4 import BeautifulSoup
import yaml
import re
import string, random
import uuid
import simplejson as json
import pylibmc
from flask_github import GitHub
import re

app = Flask(__name__,
            static_url_path='',
            static_folder='static',)
app.config.update(
                  SESSION_TYPE = 'filesystem',
                  GITHUB_CLIENT_ID = client_id,
                  GITHUB_CLIENT_SECRET = client_secret
                  )
Session(app)
github = GitHub(app)


@app.before_request
def before_request():
    user = None
    if 'user_id' in session:
        user = session['user_id']

@app.route('/login')
def login():
    return github.authorize(scope="repo")

@app.route('/authorize')
@github.authorized_handler
def authorized(oauth_token):
    next_url = request.args.get('next') or url_for('index')
    if oauth_token is None:
        #flash("Authorization failed.")
        return redirect(next_url)
    
    session['user_token'] = oauth_token
    userinfo = requests.get('https://api.github.com/user', headers={'Authorization': 'token {}'.format(oauth_token)}).json()
    session['user_id'] = userinfo['login']
    session['github_url'] = "https://api.github.com/repos/{}/{}/contents".format(session['user_id'], github_repo)
    session['origin_url'] = "https://{}.github.io/{}".format(session['user_id'],github_repo)
    session['user_name'] = userinfo['name'] if userinfo['name'] != None else userinfo['login']
    return redirect(next_url)

@app.route('/')
def index():
    if 'user_id' in session:
        manifestdata = []
        arraydata = getContents()
        for manifest in manifests:
            manifestdata.append({'manifestUri': manifest})
        return render_template('index.html', filepaths=arraydata, manifests=manifestdata, firstmanifest=manifests[0])
    else:
        return redirect('/login')

@app.route('/search')
def search():
    query = request.args.get('q')
    allcontent = querysearch(query)
    tags = request.args.get('tag')
    if tags:
        allcontent = searchfields(allcontent['items'], 'tags', tags)
    items = allcontent['items']
    tags = allcontent['tags']
    if request.args.get('format') == 'json':
        return jsonify(items), 200
    else:
        uniqtags = sorted(list(set(tags)))
        tagcount = {x:tags.count(x) for x in uniqtags}
        sortedtagcount = dict(sorted(tagcount.items(), key=(lambda x: (-x[1], x[0]))))
        return render_template('search.html', results=items, tags=sortedtagcount, query=query)

def querysearch(fieldvalue):
    tags = []
    items = []
    content = getContents()
    for key, value in content.items():
        for resource in value['resources']:
            results = get_search(resource)
            listtags = results['tags']
            results['tags'] = " ".join(results['tags'])
            if fieldvalue in " ".join(list(results.values())):
                items.append(results)
                results['tags'] = listtags
                tags.extend(listtags)
    return {'items': items, 'tags': tags}

def searchfields(content, field, fieldvalue):
    tags = []
    items = []
    for anno in content:
        if fieldvalue in anno[field]:
            items.append(anno)
            tags.extend(anno['tags'])
    return {'items': items, 'tags': tags}

def getContents():
    arraydata = {}
    canvases = getannotations()
    for canvas in canvases:
        if canvas['canvas'] in arraydata.keys():
            arraydata[canvas['canvas']].append(canvas['json'])
        else:
            arraydata[canvas['canvas']] = [canvas['json']]
    return arraydata

@app.route('/annotations/', methods=['GET'])
def listannotations():
    lists = getContents()
    format = request.args.get('type') if request.args.get('type') else 'storyboard'
    return render_template('annotations.html', annotations=lists, format=format)

def getannotations():
    if 'annotations' not in session.keys():
        response = requests.get('{}'.format(session['origin_url']))
        content = json.loads(response.content.decode('utf-8').replace('&lt;', '<').replace('&gt;', '>'))
        for item in content:
            item['canvas'] = item['json']['on'][0]['full'] if 'on' in item['json'].keys() else ''
        session['annotations'] = content
    else:
        content = session['annotations']
    return content

annotations = []
@app.route('/create_annotations/', methods=['POST'])
def create_anno():
    response = json.loads(request.data)
    data_object = response['json']
    uniqid = str(uuid.uuid1())
    filename = "{}.json".format(uniqid)
    data_object['@id'] = "{{site.url}}{{site.baseurl}}/%s"%(filename)
    cleanobject = cleananno(data_object)
    code = writetogithub(filename, cleanobject)
    return jsonify(data_object), code

@app.route('/update_annotations/', methods=['POST'])
def update_anno():
    response = json.loads(request.data)
    data_object = response['json']
    id = cleanid(data_object['@id'])
    cleanobject = cleananno(data_object)
    code = writetogithub(id, cleanobject)
    return jsonify(data_object), code

@app.route('/delete_annotations/', methods=['DELETE', 'POST'])
def delete_anno():
    response = json.loads(request.data)
    id = cleanid(response['id'])
    annotatons = getannotations()
    canvas = list(filter(lambda x: id in x['filename'], session['annotations']))[0]['canvas']
    deletefiles = [id]
    canvases = getContents()
    if len(canvases[canvas]) == 1:
        deletefiles.append(listfilename(canvas))
    delete_annos(deletefiles)
    return jsonify({"File Removed": True}), 201

@app.route('/write_annotation/', methods=['POST'])
def write_annotation():
    data = json.loads(request.data)
    json_data = data['json']
    file = filepath if data['type'] == 'annotation' else '_ranges'
    filename = os.path.join(file, data['filename'])
    for id in data['deleteids']:
        fileid = cleanid(id)
        deletefiles = [os.path.join(filepath, fileid)]
        delete_annos(deletefiles)
    if 'list' in json_data['@type'].lower() or 'page' in json_data['@type'].lower():
        for anno in json_data['resources']:
            id = cleanid(anno['@id'])
            single_filename = os.path.join(file, id)
            writetogithub(single_filename, anno)
    writetogithub(filename, json_data)
    return jsonify({"Annotations Written": True}), 201

def cleananno(data_object):
    field = 'resource' if 'resource' in data_object.keys() else 'body'
    charfield = 'chars' if 'resource' in data_object.keys() else 'value'
    if field in data_object.keys():
        for item in data_object[field]:
            replace = re.finditer(r'&lt;iiif-(.*?)&gt;&lt;\/iiif-(.*?)&gt;', item[charfield])
            for rep in replace:
                replacestring = rep.group().replace("&lt;","<").replace("&gt;", ">").replace("&quot;", '"')
                item[charfield] =  item[charfield].replace(rep.group(), replacestring)
    return data_object

def cleanid(id):
    return id.split('/')[-1].replace('.json', '') + '.json'

def delete_annos(annolist):
    for anno in annolist:
        data = createdatadict(anno, 'delete')
        print(data)
        if 'sha' in data['data'].keys():
            payload = {'ref': github_branch}
            response = requests.delete(data['url'], headers={'Authorization': 'token {}'.format(session['user_token'])}, data=json.dumps(data['data']), params=payload)
            print(response.content)
            return response

def to_pretty_json(value):
    return json.dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '))

app.jinja_env.filters['tojson_pretty'] = to_pretty_json

def github_get_existing(full_url, filename):
    path_sha = {}
    if 'github_sha' not in session.keys():
        payload = {'ref': github_branch}
        existing = requests.get(full_url, headers={'Authorization': 'token {}'.format(session['user_token'])}, params=payload).json()
        if type(existing) == list and len(existing) > 0:
            for item in existing:
                path_sha[item['path']] = item['sha']
        session['github_sha'] = path_sha
    else:
        path_sha = session['github_sha']
    if filename in path_sha.keys():
        return path_sha[filename]
    else:
        return ''

def updatelistdate(singleanno, annolist, created=False):
    if created and 'created' in singleanno.keys():
        annolist['created'] = singleanno['created']
    elif 'created' in singleanno.keys():
        annolist['modified'] = singleanno['created']
    if created and 'oa:annotatedAt' in singleanno.keys():
        annolist['oa:annotatedAt'] = singleanno['oa:annotatedAt']
    elif 'oa:annotatedAt' in singleanno.keys():
        annolist['oa:serializedAt'] = singleanno['oa:annotatedAt']
    if 'modified' in singleanno.keys():
        annolist['modified'] = singleanno['modified']
    if 'oa:serializedAt' in singleanno.keys():
        annolist['oa:serializedAt'] = singleanno['oa:serializedAt']
    return annolist

def writetogithub(filename, annotation, yaml=False):
    response = sendgithubrequest(filename, annotation)
    print(response.content)
    if response.status_code < 400:
        session['github_sha'][filename] = response.json()['content']['sha']
        canvas = annotation['on'][0]['full']
        data = {'canvas':canvas, 'json': annotation, 'filename': filename}
        canvases = list(map(lambda x: x['canvas'], session['annotations']))
        session['annotations'].append(data)
        if canvas not in canvases:
            createlistpage(canvas)
    return response.status_code

def sendgithubrequest(filename, annotation):
    data = createdatadict(filename, annotation)
    response = requests.put(data['url'], data=json.dumps(data['data']),  headers={'Authorization': 'token {}'.format(session['user_token'])})
    return response

def createlistpage(canvas):
    filename = listfilename(canvas)
    text = '---\ncanvas_id: "' + canvas + '"\n---\n{% assign annotations = site.pages | where: "canvas", page.canvas_id | map: "content" %}{"@context": "http://iiif.io/api/presentation/2/context.json","@id": "{{ site.url }}{{ site.baseurl }}{{page.url}}","@type": "sc:AnnotationList","resources": [{{ annotations | join: ","}}] }'
    sendgithubrequest(filename, text)

def listfilename(canvas):
    r = re.compile("\d+")
    canvaslist = canvas.split('/')
    withnumbs = list(filter(r.search, canvaslist))
    filename = "-".join(withnumbs) if len(withnumbs) > 0 else canvaslist[-1]
    return filename + '-list.json'

def createdatadict(filename, text):
    full_url = "{}/{}/{}".format(session['github_url'], filepath, filename)
    sha = github_get_existing(full_url, filename)
    writeordelete = "write" if text != 'delete' else "delete"
    message = "{} {}".format(writeordelete, filename)
    text = '---\ncanvas: "{}"\n---\n{}'.format(text['on'][0]['full'], json.dumps(text)) if type(text) != str else text
    data = {"message":message, "content": base64.b64encode(text.encode('utf-8')).decode('utf-8'), "branch": github_branch }
    if sha != '':
        data['sha'] = sha
    return {'data':data, 'url':full_url}

def writetofile(filename, annotation, yaml=False):
    anno_text = annotation if yaml else json.dumps(annotation)
    with open(filename, 'w') as outfile:
        outfile.write(anno_text)

def get_search(anno):
    annodata_data = {'tags': [], 'content': [], 'datecreated':'', 'datemodified': '', 'id': anno['@id'], 'url': url_for('static', filename=anno['@id'])}
    if 'oa:annotatedAt' in anno.keys():
        annodata_data['datecreated'] = encodedecode(anno['oa:annotatedAt'])
    if 'created' in anno.keys():
        annodata_data['datecreated'] = encodedecode(anno['created'])
    if 'oa:serializedAt' in anno.keys():
        annodata_data['datemodified'] = encodedecode(anno['oa:serializedAt'])
    if 'modified' in anno.keys():
        annodata_data['datemodified'] = encodedecode(anno['modified'])
    textdata = anno['resource'] if 'resource' in anno.keys() else anno['body']
    textdata = textdata if type(textdata) == list else [textdata]
    for resource in textdata:
        chars = BeautifulSoup(resource['chars'], 'html.parser').get_text() if 'chars' in resource.keys() else ''
        chars = encodedecode(chars)
        if chars and 'tag' in resource['@type'].lower():
            annodata_data['tags'].append(chars)
        elif 'purpose' in resource.keys() and 'tag' in resource['purpose']:
            tags_data = chars if chars else resource['value']
            annodata_data['tags'].append(encodedecode(tags_data))
        elif chars:
            annodata_data['content'].append(chars)
        elif 'items' in resource.keys():
            field = 'value' if 'value' in resource['items'][0].keys() else 'chars'
            fieldvalues = " ".join([encodedecode(item[field]) for item in resource['items']])
            annodata_data['content'].append(fieldvalues)
        elif 'value' in resource:
            annodata_data['content'].append(encodedecode(resource['value']))
    annodata_data['content'] = " ".join(annodata_data['content'])
    return annodata_data

def encodedecode(chars):
    if type(chars) == str:
        return chars
    else:
        return chars.encode('utf8')

if __name__ == "__main__":
    app.run(debug=True)

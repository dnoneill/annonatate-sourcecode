from flask import Flask, jsonify, url_for, session
from flask import request, render_template, redirect, send_file, flash
from flask_session import Session
from werkzeug.utils import secure_filename

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
import shutil
from datetime import datetime
from iiif_prezi.factory import ManifestFactory
import os

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
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
app.config['UPLOAD_FOLDER'] = uploadfolder


@app.before_request
def before_request():
    user = None
    if 'user_id' in session:
        user = session['user_id']

@app.route('/login')
def login():
    return github.authorize(scope="repo,user")

@app.route('/authorize')
@github.authorized_handler
def authorized(oauth_token):
    next_url = request.args.get('next') or url_for('index')
    if oauth_token is None:
        #flash("Authorization failed.")
        return redirect(next_url)
    
    session['user_token'] = oauth_token
    
    populateuserinfo()
    session['currentworkspace'] = session['workspaces'][list(session['workspaces'].keys())[0]]
    
    populateworkspace()
    
    return redirect(next_url)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/createimage', methods=['POST', 'GET'])
def createimage():
    if 'file' not in request.files:
        flash('No file part')
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        tmpfilepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(tmpfilepath)
        iiiffolder = os.path.splitext(filename)[0]
        prefix = "{{site.url}}{{site.baseurl}}/images"
        stream = os.popen("iiif_static.py {} -p {} -d {}".format(tmpfilepath, prefix, app.config['UPLOAD_FOLDER']))
        stream.read()
        iiifpath = os.path.join(app.config['UPLOAD_FOLDER'], iiiffolder)
        infocontents = open(os.path.join(iiifpath, 'info.json')).read()
        createjekyllfile(infocontents,'info.json', iiifpath)
        manifest = createmanifest(filename, tmpfilepath,iiiffolder, request.form)
        manifest = manifest.toString(compact=False).replace('canvas/info.json', 'info.json').replace('https://{{site.url}}', '{{site.url}}')
        createjekyllfile(manifest, 'manifest.json', iiifpath)
        os.remove(tmpfilepath)
        output = os.path.join(app.config['UPLOAD_FOLDER'], iiiffolder)
        shutil.make_archive(output, 'zip', iiifpath)
        shutil.rmtree(iiifpath)
        return render_template('uploadsuccess.html', output="{}.zip".format(iiiffolder))

def createjekyllfile(contents, filename, iiifpath):
    jekyllstring = "---\n---\n{}".format(contents)
    with open(os.path.join(iiifpath, filename), 'w') as file:
        file.write(jekyllstring)

def createmanifest(filename, tmpfilepath,iiiffolder, formdata):
    fac = ManifestFactory()
    outputiiif = os.path.join(app.config['UPLOAD_FOLDER'], iiiffolder)
    imgurl = "https://{{site.url}}{{site.baseurl}}/images/"
    url = "{}{}".format(imgurl, iiiffolder)
    fac.set_base_prezi_uri(url)
    fac.set_base_prezi_dir(outputiiif)
    fac.set_base_image_uri(imgurl)
    fac.set_iiif_image_info(2.0, 2)
    manifest = fac.manifest(ident='manifest', label=formdata['label'])
    manifest.viewingDirection = formdata['direction']
    manifest.description = formdata['description']
    manifest.set_metadata({"rights": formdata['rights']})
    seq = manifest.sequence()
    cvs = seq.canvas(ident='info', label=formdata['label'])
    anno = cvs.annotation()
    img = anno.image(iiiffolder, iiif=True)
    img.set_hw_from_file(tmpfilepath)
    cvs.height = img.height
    cvs.width = img.width
    return manifest

@app.route('/download', methods=['POST'])
def download():
    path = os.path.join(app.config['UPLOAD_FOLDER'], request.form['path'])
    return send_file(path, as_attachment=True)

@app.route('/')
def index():
    if 'user_id' in session:
        manifestdata = []
        arraydata = getContents()
        allmanifests = manifests + session['manifests']
        for manifest in allmanifests:
            manifestdata.append({'manifestUri': manifest})
        return render_template('index.html', filepaths=arraydata, manifests=manifestdata, firstmanifest=manifests[0])
    else:
        return redirect('/login')

@app.route('/workspaces')
def workspaces():
    populateuserinfo()
    session['annotations'] = ''
    return render_template('workspaces.html')

@app.route('/changeworkspace', methods=['POST'])
def changeworkspace():
    workspace = request.form['workspace']
    session['currentworkspace'] = session['workspaces'][workspace]
    populateworkspace()
    next_url = request.args.get('next') or url_for('index')
    return redirect(next_url)

@app.route('/add_collaborator', methods=['POST'])
def add_collaborator():
    username = request.form['username']
    permission = request.form['permission']
    contributorurl = collaburl = session['currentworkspace']['collaborators_url'].split('{')[0] + '/' + username
    params = {'permission': permission}
    response = github.raw_request('put', contributorurl, params=params)
    next_url = request.args.get('next') or url_for('index')
    return redirect('/contributors')

@github.access_token_getter
def token_getter():
    if 'user_token' in session.keys():
        return session['user_token']

def populateuserinfo():
    workspaces = {}
    userinfo = github.get(githubuserapi)
    session['user_id'] = userinfo['login']
    session['avatar_url'] = userinfo['avatar_url']
    session['user_name'] = userinfo['name'] if userinfo['name'] != None else userinfo['login']
    
    repos = github.get('{}/repos?per_page=200'.format(githubuserapi))
    relevantworkspaces = list(filter(lambda x: x['name'] == github_repo, repos))
    for workspace in relevantworkspaces:
        workspaces[workspace['full_name']] = workspace
    if len(workspaces) == 0:
        payload = {"name": github_repo, "description": "This is your first repository","private": False, "owner": session['user_id']}
        response = github.post('https://api.github.com/repos/dnoneill/annotationtemplate/forks')
        #enablepages = github.post('{}/pages'.format(response['url']), headers={'Authorization': 'token {}'.format(session['user_token']), 'Accept': 'application/vnd.github.switcheroo-preview+json'}, params={"source": {"branch": "master","path": "/"}})
        workspaces[response['full_name']] = response
    session['workspaces'] = workspaces

def populateworkspace():
    session['github_url'] = session['currentworkspace']['contents_url'].replace('/{+path}', '')
    pagesinfo = github.get('{}/pages'.format(session['currentworkspace']['url']))
    session['origin_url'] = pagesinfo['html_url']
    session['github_branch'] = pagesinfo['source']['branch']
    session['isadmin'] = session['currentworkspace']['permissions']['admin']

@app.route('/search')
def search():
    query = request.args.get('q')
    allcontent = querysearch(query)
    tags = request.args.get('tag')
    if tags:
        allcontent = searchfields(allcontent['items'], 'tags', tags)
    creator = request.args.get('creator')
    if creator:
        allcontent = searchfields(allcontent['items'], 'creator', creator)
    items = allcontent['items']
    if request.args.get('format') == 'json':
        return jsonify(items), 200
    else:
        facets = {}
        for key, value in allcontent['facets'].items():
            value = [x for x in value if x is not None]
            uniqtags = sorted(list(set(value)))
            tagcount = {x:value.count(x) for x in uniqtags}
            sortedtagcount = dict(sorted(tagcount.items(), key=(lambda x: (-x[1], x[0]))))
            facets[key] = sortedtagcount
        annolength = len(list(filter(lambda x: '-list.json' not in x['filename'], session['annotations'])))
        return render_template('search.html', results=items, facets=facets, query=query, annolength=annolength)

def querysearch(fieldvalue):
    facets = {}
    items = []
    fieldvalue = fieldvalue if fieldvalue else ''
    for item in session['annotations']:
        if '-list.json' not in item['filename']:
            results = get_search(item['json'])
            if fieldvalue in " ".join(list(results['searchfields'].values())):
                items.append(results)
                facets = mergeDict(facets, results['facets'])
    return {'items': items, 'facets': facets}

def searchfields(content, field, fieldvalue):
    facets = {}
    items = []
    for anno in content:
        if fieldvalue in anno['facets'][field]:
            items.append(anno)
            facets = mergeDict(facets, anno['facets'])
    return {'items': items, 'facets': facets}


def mergeDict(dict1, dict2):
    dict3 = {**dict1, **dict2}
    for key, value in dict3.items():
        if key in dict1 and key in dict2:
            dict3[key] = value + dict1[key]
    return dict3

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
    duration = 61
    if 'annotime' in session.keys():
        now = datetime.now()
        duration = (now - session['annotime']).total_seconds()
    if 'annotations' not in session.keys() or session['annotations'] == '' or  duration > 60:
        response = requests.get('{}'.format(session['origin_url']))
        content = json.loads(response.content.decode('utf-8').replace('&lt;', '<').replace('&gt;', '>'))
        for item in content['annotations']:
            item['canvas'] = item['json']['on'][0]['full'] if 'on' in item['json'].keys() else ''
        session['annotations'] = content['annotations']
        
        session['manifests'] = content['manifests']
        session['annotime'] = datetime.now()
        annotations = content['annotations']
    else:
        annotations = session['annotations']
    return annotations

@app.route('/create_annotations/', methods=['POST'])
def create_anno():
    response = json.loads(request.data)
    data_object = response['json']
    uniqid = str(uuid.uuid1())
    filename = "{}.json".format(uniqid)
    data_object['@id'] = "{{site.url}}{{site.baseurl}}/%s/%s"%(filepath.replace("_", ""), filename)
    data_object['oa:annotatedBy'] = [session['user_name']]
    cleanobject = cleananno(data_object)
    response = writetogithub(filename, cleanobject)
    returnvalue = response.content if response.status_code > 399 else data_object
    return jsonify(returnvalue), response.status_code

@app.route('/update_annotations/', methods=['POST'])
def update_anno():
    response = json.loads(request.data)
    data_object = response['json']
    id = cleanid(data_object['@id'])
    currentcreators = data_object['oa:annotatedBy'] if data_object['oa:annotatedBy'] else []
    currentcreators.append(session['user_name'])
    data_object['oa:annotatedBy'] = list(set(currentcreators))
    cleanobject = cleananno(data_object)
    response = writetogithub(id, cleanobject)
    returnvalue = response.content if response.status_code > 399 else data_object
    return jsonify(returnvalue), response.status_code

@app.route('/delete_annotations/', methods=['DELETE', 'POST'])
def delete_anno():
    response = json.loads(request.data)
    id = cleanid(response['id'])
    annotatons = getannotations()
    canvas = list(filter(lambda x: id in x['filename'], session['annotations']))[0]['canvas']
    canvases = getContents()
    response = delete_annos(id)
    if len(canvases[canvas]) == 1:
        delete_annos(listfilename(canvas))
    return jsonify({"File Removed": True}), response

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

@app.route('/profile/')
def getprofiledata():
    invites = github.get('{}/repository_invitations'.format(githubuserapi))
    collaburl = session['currentworkspace']['collaborators_url'].split('{')[0]
    collaborators = github.get(collaburl)
    return render_template('profile.html', userinfo={'name':session['user_name']}, invites=invites, collaborators=collaborators)

@app.route('/acceptinvite/', methods=['POST'])
def acceptinvite():
    inviteurl = request.form['inviteurl']
    response = github.raw_request('patch', inviteurl)
    populateuserinfo()
    return redirect('/profile'), 200

@app.route('/updateprofile/', methods=['POST'])
def updateprofile():
    next_url = request.args.get('next') or url_for('index')
    profile_data = request.form.to_dict()
    response = github.raw_request('patch', githubuserapi, data=json.dumps(profile_data))
    session['user_name'] = profile_data['name']
    return redirect(next_url)

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

def delete_annos(anno):
    data = createdatadict(anno, 'delete')
    if 'sha' in data['data'].keys():
        payload = {'ref': session['github_branch']}
        response = github.raw_request('delete', data['url'], data=json.dumps(data['data']), params=payload)
        if response.status_code < 400:
            session['annotations'] = [x for x in session['annotations'] if x['filename'] != anno]
        return response.status_code
    else:
        return 400

def to_pretty_json(value):
    return json.dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '))

app.jinja_env.filters['tojson_pretty'] = to_pretty_json

def github_get_existing(full_url, filename):
    path_sha = {}
    full_url = os.path.dirname(full_url)
    duration = 61
    if 'githubtime' in session.keys():
        now = datetime.now()
        duration = (now - session['githubtime']).total_seconds()
    if 'github_sha' not in session.keys() or filename not in session['github_sha'].keys() or duration > 60:
        payload = {'ref': session['github_branch']}
        existing = github.raw_request('get',full_url, params=payload).json()
        if type(existing) == list and len(existing) > 0:
            for item in existing:
                path_sha[os.path.basename(item['path'])] = item['sha']
        session['github_sha'] = path_sha
        session['githubtime'] = datetime.now()
    else:
        path_sha = session['github_sha']
    if filename in path_sha.keys():
        return path_sha[filename]
    else:
        return ''

def writetogithub(filename, annotation):
    response = sendgithubrequest(filename, annotation)
    if response.status_code < 400:
        session['github_sha'][filename] = response.json()['content']['sha']
        canvas = annotation['on'][0]['full']
        data = {'canvas':canvas, 'json': annotation, 'filename': filename}
        canvases = list(map(lambda x: x['canvas'], session['annotations']))
        existinganno = list(filter(lambda n: n.get('filename') == filename, session['annotations']))
        if len(existinganno) > 0:
            annoindex = session['annotations'].index(existinganno[0])
            session['annotations'][annoindex] = data
        else:
            session['annotations'].append(data)
        if canvas not in canvases:
            createlistpage(canvas)
    return response

def sendgithubrequest(filename, annotation):
    data = createdatadict(filename, annotation)
    response = github.raw_request('put', data['url'], data=json.dumps(data['data']))
    return response

def createlistpage(canvas):
    filename = listfilename(canvas)
    text = '---\ncanvas_id: "' + canvas + '"\n---\n{% assign annotations = site.annotations | where: "canvas", page.canvas_id | map: "content" %}{"@context": "http://iiif.io/api/presentation/2/context.json","@id": "{{ site.url }}{{ site.baseurl }}{{page.url}}","@type": "sc:AnnotationList","resources": [{{ annotations | join: ","}}] }'
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
    data = {"message":message, "content": base64.b64encode(text.encode('utf-8')).decode('utf-8'), "branch": session['github_branch'] }
    if sha != '':
        data['sha'] = sha
    return {'data':data, 'url':full_url}

def get_search(anno):
    annodata_data = {'searchfields': {'content': []}, 'facets': {'tags': [], 'creator': []}, 'datecreated':'', 'datemodified': '', 'id': anno['@id'].replace('{{site.url}}{{site.baseurl}}/', session['origin_url']), 'basename': os.path.basename(anno['@id'])}
    if 'oa:annotatedAt' in anno.keys():
        annodata_data['datecreated'] = encodedecode(anno['oa:annotatedAt'])
    if 'created' in anno.keys():
        annodata_data['datecreated'] = encodedecode(anno['created'])
    if 'oa:serializedAt' in anno.keys():
        annodata_data['datemodified'] = encodedecode(anno['oa:serializedAt'])
    if 'modified' in anno.keys():
        annodata_data['datemodified'] = encodedecode(anno['modified'])
    if anno['oa:annotatedBy']:
        annodata_data['facets']['creator'] = anno['oa:annotatedBy']
    textdata = anno['resource'] if 'resource' in anno.keys() else anno['body']
    textdata = textdata if type(textdata) == list else [textdata]
    for resource in textdata:
        chars = BeautifulSoup(resource['chars'], 'html.parser').get_text() if 'chars' in resource.keys() else ''
        chars = encodedecode(chars)
        if chars and 'tag' in resource['@type'].lower():
            annodata_data['facets']['tags'].append(chars)
        elif 'purpose' in resource.keys() and 'tag' in resource['purpose']:
            tags_data = chars if chars else resource['value']
            annodata_data['facets']['tags'].append(encodedecode(tags_data))
        elif chars:
            annodata_data['searchfields']['content'].append(chars)
        elif 'items' in resource.keys():
            field = 'value' if 'value' in resource['items'][0].keys() else 'chars'
            fieldvalues = " ".join([encodedecode(item[field]) for item in resource['items']])
            annodata_data['searchfields']['content'].append(fieldvalues)
        elif 'value' in resource:
            annodata_data['searchfields']['content'].append(encodedecode(resource['value']))
    annodata_data['searchfields']['content'] = " ".join(annodata_data['searchfields']['content'])
    annodata_data['searchfields']['tags'] = " ".join(annodata_data['facets']['tags'])
    return annodata_data

def encodedecode(chars):
    if type(chars) == str:
        return chars
    else:
        return chars.encode('utf8')

if __name__ == "__main__":
    app.run(debug=True)

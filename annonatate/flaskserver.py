from flask import Flask, jsonify, url_for, session,g
from flask import request, render_template, redirect, send_file, flash
from flask_session import Session
import urllib.parse

import json, os, glob, requests
import base64
from settings import *
import yaml, time, csv
import re
import simplejson as json
from flask_github import GitHub
from datetime import datetime
import os

from utils.search import get_search, encodedecode, Search
from utils.image import Image
from utils.iiiffunctions import addAnnotationList
from utils.collectionform import CollectionForm, parseboard, parsetype

app = Flask(__name__,
            static_url_path='',
            )
app.config.update(
                  SESSION_TYPE = 'filesystem',
                  GITHUB_CLIENT_ID = client_id,
                  GITHUB_CLIENT_SECRET = client_secret
                  )
Session(app)
github = GitHub(app)
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
app.config['UPLOAD_FOLDER'] = uploadfolder
githubfilefolder = 'annonatate/static/githubfiles/'
@app.before_request
def before_request():
    user = None
    nolandingpage = ['login', 'authorized', 'logout', 'static']
    if 'user_id' in session:
        user = session['user_id']
    elif request.endpoint not in nolandingpage:
        return render_template('landingpage.html')
    g.error = ''
    if 'login_time' in session.keys():
        timediff = (datetime.now() - datetime.strptime(session['login_time'], '%Y-%m-%d %H:%M:%S.%f')).seconds
        if timediff > 259200:
            session.clear()
            return redirect('/login')
    if request.args.get('firstbuild') != 'True' and request.endpoint not in nolandingpage and 'currentworkspace' in session.keys() and session['currentworkspace']:
        check = workspaceCheck(request.method)
        if check == 'problem':
            return 'You have lost access to {}, please go to the profile page to change workspaces or refresh this page to have it automatically choose a new workspace for you.'.format(session['currentworkspace']['full_name']), 400
    
def getDefaults():
    if 'currentworkspace' in session.keys():
        currentworkspace = session['currentworkspace']
        if 'annonatate-wax' in currentworkspace['description'].lower():
            apiurl = 'api/all.json'
            return {'annotations': '_annotations', 
            'apiurl': apiurl,
            'customviews': '_exhibits',
            'collections': 'collections',
            'iswax': True,
            'index': os.path.join(githubfilefolder, apiurl)
            }
        else:
            return {'annotations': '_annotations', 
            'apiurl': '', 
            'customviews': 'customviews', 
            'collections': 'collections',
            'iswax': False,
            'index': os.path.join(githubfilefolder, 'index.html')
            }

@app.route('/login')
def login():
    argsnext = urllib.parse.quote(request.args.get('next')) if request.args.get('next') else url_for('index')
    nexturl = url_for('authorized', _external=True) + "?next={}".format(argsnext)
    return github.authorize(scope="repo,workflow", redirect_uri=nexturl)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('https://github.com/logout')

@app.route('/authorize')
@github.authorized_handler
def authorized(oauth_token):
    if oauth_token is None:
        #flash("Authorization failed.")
        return render_template('error.html')
        #return redirect(next_url)
    session['user_token'] = oauth_token
    session['login_time'] = str(datetime.now())
    session['defaults'] = getDefaults()
    isfirstbuild = buildWorkspaces()
    next_url = request.args.get('next')
    if next_url and isfirstbuild != True:
        getContents()
    else:
        next_url =  url_for('index', firstbuild=isfirstbuild)
    return redirect(next_url)

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/sitestatus')
def sitestatus():
    content, status_code = origin_contents()
    timediff = (datetime.now() - datetime.strptime(session['login_time'], '%Y-%m-%d %H:%M:%S.%f')).seconds
    if status_code > 299 and timediff > 40:
        triggerbuild()
    time.sleep(1)
    return content, status_code

@app.route('/uploadstatus')
def uploadstatus():
    url = request.args.get('url')
    checknum = request.args.get('checknum')
    uploadtype = request.args.get('uploadtype') + 's'
    response = requests.get(url)
    if uploadtype != 'customviews' and url not in session['upload'][uploadtype]:
        session['upload'][uploadtype].append(url)
    if response.status_code > 299:
        if checknum == '1':
            triggerbuild()
        elif checknum == '2':
            updateindex(False)
        return 'failure', 404
    if uploadtype == 'customviews':
        deleteItemAnnonCustomViews(url, 'slug')
    return 'success', 200

def deleteItemAnnonCustomViews(url, deletetype=''):
    for key, value in session['annocustomviews'].items():
        for index, item in enumerate(value):
            if item == url or (type(item) == dict and item['filename'] == url):
                if deletetype:
                    if type(item) == dict and deletetype in item.keys():
                        del session['annocustomviews'][key][index][deletetype]
                else:
                    del session['annocustomviews'][key][index]
                break

@app.route('/rename', methods=['POST'])
def renameGitHub():
    oldname = request.form['workspace']
    newname = request.form['newname']
    oldworkspace = session['workspaces'][oldname]
    oldurl = oldworkspace['url']
    newhtmlurl = '{}.github.io/{}'.format(oldworkspace['owner']['login'], newname)
    iscurrentworkspace = session['currentworkspace']['full_name'] == oldname
    updatedata = {'homepage': newhtmlurl, 'name': newname}
    response = github.raw_request('patch', oldurl, data=json.dumps(updatedata))
    if response.status_code < 299:
        content = response.json()
        del session['workspaces'][oldname]['url']
        session['workspaces'][content['full_name']] = content
        if iscurrentworkspace:
            session['currentworkspace'] = content
            session['defaults'] = getDefaults()
            updateworkspace(content['full_name'])
            session['annotime'] = datetime.now()
    else:
        error = parseGitHubErrors(response.json())
        return redirect('/profile?renameerror={}'.format(error))
    return redirect('/profile')

@app.route('/removecollaborator', methods=['POST'])
def removecollaborator():
    collaburl = session['currentworkspace']['collaborators_url'].split('{')[0]
    user = request.form['user']
    collaburl += '/{}'.format(user)
    response = github.raw_request('DELETE', collaburl)
    next_url = request.args.get('next') or url_for('index')
    if response.status_code > 299:
        next_url += '?error={}'.format(parseGitHubErrors(response.json()))
    return redirect(next_url)

@app.route('/createimage', methods=['POST', 'GET'])
def createimage():
    image = Image(request.form, request.files, session['origin_url'])

    if not image.isimage:
        if type(image.manifest) == dict:
            return render_template('upload.html', error=image.manifest['error'])
        response = sendgithubrequest("manifest.json", image.manifest_markdown, image.manifestpath).json()
        uploadtype = 'manifest'
        if 'content' in response.keys():
            uploadurl ='{}{}'.format(image.origin_url, response['content']['path'].replace('_manifest', 'manifest'))
            output = True
        else:
            output = response['message']
    else:
        response = sendgithubrequest(image.file.filename, image.encodedimage, "images").json()
        uploadtype='image'
        if 'content' in response.keys():
            uploadurl = "{}{}".format(image.origin_url, response['content']['path'])
            output =  True
        else:
            output = response['message']
    triggerbuild()
    return render_template('uploadsuccess.html', output=output, uploadurl=uploadurl, uploadtype=uploadtype)


@app.route('/processwaxcollection', methods=['POST', 'GET'])
def processwaxcollection():
    collectionname = request.form['waxcollection']
    csvfile = request.files['collectioncsv'].stream.read()
    sendgithubrequest('{}.csv'.format(collectionname), csvfile, '_data')
    reader = csv.DictReader(csvfile.decode().splitlines())
    actions = github.get('{}/actions/workflows'.format(session['currentworkspace']['url']))
    hasaction = list(filter(lambda action: action['name'] == collectionname, actions['workflows']))
    if len(hasaction) > 0:
        triggerAction(hasaction[0]['id'])
    else:
        updateconfig(collectionname, reader.fieldnames)
        yamlcontents = open(os.path.join(githubfilefolder, 'action.yml')).read()
        yamlcontents = yamlcontents.replace('replacewithcollection', collectionname)
        yamlcontents = yamlcontents.replace('replacewithbranch', session['currentworkspace']['default_branch'])
        response = sendgithubrequest('.github/workflows/{}.yml'.format(collectionname), yamlcontents)
        if response.status_code < 299:
            time.sleep(1)
            triggerAction(response.json()['content']['name'])
    return redirect(url_for('upload'))

def triggerAction(ident):
    currrentworkspace = session['currentworkspace']
    response = github.raw_request('post', '{}/actions/workflows/{}/dispatches'.format(currrentworkspace['url'], ident), headers={'Accept': 'application/vnd.github.v3+json'}, data=json.dumps({"ref":currrentworkspace['default_branch']}))
    print(response.content)

@app.route('/download', methods=['POST'])
def download():
    path = os.path.join(app.config['UPLOAD_FOLDER'], request.form['path'])
    return send_file(path, as_attachment=True)

@app.route('/createcollections', methods=['GET', 'POST'])
@app.route('/createcollections/<collectionid>', methods=['GET', 'POST'])
def createcollection(collectionid=''):
    if 'collections' not in session.keys():
        updateindex()
    if request.method == 'POST':
        jsonitems = json.loads(request.data)
        title=jsonitems['title']
        collection = session['collections'][title] if title in session['collectionnames'] and jsonitems['add'] == True else {"json": {"label": title,"type": "storyboardlist","items": []}}
        for item in jsonitems['annotations']:
            url = item['url']
            if url:
                board = item['board'] if 'board' in item.keys() and item['board'] else "<%s annotationurl='%s'></%s>"%(item['viewtype'], url, item['viewtype'])
                board = {"board": board
                , "title": item['title'], "description": item['description'], "thumbnail": item["thumbnail"]}
                if "annotation" in item.keys() and item["annotation"]:
                    board['annotation'] = json.loads(item['annotation'])
                if url in session['annocollections'].keys() and title not in session['annocollections'][url]:
                    session['annocollections'][url].append(title)
                else:
                    session['annocollections'][url] = [title]
                collection['json']['items'].append(board)
            contents = '---\n---\n{}'.format(json.dumps(collection['json'], indent=4).replace('null', '""'))
        session['collections'][title] = collection
        if title not in session['collectionnames']:
            session['collectionnames'].append(title)
        sendgithubrequest('{}.json'.format(title), contents, session['defaults']['collections'])
        return redirect('/collections')
    else:
        formvalues = CollectionForm(collectionid, request, session['collections']).formvalues
        return render_template('createcollection.html', formvalues=formvalues)

@app.route('/collections')
@app.route('/collections/<collectionid>', methods=['GET'])
def collections(collectionid=''): 
    if 'collections' not in session.keys():
        collections = {}
    elif collectionid:
        collections = {collectionid: session['collections'][collectionid]}
    else:
        collections=session['collections']
    return render_template('collections.html', collections=collections, collectionurl='{}{}'.format(session['origin_url'], session['defaults']['collections']))

@app.route('/')
def index():
    if 'user_id' in session:
        try:
            data, status = origin_contents()
            if status > 299:
                return errorchecking(request)
            arraydata = getContents()
            manifests = session['preloaded']['manifests'] + session['upload']['manifests']
            images = session['preloaded']['images'] + session['upload']['images']
            existing = {'manifests': manifests, 'images': images}
            return render_template('index.html', existingitems=existing, filepaths=arraydata['contents'], tags=list(set(arraydata['tags'])), userinfo={'name': session['user_name'], 'id': session['user_id']})
        except:
           return errorchecking(request)

def errorchecking(request):
    firstbuild = request.args.get('firstbuild')
    if firstbuild == 'True':
        return render_template('firstbuild.html')
    elif firstbuild == 'noworkspaces':
        return render_template('error.html', message='There was a problem enabling GitHub pages on your site. Please follow the <a href="https://annonatate.github.io/annonatate-help/getting-started#troubleshooting">troubleshooting instructions to fix this problem.</a>')
    else:
        triggerbuild()
        #sendgithubrequest('index.html', open(indexfile, "r").read(), '')
        return render_template('error.html', message='''<b>If this
        is your first time logging into your website, is still being built
        and that is why you are seeing this error page.
        Please wait a minute and try refreshing the page.<b>
        <p>There is a problem with your website: <a href='{}'>{}</a></p>
        <p>Please refresh the page. If it is not working after a minute
        please delete or rename your repository
        <a href='{}/settings'>{}/settings</a> and refresh the page.</p>'''.format(session['origin_url'], session['origin_url'], session['currentworkspace']['html_url'], session['currentworkspace']['html_url']))

@app.route('/changeworkspace', methods=['POST'])
def changeworkspace():
    workspace = request.form['workspace']
    next_url = request.args.get('next') or url_for('index')
    prevworkspace = session['currentworkspace']['full_name']
    updateworkspace(workspace)
    content, status_code = origin_contents()
    if status_code < 299:
        getContents()
    else:
        if 'wax' in session['currentworkspace']['description'].lower():
            try:
                github.get(session['currentworkspace']['contents_url'].replace('/{+path}', session['defaults']['apiurl']))
            except:
                updateWax()
        triggerbuild()
        next_url += '?switcherror={}'.format(workspace)
        updateworkspace(prevworkspace)
    return redirect(next_url)

def updateWax():
    updateconfig()
    updateindex()

def updateconfig(collection='', searchfields=''):
    configfilenames = '_config.yml'
    config = github.get(session['currentworkspace']['contents_url'].replace('/{+path}', configfilenames))
    decodedcontents = base64.b64decode(config['content']).decode('utf-8')
    contentsyaml = yaml.load(decodedcontents, Loader=yaml.FullLoader)
    if collection:
        contentsyaml['collections'][collection] = {'output': True, 'layout': 'qatar_item',
        'metadata': {'source': '{}.csv'.format(collection)},
        'images': {'source': 'raw_images/{}'.format(collection)},
        }
        contentsyaml['search']['main']['collections'][collection] = {'content': False, 'fields': searchfields}
    else:
        contentsyaml['collections']['annotations'] = {'output': True, 'permalink': '/annotations/:name'}
        contentsyaml['baseurl'] = '/' + session['currentworkspace']['name']
    if 'url' in contentsyaml.keys() and 'minicomp.github.io' in contentsyaml['url']:
        del contentsyaml['url']
    updatedcontents = yaml.dump(contentsyaml)
    sendgithubrequest(configfilenames, updatedcontents)

def updateworkspace(workspace):
    clearSessionWorkspaces()
    session['currentworkspace'] = session['workspaces'][workspace]
    session['defaults'] = getDefaults()
    populateworkspace()

@app.route('/add_collaborator', methods=['POST'])
def add_collaborator():
    username = request.form['username']
    permission = request.form['permission']
    contributorurl = session['currentworkspace']['collaborators_url'].split('{')[0] + '/' + username
    params = {'permission': permission}
    response = github.raw_request('put', contributorurl, params=params)
    next_url = request.args.get('next') or url_for('index')
    return redirect('/profile/')

@app.route('/create_annotations/', methods=['POST'])
def create_anno():
    response = json.loads(request.data)
    data_object = response['json']
    filename = data_object['id'].replace("#", "") + '.json'
    data_object['id'] = "{{site.url}}{{site.baseurl}}/%s/%s"%(filepath.replace("_", ""), filename)
    cleanobject = cleananno(data_object)
    canvas = cleanobject['target']['source']
    listlength = len(list(filter(lambda n: canvas == n.get('canvas'), session['annotations'])))
    response = writetogithub(filename, cleanobject, listlength+1)
    returnvalue = response.content if response.status_code > 399 else data_object
    returnvalue['order'] = listlength+1
    return jsonify(returnvalue), response.status_code

@app.route('/update_annotations/', methods=['POST'])
def update_anno():
    response = json.loads(request.data)
    data_object = response['json']
    order = data_object['order']
    id = cleanid(data_object['id'])
    cleanobject = cleananno(data_object)
    response = writetogithub(id, cleanobject, response['order'])
    returnvalue = response.content if response.status_code > 399 else data_object
    returnvalue['order'] = order
    return jsonify(returnvalue), response.status_code

@app.route('/delete_annotations/', methods=['DELETE', 'POST'])
def delete_anno():
    response = json.loads(request.data)
    id = cleanid(response['id'])
    annotatons = getannotations()
    canvas = list(filter(lambda x: id in x['filename'], session['annotations']))[0]['canvas']
    canvases = getContents()['contents']
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
    if 'list' in json_data['type'].lower() or 'page' in json_data['type'].lower():
        for anno in json_data['resources']:
            id = cleanid(anno['id'])
            single_filename = os.path.join(file, id)
            writetogithub(single_filename, anno)
    writetogithub(filename, json_data)
    return jsonify({"Annotations Written": True}), 201

@app.route('/profile/')
def getprofiledata():
    invites = github.get('{}/repository_invitations'.format(githubuserapi))
    collaburl = session['currentworkspace']['collaborators_url'].split('{')[0]
    collaborators = github.get(collaburl)
    populateuserinfo()
    orgs()
    return render_template('profile.html', userinfo={'name':session['user_name']}, invites=invites, collaborators=collaborators)

def orgs():
    if 'orgs' not in session.keys():
        allorgs = [session['user_id']]
        orgs = github.get('{}/orgs'.format(githubuserapi))
        allorgs += list(map(lambda x: x['login'], orgs))
        session['orgs'] = allorgs

@app.route('/deletefile/', methods=['POST'])
def deletefile():
    url = request.args.get('file')
    fullfile = url.replace(session['origin_url'], '').strip('/')
    path, filename = fullfile.rsplit('/', 1)
    if path == session['defaults']['customviews'].strip('_'):
        path = session['defaults']['customviews']
        deleteItemAnnonCustomViews(url)
        filename += '.html'
    elif path == session['defaults']['collections'].strip('_'):
        path = session['defaults']['collections']
        collectionname = urllib.parse.unquote(filename.replace('.json', ''))
        session['collectionnames'].remove(collectionname)
        del session['collections'][collectionname]
        for key, value in session['annocollections'].items():
            if collectionname in value:
                session['annocollections'][key].remove(collectionname)
    else:
        uploadtype = path.split('/')[0]
        session['upload'][uploadtype].remove(url)
    payload = {'ref': session['github_branch']}
    data = createdatadict(filename, 'delete', path)
    response = github.raw_request('delete', data['url'], data=json.dumps(data['data']), params=payload)
    return redirect(request.args.get('next'))

def deletebykey(dictlist, key, match):
    for index,item in enumerate(dictlist):
        if item[key].strip('/') == match.strip('/'):
            del dictlist[index]
            break
    return dictlist

@app.route('/acceptinvite/', methods=['POST'])
def acceptinvite():
    inviteurl = request.form['inviteurl']
    response = github.raw_request('patch', inviteurl)
    populateuserinfo()
    return redirect('/profile')

@app.route('/search')
def search():
    search = Search(request.args, session['annotations'])

    if request.args.get('format') == 'json':
        return jsonify(search.items), 200
    else:
        annolength = len(list(filter(lambda x: '-list' not in x['filename'], session['annotations'])))
        return render_template('search.html', results=search.items, facets=search.facets, query=search.query, annolength=annolength)

@app.route('/annotations/', methods=['GET'])
@app.route('/annotations/<annoid>', methods=['GET'])
def listannotations(annoid=''):
    items = getannotations()
    if annoid:
        lists = list(filter(lambda x: annoid in x['filename'], items))
    else:
        lists = list(filter(lambda x: '-list' not in x['filename'], items)) if request.args.get('annotype') == 'single' else list(filter(lambda x: '-list' in x['filename'], items))
    format = request.args.get('viewtype') if request.args.get('viewtype') else 'annotation'
    return render_template('annotations.html', annotations=lists, format=format, filepath=filepath, annoid=annoid)

@app.route('/customviews')
def customviews():
    return render_template('customviews.html')

@app.route('/annonaview')
def annonaview():
    return render_template('annonabuilder.html')

@app.route('/saveannonaview', methods=['POST'])
def saveannonaview():
    jsonitems = json.loads(request.data)
    frontmatter = ''
    if session['defaults']['iswax']:
        title = jsonitems['slug'].replace('_', ' ').title()
        date = datetime.now().strftime('%Y-%m-%d')
        frontmatter = 'title: {}\nlayout: exhibit\nauthor: {}\npublish_date: {}\n'.format(title, session['user_name'], date)
    folder = session['defaults']['customviews']
    content = """---\n{}---\n
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://ncsu-libraries.github.io/annona/dist/annona.js"></script>
        <link rel="stylesheet" type="text/css" href="https://ncsu-libraries.github.io/annona/dist/annona.css">
    </head>
    <body>
    {}
    </body>
    </html>""".format(frontmatter, jsonitems['tag'])
    response = sendgithubrequest('{}.html'.format(jsonitems['slug']), content, folder)
    if response.status_code < 300:
        annourl = parseboard(jsonitems['tag'])['url']
        fileurl = os.path.join(session['origin_url'], folder.strip('_'), jsonitems['slug']) + '/'
        if annourl in session['annocustomviews'] and annourl not in session['annocustomviews'][annourl]:
            if fileurl not in session['annocustomviews'][annourl]:
                session['annocustomviews'][annourl].append({'slug': jsonitems['slug'], 'filename': fileurl})
        elif annourl:
            session['annocustomviews'][annourl] = [{'slug': jsonitems['slug'], 'filename': fileurl}]
    return jsonify(response.content), response.status_code

@app.route('/updatedata', methods=['POST'])
def updatedata():
    data = request.form['updatedata']
    jsondata = json.loads(data)
    yamldata = yaml.dump(jsondata)
    sendgithubrequest('preload.yml', yamldata, '_data')
    session['preloaded'] = jsondata
    return redirect('/profile?tab=data')
@github.access_token_getter
def token_getter():
    if 'user_token' in session.keys():
        return session['user_token']

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def buildWorkspaces():
    isfirstbuild = populateuserinfo()
    if isfirstbuild != 'noworkspaces':
        if 'currentworkspace' not in session.keys() or not session['currentworkspace']:
            session['currentworkspace'] = session['workspaces'][list(session['workspaces'].keys())[0]]
            session['defaults'] = getDefaults()
        populateworkspace()
    return isfirstbuild

def triggerbuild(url=False):
    pagebuild = url if url else session['currentworkspace']['url'] + '/pages'
    return github.raw_request("post", '{}/builds'.format(pagebuild), headers={'Accept': 'application/vnd.github.mister-fantastic-preview+json'})


def populateuserinfo():
    workspaces = {}
    userinfo = github.get(githubuserapi)
    firstbuild = False
    session['user_id'] = userinfo['login']
    session['avatar_url'] = userinfo['avatar_url']
    session['user_name'] = userinfo['name'] if userinfo['name'] != None else userinfo['login']
    repos = github.get('{}/repos?per_page=300&sort=name'.format(githubuserapi))
    relevantworkspaces = list(filter(lambda x: x['name'] == github_repo or (x['description'] and 'annonatate' in x['description'].lower()), repos))
    for workspace in relevantworkspaces:
        workspaces[workspace['full_name']] = workspace
    if len(workspaces) == 0:
        response = github.post('https://api.github.com/repos/annonatate/{}/forks'.format(github_repo))
        time.sleep(1)
        enablepages = enablepagesfunc(response['url'])
        if enablepages.status_code > 299:
            enablepages = enablepagesfunc(response['url'])
        if enablepages.status_code > 299:
            firstbuild = 'noworkspaces'
            workspaces[response['full_name']] = response
        else:
            updates = {'homepage': enablepages.json()['html_url']}
            updatehomepage = github.raw_request('patch', response['url'], data=json.dumps(updates))
            workspaces[response['full_name']] = response
            firstbuild = True
    session['workspaces'] = workspaces
    return firstbuild

def enablepagesfunc(pagesurl):
    branches = {'source': {'branch': github_branch,'path': '/'}}
    enablepages = github.raw_request('post', '{}/pages'.format(pagesurl), data=json.dumps(branches), headers={'Accept': 'application/vnd.github.switcheroo-preview+json'})
    return enablepages

@app.route('/add_repos', methods=['POST'])
def add_repos():
    owner = request.form['owner']
    name = request.form['name']
    private = True if 'private' in request.form else False
    repodata = {
        'owner': owner,
        'name': name,
        'private': private,
        'description': 'annonatate'
    }
    response = github.raw_request('post', 'https://api.github.com/repos/annonatate/{}/generate'.format(github_repo),headers={'Accept': 'application/vnd.github.baptiste-preview+json'}, data=json.dumps(repodata)).json()
    if 'url' in response.keys():
        time.sleep(1)
        enablepages = enablepagesfunc(response['url'])
        if enablepages.status_code > 299:
            error = 'problem enabling GitHub pages. Did it manually or delete this repository.'
            return redirect('/profile?tab=profile&error={}'.format(error))
    else:
        error = parseGitHubErrors(response.json())
        return redirect('/profile?tab=profile&error={}'.format(error))
    return redirect('/profile?tab=profile')

def parseGitHubErrors(response):
    firsterror = response['errors'][0] if 'errors' in response.keys() else response
    error = firsterror['message'] if 'message' in firsterror else firsterror
    return error

def clearSessionWorkspaces(): 
    for key in list(session.keys()):
        if 'user' not in key and 'workspaces' not in key:
            del session[key]
            
def clearSession():
    for key in list(session.keys()):
        if 'user' not in key:
            del session[key]

def populateworkspace():
    session['github_url'] = session['currentworkspace']['contents_url'].replace('/{+path}', '')
    try:
        pagesinfo = github.get('{}/pages'.format(session['currentworkspace']['url']))
        session['origin_url'] = pagesinfo['html_url']
        session['github_branch'] = pagesinfo['source']['branch']
        session['isadmin'] = session['currentworkspace']['permissions']['admin']
    except:
        return render_template('error.html', message="<p>There is a problem with your GitHub pages site. Try <a href='https://docs.github.com/en/github/working-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site'>enabling the website</a> or deleting/renaming the repository <a href='{}/settings'>{}/settings</a></p>".format(session['currentworkspace']['html_url'], session['currentworkspace']['html_url']))

def getContents():
    arraydata = {}
    canvases = getannotations()
    tags = []
    for canvas in canvases:
        loadcanvas = canvas['json']
        if 'resources' not in loadcanvas.keys():
            searchfields = get_search(loadcanvas)
            tags += searchfields['facets']['tags']
            loadcanvas['order'] = canvas['order']
        if canvas['canvas'] in arraydata.keys():
            arraydata[canvas['canvas']].append(loadcanvas)
        else:
            arraydata[canvas['canvas']] = [loadcanvas]
    return {'contents': arraydata, 'tags': tags}

def getannotations():
    duration = 36
    if 'annotime' in session.keys():
        now = datetime.now()
        duration = (now - session['annotime']).total_seconds()
    if 'annotations' not in session.keys() or session['annotations'] == '' or  duration > 35:
        content, status = origin_contents()
        for item in content['annotations']:
            item['canvas'] = item['json']['target']['source'] if 'target' in item['json'].keys() else ''
        session['annotations'] = content['annotations']
        if 'preloadedcontent' not in content.keys():
            updateindex()
            session['preloaded'] = {'manifests': content['manifests'], 'images': content['images']}
            session['upload'] = {'manifests': [], 'images' : []}
        if 'preloadedcontent' in content.keys() and ('preloaded' not in session.keys() or duration > 60):
            parsecollections(content)
            session['preloaded'] = content['preloadedcontent']
            session['upload'] = {'images': content['images'], 'manifests': content['manifests']}
        parsecustomviews(content)
        session['annotime'] = datetime.now()
        updateAnnosGitHub()
        annotations = session['annotations']
        if status > 299:
            session['annotations'] = ''
    else:
        annotations = session['annotations']
        githubresponse = updateAnnosGitHub()
        if githubresponse:
            filenames = list(map(lambda x: x['filename'].split('/')[-1], session['annotations']))
            notinsession = list(filter(lambda x: x['name'] not in filenames and '-list' not in x['name'],githubresponse))
            #beforefilenames = list(map(lambda x: x['filename'].split('/')[-1], annotations))
            #remove = list(set(beforefilenames).difference(filenames))
            for item in notinsession:
                downloadresponse = github.get(item['download_url'])
                contentssplit = downloadresponse.content.decode("utf-8").rsplit('---\n', 1)
                yamlparse = yaml.load(contentssplit[0], Loader=yaml.FullLoader)
                yamlparse['json'] = json.loads(contentssplit[-1])
                yamlparse['filename'] = item['name']
                filenamelist = listfilename(yamlparse['canvas'])
                indexof = [idx for idx, annotation in enumerate(session['annotations']) if filenamelist in annotation['filename']]
                session['annotations'].append(yamlparse)
                if len(indexof) > 0:
                    session['annotations'][indexof[0]]['json']['resources'].append(yamlparse['json'])
                else:
                    session['annotations'].append({'filename': filenamelist, 'order': None, 'json': {"@context": "http://iiif.io/api/presentation/2/context.json","id": "{}".format(filenamelist),"type": "AnnotationPage","items": [yamlparse['json']]}, 'canvas': ''})
            annotations = session['annotations']
    return annotations

def parsecustomviews(content):
    parseddict = {}
    for customview in content['customviews']:
        annourl = parseboard(customview['json'])['url']
        if annourl in parseddict.keys() and customview['filename'] not in parseddict[annourl]:
            parseddict[annourl].append(customview['filename'])
        else:
            parseddict[annourl] = [customview['filename']]
    session['annocustomviews'] = parseddict

def parsecollections(content):
    session['collections'] = {}
    session['collectionnames'] = []
    session['annocollections'] = {}
    if 'collections' in content.keys():
        for collection in content['collections']:
            session['collectionnames'].append(collection['json']['label'])
            for item in collection['json']['items']:
                annourl = parseboard(item['board'])['url']
                if annourl in session['annocollections'].keys():
                    if collection['json']['label'] not in session['annocollections'][annourl]:
                        session['annocollections'][annourl].append(collection['json']['label'])
                else:
                    session['annocollections'][annourl] = [collection['json']['label']]
            session['collections'][collection['json']['label']] = collection
    else:
        updateindex()

def updateindex(updateConfig=True):
    index = session['defaults']['index']
    contents = open(index).read()
    sendgithubrequest(index.replace(githubfilefolder, ''), contents)

def updateAnnosGitHub():
    annotations = session['annotations']
    try:
        githubresponse = github.get(session['currentworkspace']['contents_url'].replace('{+path}', session['defaults']['annotations']))
        githubfilenames = list(map(lambda x: x['name'], githubresponse))
        session['annotations'] = list(filter(lambda x: x['filename'].split('/')[-1] in githubfilenames,annotations))
        return githubresponse
    finally:
        return False

def origin_contents():
    apiurl = session['origin_url'] + session['defaults']['apiurl']
    response = requests.get(apiurl)
    if response.status_code > 299:
        response = requests.get(apiurl + 'index.html')
    try:
        content = json.loads(response.content.decode('utf-8').replace('&lt;', '<').replace('&gt;', '>'))
    except:
        content = {'annotations': [], 'images': [], 'manifests': [], 'customviews': [], 'collections': []}
    return content, response.status_code

def cleananno(data_object):
    if 'order' in data_object.keys():
        del data_object['order']
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
            session['annotations'] = [x for x in session['annotations'] if anno not in x['filename']]
        return response.status_code
    else:
        return 400

def to_pretty_json(value):
    return json.dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '))
app.jinja_env.filters['tojson_pretty'] = to_pretty_json

def github_get_existing(full_url):
    payload = {'ref': session['github_branch']}
    match = False
    if '/images/' in full_url:
        full_url, match = full_url.strip('/').rsplit('/', 1)
    existing = github.raw_request('get',full_url, params=payload).json()
    if match and type(existing) == list:
        matches = list(filter(lambda x: x['name'] == match, existing))
        existing = matches[0] if len(matches) > 0 else matches
    if 'sha' in existing:
        return existing['sha']
    else:
        return ''

def writetogithub(filename, annotation, order):
    githuborder = 'order: {}\n'.format(order)
    folder = session['defaults']['annotations']
    response = sendgithubrequest(filename, annotation, folder, githuborder)
    if response.status_code < 400:
        canvas = annotation['target']['source']
        manifest = annotation['target']['dcterms:isPartOf']['id'] if 'dcterms:isPartOf' in annotation['target'].keys() else ''
        data = {'canvas':canvas, 'json': annotation, 'filename': filename, 'order': order}
        canvases = list(map(lambda x: x['canvas'], session['annotations']))
        existinganno = list(filter(lambda n: filename in n.get('filename'), session['annotations']))
        annolistfilename = listfilename(canvas)
        existinglist = list(filter(lambda n: annolistfilename in n.get('filename'), session['annotations']))
        if len(existinganno) > 0:
            annoindex = session['annotations'].index(existinganno[0])
            session['annotations'][annoindex] = data
        else:
            session['annotations'].append(data)
        if len(existinglist) > 0:
            annolistindex = session['annotations'].index(existinglist[0])
            canvasannos = list(filter(lambda n: canvas == n.get('canvas'), session['annotations']))
            session['annotations'][annolistindex]['json']['resources'] = list(map(lambda k: k.get('json'), canvasannos))
        else:
            listdata = {'json': {'resources': [data['json']]}, 'filename':annolistfilename, 'canvas': ''}
            session['annotations'].append(listdata)
        response = requests.get(manifest)
        if canvas not in canvases:
            createlistpage(canvas, manifest)
        session['annotime'] = datetime.now()
    return response


def sendgithubrequest(filename, annotation, path='', order=''):
    data = createdatadict(filename, annotation, path, order)
    response = github.raw_request('put', data['url'], data=json.dumps(data['data'], indent=4))
    return response

def createlistpage(canvas, manifest):
    filenameforlist = listfilename(canvas)
    filename = os.path.join(session['defaults']['annotations'], filenameforlist)
    text = '---\ncanvas_id: "' + canvas + '"\n---\n{% assign annotations = site.annotations | where: "canvas", page.canvas_id | sort: "order" | map: "content" %}\n{\n"@context": "http://iiif.io/api/presentation/2/context.json",\n"id": "{{ site.url }}{{ site.baseurl }}{{page.url}}",\n"type": "AnnotationPage",\n"resources": [{{ annotations | join: ","}}] }'
    sendgithubrequest(filename, text)
    if manifest in session['upload']['manifests']:
        response = requests.get(manifest)
        urlforlist = os.path.join(session['origin_url'], session['defaults']['annotations'].replace('_', ''), filenameforlist)
        manifestwithlist = addAnnotationList(response.json(), canvas, urlforlist, session['origin_url'])
        manifestfilename = manifest.replace(session['origin_url'], '')
        response = sendgithubrequest(manifestfilename, manifestwithlist)

def listfilename(canvas):
    r = re.compile("\d+")
    canvas = canvas.replace('.json', '')
    canvaslist = canvas.split('/')
    withnumbs = list(filter(r.search, canvaslist))
    filename = "-".join(withnumbs) if len(withnumbs) > 0 else canvaslist[-1]
    filename = re.sub('[^A-Za-z0-9]+', '-', filename).lower()
    return filename + '-list.json'
app.jinja_env.filters['listfilename'] = listfilename

# def listfilenamelink(canvas):
#     return "%s%s/%s"%(session['origin_url'], filepath.replace("_", ""), listfilename(canvas))
# app.jinja_env.filters['listfilenamelink'] = listfilenamelink

def createdatadict(filename, text, path='', order=''):
    full_url = os.path.join(session['github_url'], path, filename)
    sha = github_get_existing(full_url)
    writeordelete = "write" if text != 'delete' else "delete"
    message = "{} {}".format(writeordelete, filename)
    text = '---\ncanvas: "{}"\n{}---\n{}'.format(text['target']['source'],order, json.dumps(text, indent=4)) if type(text) != str and type(text) != bytes else text
    text = text.encode('utf-8') if type(text) != bytes else text
    data = {"message":message, "content": base64.b64encode(text).decode('utf-8'), "branch": session['github_branch'] }
    if sha != '':
        data['sha'] = sha
    return {'data':data, 'url':full_url}

def workspaceCheck(method=False):
    collaburl = session['currentworkspace']['collaborators_url'].split('{')[0]
    response = github.raw_request('get', collaburl)
    if response.status_code > 299:
        prevsession = session['currentworkspace']
        if 'bad credentials' in response.json()['message'].lower():
            session.clear()
            return redirect('/login')
        elif method == 'POST':
            return 'problem'
        else:
            clearSession()
        buildWorkspaces()

        getContents()
        g.error = '<i class="fas fa-exclamation-triangle"></i> You have lost access to {}, we have updated your workspace to {}'.format(prevsession['full_name'], session['currentworkspace']['full_name'])
        
if __name__ == "__main__":
    app.run(debug=True)

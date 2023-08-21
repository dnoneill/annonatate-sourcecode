from flask import Flask, jsonify, url_for, session,g
from flask import request, render_template, redirect, send_file, flash
from flask_session import Session
import urllib.parse

import json, os, glob, requests
from annonatate.settings import *
import yaml, time, csv
import re
import simplejson as json
#from flask_github import GitHub
import shutil
from datetime import datetime, timedelta
import os
from io import StringIO

from annonatate.utils.search import get_search, encodedecode, Search
from annonatate.utils.image import Image, addAnnotationList, listfilename, getThumbnailTitle
from annonatate.utils.collectionform import CollectionForm, parseboard, parsetype
from annonatate.utils.github import GitHubAnno
from annonatate.utils.annogetters import getCanvas, getManifest, contextType, isMirador
app = Flask(__name__,
            static_url_path='',)
app.config.update(
                  SESSION_TYPE = 'filesystem',
                  GITHUB_CLIENT_ID = client_id,
                  GITHUB_CLIENT_SECRET = client_secret
                  )
Session(app)
github = GitHubAnno(app)
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
app.config['UPLOAD_FOLDER'] = uploadfolder
githubfilefolder = 'annonatate/static/githubfiles/'
currentversion = '2.0'
#Before every page loads this runs a series of tests
@app.before_request
def before_request():
    #pages that should have have a landing page when not logged in
    nolandingpage = ['login', 'authorized', 'logout', 'static']
    # if not logged in and the page is no the login/authorized/logout or static file show landing page
    if 'user_id' not in session.keys() and '_anno' in request.endpoint:
        return 'You have been logged out of the application. You will now be redirected to the login page.', 418
    elif 'user_id' not in session.keys() and request.endpoint not in nolandingpage:
        if landingpage:
            return render_template('landingpage.html')
        else:
            return redirect('/login')
    g.error = ''
    # If the user has been logged in for longer than 3 days, clear the session and log them back in
    if 'login_time' in session.keys():
        timediff = (datetime.now() - datetime.strptime(session['login_time'], '%Y-%m-%d %H:%M:%S.%f')).seconds
        if timediff > 259200:
            clearSession('currentworkspace')
            return redirect('/login')
    # if the site is not building for the first time and it is not the login/authorized/logout/static item,
    #and there is a workplace selected check to make sure the user still had access to the workspace (hasn't been deleted, access has been revoked)
    if request.args.get('firstbuild') != 'True' and request.endpoint not in nolandingpage and 'currentworkspace' in session.keys() and session['currentworkspace']:
        check = workspaceCheck(request.method)
        if check == 'problem':
            return 'You have lost access to {}, please go to the profile page to change workspaces or refresh this page to have it automatically choose a new workspace for you.'.format(session['currentworkspace']['full_name']), 400

# check defaults, sets defaults for an annontate repo/wax repo
def getDefaults():
    if 'currentworkspace' in session.keys():
        currentworkspace = session['currentworkspace']
        topicdescription = currentworkspace['topics']
        if currentworkspace['description']:
            topicdescription.append(currentworkspace['description'].lower())
        if 'annonatate-wax' in topicdescription:
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

#logins in by redirecting to the authorize route which is part of GitHub flask library
#feeds redirect url to authorize function
@app.route('/login')
def login():
    argsnext = urllib.parse.quote(request.args.get('next')) if request.args.get('next') else url_for('index')
    nexturl = url_for('authorized', _external=True) + "?next={}".format(argsnext)
    if set_user_token:
        return authorized()
    else:
        return github.authorize(scope="repo,workflow", redirect_uri=nexturl)

# clears session, redirects to github logout
@app.route('/logout')
def logout():
    clearSession()
    return redirect('https://github.com/logout?return_to=https://annonatate.fly.dev')

#After logging into GitHub, library returns oauth token, load that token into session
#add login time, get defaults, get/build workspaces
# if it is not first build get the contents of the API, else go to the first build page
@app.route('/authorize')
@github.authorized_handler
def authorized(oauth_token):
    if set_user_token:
        oauth_token = set_user_token
    if oauth_token is None:
        #flash("Authorization failed.")
        return render_template('error.html')
        #return redirect(next_url)
    session['user_token'] = oauth_token
    session['login_time'] = str(datetime.now())
    isfirstbuild = buildWorkspaces()
    session['defaults'] = getDefaults()
    next_url = request.args.get('next')
    if next_url and 'origin_url' in session.keys():
        getContents()
    else:
        next_url =  url_for('index', firstbuild=isfirstbuild)
    return redirect(next_url)

# render upload template
@app.route('/upload')
def upload():
    tabs = get_tabs('upload')
    return render_template('upload.html', tabs=tabs)

# check the status of the github site
# if the site returns error code and you have not just logged in, send trigger code to GitHub pages
@app.route('/sitestatus')
def sitestatus():
    content, status_code = origin_contents()
    if status_code > 299:
        triggerbuild()
    time.sleep(1)
    return content, status_code

# Check the status of uploads (custom views/images/manifests)
# If an upload is not rendering, after the second try, trigger a site rebuild,
# after the third try, write the index in hopes of triggering a build
# If successfully able to reach the item, return 200 status code
@app.route('/uploadstatus')
def uploadstatus():
    url = request.args.get('url')
    checknum = request.args.get('checknum')
    uploadtype = request.args.get('uploadtype') + 's'
    isprofile = request.args.get('isprofile')
    response = requests.get(url)
    actionname = request.args.get('actionname')
    if response.status_code > 299:
        if checknum == '3' and 'derivatives' not in url:
            triggerbuild()
        elif checknum == '5' and 'derivatives' not in url:
            updateindex()
        if actionname:
            getActions()
            currentaction = list(filter(lambda x: x['name'] == actionname, session['actions']))
            if len(currentaction) > 0 and currentaction[0]['conclusion'] == 'failure':
                session['inprocess'] = list(filter(lambda x: x['url'] != url, session['inprocess']))
                return 'An error occured during the processing of: {}. You can check what happened here: <a href="{}">{}</a>'.format(actionname, currentaction[0]['html_url'],currentaction[0]['html_url']), 400
        return '{} not rendered yet'.format(url), 404
    if uploadtype == 'customviews':
        deleteItemAnnonCustomViews(url, 'slug')
    elif url not in session['upload'][uploadtype]:
        session['upload'][uploadtype].append(url)
    if isprofile:
        session['inprocess'] = list(filter(lambda x: x['url'] != url, session['inprocess']))
    return 'success', 200

# Delete items from annocustomviews by URL
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

# Rename GitHub repo, update workspaces in session
@app.route('/rename', methods=['POST'])
def renameGitHub():
    oldname = session['currentworkspace']['full_name']
    newname = request.form['newname']
    oldworkspace = session['workspaces'][oldname]
    oldurl = oldworkspace['url']
    newhtmlurl = '{}.github.io/{}'.format(oldworkspace['owner']['login'], newname)
    updatedata = {'homepage': newhtmlurl, 'name': newname}
    response = github.raw_request('patch', oldurl, data=json.dumps(updatedata))
    if response.status_code < 299:
        content = response.json()
        del session['workspaces'][oldname]['url']
        session['workspaces'][content['full_name']] = content
        session['currentworkspace'] = content
        session['defaults'] = getDefaults()
        updateworkspace(content['full_name'])
    else:
        error = parseGitHubErrors(response.json())
        return redirect('/profile?renameerror={}'.format(error))
    return redirect('/profile')

# Remove collaborator from workspace
@app.route('/updatecollaborator', methods=['POST'])
def updatecollaborator():
    collaburl = session['currentworkspace']['collaborators_url'].split('{')[0]
    user = request.form['user']
    permission = request.form['permission']
    collaburl += '/{}'.format(user)
    if permission == 'remove':
        response = github.raw_request('DELETE', collaburl)
    else:
        response = github.raw_request('PUT', collaburl, data=json.dumps({"permission":permission}))
    next_url = request.args.get('next') or url_for('index')
    if response.status_code > 299:
        next_url += '?error={}'.format(parseGitHubErrors(response.json()))
    return redirect(next_url)

@app.route('/uploadvocab', methods=['POST'])
def uploadvocab():
    filevocab = request.files['vocabcsv']
    csvcontents = StringIO(filevocab.stream.read().decode("UTF8"), newline=None)
    reader = csv.DictReader(csvcontents)
    vocab = []
    for row in reader:
        row = dict(row)
        if row['uri']:
            vocab.append(row)
        else:
            vocab.append(row['label'])
    vocab =  vocab + [i for i in session['preloaded']['vocab'] if i not in vocab] if session['preloaded'] and 'vocab' in session['preloaded'].keys() else vocab
    session['preloaded']['vocab'] = vocab
    github.sendgithubrequest(session, 'preload.yml', yaml.dump(session['preloaded']), '_data')
    return render_template('uploadsuccess.html', output=True, uploadurl=False, successmessage="success!", uploadtype="vocab")
# take uploaded content from upload form
# create manifest or upload image
@app.route('/createimage', methods=['POST', 'GET'])
def createimage():
    request_form = request.form.to_dict()
    request_form['added'] = str(datetime.now())
    request_form['user'] = session['user_name']
    image = Image(request_form, request.files, session['origin_url'])
    successmessage = ''
    uploadurl = ''
    uploadtype = 'manifest'
    actionname = ''
    if not image.isimage:
        if type(image.manifest) == dict:
            return render_template('upload.html', error=image.manifest['error'], tabs=get_tabs('upload'))
        response = github.sendgithubrequest(session, "manifest.json", image.manifest_markdown, image.manifestpath).json()
        if 'content' in response.keys():
            uploadurl ='{}{}'.format(image.origin_url, response['content']['path'].replace('_manifest', 'manifest'))
            successmessage = successtext(uploadurl, uploadtype, actionname)
            output = True
        else:
            output = response['message']
    else:
        filenames = []
        for afile in image.files:
            imagespath = "images"
            response = github.sendgithubrequest(session, afile['filename'], afile['encodedimage'], imagespath).json()
            if 'content' in response.keys():
                actionname = 'convert_images_{}'.format(image.folder)
                uploadurl = "{}img/derivatives/iiif/{}/manifest.json".format(image.origin_url, image.folder)
                successmessage = successtext(uploadurl, uploadtype, actionname)
                filenames.append((os.path.join(imagespath, afile['filename']), afile['label']))
                output =  True
            else:
                output = response['message']
        convertiiif = image.createActionScript(githubfilefolder, filenames)
        ymlname = '{}.yml'.format(actionname)
        response = github.sendgithubrequest(session, ymlname, convertiiif, ".github/workflows").json()
        triggerAction(ymlname)
    #triggerbuild()
    if 'returnjson' in request.form.keys():
        manifestdict = {'added': request_form['added'], 'json': image.manifest, 
        'output': output, 'url': uploadurl, 'iiif': True, 'upload': True, 
        'title': image.title, 'thumbnail': image.thumbnail, 'user': request_form['user']}
        session['upload']['manifests'].insert(0, manifestdict)
        return jsonify(manifestdict), 200
    else:
        return render_template('uploadsuccess.html', output=output, actionname=actionname, uploadurl=uploadurl, successmessage=successmessage, uploadtype=uploadtype)

def successtext(uploadurl, uploadtype, actionname=''):
    if uploadurl:
        uploaddict = {'url': uploadurl, 'uploadtype': uploadtype, 'actionname': actionname }
        if 'inprocess' in session.keys() and uploaddict not in session['inprocess']:
            session['inprocess'].append(uploaddict)
        else:
            session['inprocess'] = [uploaddict]
    return '<a href="{}">{}</a> is now avaliable.</p><p><a href="/?{}url={}">Start annotating your {}!</a></p>'.format(uploadurl, uploadurl, uploadtype, uploadurl, uploadtype)
# upload wax formatted csv. Get headers from CSV. Update config.yml with wax fields
# create GitHub action for collection and run it.
@app.route('/processwaxcollection', methods=['POST', 'GET'])
def processwaxcollection():
    collectionname = request.form['waxcollection']
    imagesurl = session['currentworkspace']['contents_url'].replace('/{+path}', '/_data/raw_images/{}'.format(collectionname))
    checkcontents = github.raw_request('get', imagesurl)
    if checkcontents.status_code > 299:
        blob_url = session['currentworkspace']['html_url'] + '/tree/' + session['currentworkspace']['default_branch'] + '/_data/raw_images'
        return render_template('upload.html', tab="collection", tabs=get_tabs('upload') ,error='A folder named <b>{}</b> does not exist in <a href="{}" target="_blank">{}</a>. Please upload collection images to the correct folder.'.format(collectionname, blob_url, blob_url))
    csvfile = request.files['collectioncsv'].stream.read()
    github.sendgithubrequest(session, '{}.csv'.format(collectionname), csvfile, '_data')
    reader = csv.DictReader(csvfile.decode().splitlines())
    if 'pid' not in reader.fieldnames or 'label' not in reader.fieldnames:
        missingfield = 'pid' if 'pid' not in reader.fieldnames else 'label'
        return render_template('upload.html', tab="collection", tabs=get_tabs('upload'), error='<b>{}</b> column missing from your spreadsheet. This is a required field!'.format(missingfield))
    actions = github.get('{}/actions/workflows'.format(session['currentworkspace']['url']))
    hasaction = list(filter(lambda action: action['name'] == collectionname, actions['workflows']))
    uploadurl = ''
    successtexts = ''
    layout = ''
    output = True
    actionname = 'process_collection_{}'.format(collectionname)
    for row in reader:
        url = session['origin_url'].strip("/") + '/img/derivatives/iiif/' + row['pid'] + '/manifest.json'
        successtexts += successtext(url, 'manifest', actionname)
        uploadurl = url
    if len(hasaction) > 0:
        triggerAction(hasaction[0]['id'])
    else:
        ignorefields = ['pid', 'full', 'thumbnail', 'layout', 'order', 'collection']
        updateconfig(collectionname, list(filter(lambda x: x not in ignorefields, reader.fieldnames)))
        yamlcontents = open(os.path.join(githubfilefolder, 'action.yml')).read()
        yamlcontents = yamlcontents.replace('replacewithcollection', collectionname)
        yamlcontents = yamlcontents.replace('replacewithbranch', session['currentworkspace']['default_branch'])
        response = github.sendgithubrequest(session, '.github/workflows/{}.yml'.format(collectionname), yamlcontents)
        if response.status_code < 299:
            triggerAction(response.json()['content']['name'])
        else:
            output = response.json()
    return render_template('uploadsuccess.html', output=output, actionname=actionname, uploadurl=uploadurl, successmessage=successtexts, uploadtype='collection')

# Trigger a GitHub action to run
def triggerAction(ident):
    currrentworkspace = session['currentworkspace']
    time.sleep(2)
    response = github.raw_request('post', '{}/actions/workflows/{}/dispatches'.format(currrentworkspace['url'], ident), headers={'Accept': 'application/vnd.github.v3+json'}, data=json.dumps({"ref":currrentworkspace['default_branch']}))
    print(response.content)
    if 'Not Found' in str(response.content):
        triggerAction(ident)

@app.route('/defaultworkspace', methods=['POST'])
def defaultworkspace():
    for workspace, workitems in session['workspaces'].items():
        if 'default-workspace' in workitems['topics']:
            updateTopics(workspace, True)
    error = updateTopics(request.form['workspace'])
    url = '/profile?error={}'.format(error) if error else '/profile'
    return redirect(url)

def updateTopics(workspacename, remove=False):
    workspace = session['workspaces'][workspacename]
    topics = workspace['topics']
    if remove:
        topics.remove('default-workspace')
    else:
        topics.append('default-workspace')
    response = github.raw_request('put', '{}/topics'.format(workspace['url']), headers={'Accept': 'application/vnd.github.v3+json'}, data=json.dumps({"names":topics}))
    if response.status_code < 299:
        session['workspaces'][workspacename]['topics'] = topics
        return False
    else:
        return response.content

# create collections form if GET.
# If POST, grab all data from form and create collection JSON
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
        github.sendgithubrequest(session, '{}.json'.format(title), contents, session['defaults']['collections'])
        return redirect('/collections')
    else:
        formvalues = CollectionForm(collectionid, request.args, session['collections']).formvalues
        return render_template('createcollection.html', formvalues=formvalues)

# Display created collections, either all collections or a single collection if there is a collection id.
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

@app.route('/update')
def updateindex():
    arraydata = getContents()
    return arraydata['contents'], 200


# Homepage if logged in. Get contents of API and load into homepage.
@app.route('/')
def index():
    if 'user_id' in session:
        try:
            arraydata = getContents()
            manifests = session['upload']['manifests'] + session['preloaded']['images']
            manifests = sorted(manifests, key=lambda d: datetime.strptime(d['added'].replace('&#58;', ':').replace(" +", "."), '%Y-%m-%d %H:%M:%S.%f') if type(d) == dict and 'added' in d.keys() and d['added'] else datetime.now() - timedelta(days=1), reverse=True)
            existing = {'images': manifests, 'settings': session['preloaded']['settings']}
            if 'vocab' in session['preloaded'].keys():
                labelonlyvocab = [item['label'] if type(item) == dict else item for item in session['preloaded']['vocab']]
            vocabtags = arraydata['tags'] if 'vocab' not in session['preloaded'].keys() else session['preloaded']['vocab'] + list(filter(lambda tag: tag not in labelonlyvocab, arraydata['tags']))
            userid =  session['user_id'] if 'tempuser' not in session.keys() else session['user_name']
            return render_template('index.html', existingitems=existing, filepaths=arraydata['contents'], tags=vocabtags, userinfo={'name': session['user_name'], 'id': userid, 'permissions': session['permissions']})
        except Exception as e:
           return errorchecking(request, e)

# If it is first build, render the first build page. If there are no workspaces present, render error template.
# Otherwise trigger build and render error page.
def errorchecking(request, error=False):
    firstbuild = request.args.get('firstbuild')
    if firstbuild == 'True':
        return render_template('firstbuild.html')
    elif firstbuild == 'noworkspaces':
        return render_template('error.html', message='There was a problem enabling GitHub pages on your site. Please follow the <a href="https://annonatate.github.io/annonatate-help/getting-started#troubleshooting">troubleshooting instructions to fix this problem.</a>')
    elif error:
        return render_template('error.html', message=error)
    else:
        triggerbuild()
        return render_template('error.html', message='''<b>If this
        is your first time logging into your website, is still being built
        and that is why you are seeing this error page.
        Please wait a minute and try refreshing the page.<b>
        <p>There is a problem with your website: <a href='{}'>{}</a></p>
        <p>Please refresh the page. If it is not working after a minute
        please delete or rename your repository
        <a href='{}/settings'>{}/settings</a> and refresh the page.</p>'''.format(session['origin_url'], session['origin_url'], session['currentworkspace']['html_url'], session['currentworkspace']['html_url']))

# Switch workspace. If there is problem updating the workspace,
#switch to the previous workspace and show error
@app.route('/changeworkspace', methods=['POST'])
def changeworkspace():
    workspace = request.form['workspace']
    next_url = request.args.get('next') or url_for('index')
    prevworkspace = session['currentworkspace']['full_name']
    updateworkspace(workspace)
    content, status_code = origin_contents()
    getContents()
    if status_code > 299:
        if session['defaults']['iswax']:
            try:
                github.get(session['currentworkspace']['contents_url'].replace('/{+path}', session['defaults']['apiurl']))
            except:
                updateWax()
        triggerbuild()
    return redirect(next_url)

# update config in wax site and update config
def updateWax():
    updateconfig()
    updateindex()

# Get decoded contents of _config.yml.
# If collection, update config with WAX collections. Otherwise update urls for annotations and baseurl
def updateconfig(collection='', searchfields=''):
    configfilenames = '_config.yml'
    config = github.get(session['currentworkspace']['contents_url'].replace('/{+path}', configfilenames))
    decodedcontents = github.decodeContent(config['content'])
    contentsyaml = yaml.load(decodedcontents, Loader=yaml.FullLoader)
    if collection:
        contentsyaml['collections'][collection] = {'output': True,
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
    github.sendgithubrequest(session, configfilenames, updatedcontents)

# clear everything that is not workspaces or user info
# update currentworkspace, get defaults and populate the workspace
def updateworkspace(workspace):
    clearSessionWorkspaces()
    session['currentworkspace'] = session['workspaces'][workspace]
    session['defaults'] = getDefaults()
    populateworkspace()

# Create annotations via Annotorious
@app.route('/create_annotations/', methods=['POST'])
def create_anno():
    response = json.loads(request.data)
    canvas = response['canvas']
    data_object = response['json']
    idfield = '@id' if isMirador(session) else 'id'
    data_object[idfield] = data_object[idfield].replace("#", "") + '.json'
    cleanobject = cleananno(data_object)
    listlength = len(list(filter(lambda n: canvas == n.get('canvas'), session['annotations'])))
    response = writetogithub(data_object[idfield], cleanobject, listlength+1)
    returnvalue = response.content if response.status_code > 399 else data_object
    returnvalue['order'] = listlength+1
    return jsonify(returnvalue), response.status_code

# Update annotations via Annotorious
@app.route('/update_annotations/', methods=['POST'])
def update_anno():
    response = json.loads(request.data)
    data_object = response['json']
    order = data_object['order']
    cleanobject = cleananno(data_object)
    idfield = '@id' if isMirador(session) else 'id'
    response = writetogithub(data_object[idfield], cleanobject, response['order'])
    returnvalue = response.content if response.status_code > 399 else data_object
    returnvalue['order'] = order
    return jsonify(returnvalue), response.status_code

# Delete annotations via Annotorious
@app.route('/delete_annotations/', methods=['DELETE', 'POST'])
def delete_anno():
    response = json.loads(request.data)
    id = response['id']
    annotatons = getannotations()
    canvas = response['canvas']
    canvases = getContents()['contents']
    response = delete_annos(id)
    if len(canvases[canvas]) == 1:
        delete_annos(listfilename(canvas))
    message = response['message'] if type(response['message']) == str else response['message'].decode("utf-8")
    return jsonify(message), response['status_code']

# Get repository invites, collaborators, user info/organizations, render profile page
@app.route('/profile/')
def getprofiledata():
    sent_invites = []
    tabs = get_tabs('profile')
    invites = github.get('{}/repository_invitations'.format(githubuserapi))
    if session['isadmin']:
        sent_invites = github.get('{}/invitations'.format(session['currentworkspace']['url']))
    collaburl = session['currentworkspace']['collaborators_url'].split('{')[0]
    try:
        collaborators = github.get(collaburl)
    except:
        collaborators = []
    populateuserinfo()
    orgs()
    return render_template('profile.html', userinfo={'name':session['user_name']}, invites=invites, sent_invites=sent_invites, collaborators=collaborators, tabs=tabs, revoke_url='https://github.com/settings/connections/applications/{}'.format(client_id))

# get list of orgs user belongs to
def orgs():
    if 'orgs' not in session.keys():
        allorgs = [session['user_id']]
        orgs = github.get('{}/orgs'.format(githubuserapi))
        allorgs += list(map(lambda x: x['login'], orgs))
        session['orgs'] = allorgs

# Used via delete button, delete files from GitHub
@app.route('/deletefile/', methods=['POST'])
def deletefile():
    try:
        content = json.loads(request.form.get('file'))
        url = content['url'] if type(content) == dict else content
    except:
        url = request.form.get('file')
        content = url
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
    elif 'img/derivatives/iiif' in path:
        deletescript = open(os.path.join(githubfilefolder, 'deleteimage.yml')).read()
        deletescript = deletescript.replace("replacewithimagepath", path)
        github.sendgithubrequest(session, 'deleteimage.yml', deletescript, ".github/workflows").json()
        triggerAction('deleteimage.yml')
        session['upload']['manifests'].remove(content)
    else:
        uploadtype = path.split('/')[0]
        try:
            session['upload'][uploadtype].remove(content)
        except:
            if 'inprocess' in session.keys() and len(session['inprocess']) == 0:
                if url not in list(map(lambda x: x['url'], session['inprocess'])):
                    return 'error', 400
    payload = {'ref': session['github_branch']}
    data = github.createdatadict(session, filename, 'delete', path)
    response = github.raw_request('delete', data['url'], data=json.dumps(data['data']), params=payload)
    if 'returnjson' in request.form.keys():
        return response.content, response.status_code
    else:
        return redirect(request.args.get('next'))


def getActions():
    params = {'created': '>={}'.format(datetime.now().date())}
    runs = github.get('{}/actions/runs'.format(session['currentworkspace']['url']), params)
    session['actions'] = runs['workflow_runs']

# Route for accepting invitations to repositories
@app.route('/invite/<string:type>', methods=['POST'])
def invites(type):
    inviteurl = request.form['inviteurl']
    requesttype = 'patch' if type == 'accept' else 'delete'
    response = github.raw_request(requesttype, inviteurl)
    populateuserinfo()
    return redirect('/profile')

# search all annotations in session
@app.route('/search')
def search():
    search = Search(request.args, session['annotations'])
    if request.args.get('format') == 'json':
        return jsonify(search.items), 200
    else:
        annolength = len(list(filter(lambda x: '-list' not in x['filename'], session['annotations'])))
        return render_template('search.html', results=search.items, facets=search.facets, query=search.query, annolength=annolength)

# Get list of annotations, if annoid, show only that annotation.
@app.route('/annotations/', methods=['GET'])
@app.route('/annotations/<annoid>', methods=['GET'])
def listannotations(annoid=''):
    items = getannotations()
    if annoid:
        lists = list(filter(lambda x: annoid in x['filename'], items))
    else:
        lists = list(filter(lambda x: '-list' not in x['filename'], items)) if request.args.get('annotype') == 'single' else list(filter(lambda x: '-list' in x['filename'], items))
    format = request.args.get('viewtype') if request.args.get('viewtype') else 'annotation'
    return render_template('annotations.html', annotations=lists, format=format, filepath=session['defaults']['annotations'], annoid=annoid)

# render template for customviews
@app.route('/customviews')
def customviews():
    return render_template('customviews.html')

# Tag builder page
@app.route('/annonaview')
def annonaview():
    return render_template('annonabuilder.html')

# Create cutstom view with tags, if wax add exhibit front matter
@app.route('/saveannonaview', methods=['POST'])
def saveannonaview():
    jsonitems = json.loads(request.data)
    frontmatter = 'tagurl: {}\n'.format(jsonitems['url'])
    tag = jsonitems['tag'].replace('styling=', 'styling=fullpage:true;')
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
    </html>""".format(frontmatter, tag)
    response = github.sendgithubrequest(session, '{}.html'.format(jsonitems['slug']), content, folder)
    if response.status_code < 300:
        annourl = parseboard(jsonitems['tag'])['url']
        fileurl = os.path.join(session['origin_url'], folder.strip('_'), jsonitems['slug']) + '/'
        if annourl in session['annocustomviews'] and annourl not in session['annocustomviews'][annourl]:
            if fileurl not in session['annocustomviews'][annourl]:
                session['annocustomviews'][annourl].append({'slug': jsonitems['slug'], 'filename': fileurl})
        elif annourl:
            session['annocustomviews'][annourl] = [{'slug': jsonitems['slug'], 'filename': fileurl}]
    return jsonify(response.content), response.status_code

# Update preloaded manifests and images
@app.route('/updatedata', methods=['POST'])
def updatedata():
    jsonreturn = False
    if request.form and 'updatedata' in request.form.keys():
        data = request.form['updatedata']
        jsondata = json.loads(data)
    elif request.form and 'addurl' in request.form.keys():
        newurl = request.form['addurl']
        session['preloaded']['images'].insert(0, newurl)
        jsondata = session['preloaded']
        jsonreturn = True
    elif request.form and 'removeurl' in request.form.keys():
        session['preloaded']['images'].remove(json.loads(request.form['removeurl']))
        jsondata = session['preloaded']
        jsonreturn = True
    else:
        jsondata = session['preloaded']
    jsondata['settings'] = getSettings(jsondata['settings'])
    for key in jsondata:
        if key != 'settings' and jsondata[key] == {}:
            jsondata[key] = []
    jsondata['images'] = checkManUrls(jsondata['images'])
    if request.form and 'addurl' in request.form.keys():
        jsondata['images'][0]['added'] = str(datetime.now())
        jsondata['images'][0]['user'] = session['user_name']
    yamldata = yaml.dump(jsondata)
    github.sendgithubrequest(session, 'preload.yml', yamldata, '_data')
    session['preloaded'] = jsondata
    checkTempUser(jsondata)
    if jsonreturn:
        return jsonify(jsondata), 200
    else:
        return redirect('/profile?tab=data')

def checkManUrls(data):
    returndata = []
    for man in data:
        if type(man) == str and man != '' and man != None:
            imagetypes = ['jpg', 'jpeg', 'png', 'gif', 'tif', 'tiff']
            if man.rsplit('.', 1)[-1] not in imagetypes:
                r = requests.get(man)
                if 'image' not in r.headers['Content-Type']:
                    thumbnail, title = getThumbnailTitle(r.content)
                    if '/info.json' in man:
                        thumbnail = man.replace('/info.json', '/full/120,/0/default.jpg')
                    returndata.append({'url': man, 'thumbnail': thumbnail, 'title': title, 'iiif': True})
                else:
                    mandict = {'url': man, 'iiif': False, 'title': '', 'thumbnail': man}
                    returndata.append(mandict)
            else:
                mandict = {'url': man, 'iiif': False, 'title': '', 'thumbnail': man}
                returndata.append(mandict)
        elif man != '' and man != None:
            returndata.append(man)
    return returndata


def checkTempUser(data):
    if 'tempuser' not in session.keys() and 'tempuser' in data['settings'].keys() and data['settings']['tempuser'] == 'enabled':
        session['tempuser'] = True
    elif 'tempuser' in session.keys() and data['settings']['tempuser'] == 'notenabled':
        del session['tempuser']

# Shows GitHub libray how to get token
@github.access_token_getter
def token_getter():
    if 'user_token' in session.keys():
        return session['user_token']

# Build workspaces
def buildWorkspaces():
    isfirstbuild = populateuserinfo()
    if isfirstbuild != 'noworkspaces':
        if 'currentworkspace' not in session.keys() or not session['currentworkspace']:
            session['currentworkspace'] = session['workspaces'][list(session['workspaces'].keys())[0]]
            session['defaults'] = getDefaults()
        populateworkspace()
    return isfirstbuild

def checkBuildStatus():
    params = {'created': '>={}'.format(datetime.now().date())}
    runs = github.get('{}/actions/runs'.format(session['currentworkspace']['url'], params))
    statuses = ['in_progress', 'queued', 'waiting']
    isbuilding = list(filter(lambda x: 'pages-build' in x['path'] and x['status'] in statuses and x['conclusion'] == None,runs['workflow_runs']))
    return isbuilding

# trigger build of GitHub pages website
def triggerbuild(url=False):
    isbuilding = checkBuildStatus()
    if len(isbuilding) == 0:
        pagebuild = url if url else session['currentworkspace']['url'] + '/pages'
        return github.raw_request("post", '{}/builds'.format(pagebuild), headers={'Accept': 'application/vnd.github.mister-fantastic-preview+json'})

# Get user info from GitHub user api, get all repos user has access to.
# If no workspaces, fork Annnonatate repo, enable pages
def populateuserinfo():
    workspaces = {}
    userinfo = github.get(githubuserapi)
    firstbuild = False
    session['user_id'] = userinfo['login']
    session['avatar_url'] = userinfo['avatar_url']
    username = userinfo['name'] if userinfo['name'] != None else userinfo['login']
    session['user_name'] = username if 'tempuser' not in session.keys() else session['tempuser']
    repos = github.get('{}/repos?per_page=300&sort=name'.format(githubuserapi))
    if len(repos) == 100:
        page = 2
        repos2 = repos
        while len(repos2) == 100:
            repos2 = github.get('{}/repos?per_page=100&sort=name&page={}'.format(githubuserapi,page))
            repos = repos + repos2
            page += 1
    relevantworkspaces = []
    for repo in repos:
        repotypes = ["wax", github_repo]
        repotypes = repotypes + list(map(lambda x: "{}-{}".format(github_repo, x), repotypes))
        if repo['name'] == github_repo or any(x in repo['topics'] for x in repotypes):
            relevantworkspaces.append(repo)
        elif repo['description'] and 'annonatate' in repo['description'].lower():
            relevantworkspaces.append(repo)
        if 'default-workspace' in repo['topics'] and 'currentworkspace' not in session.keys():
            session['currentworkspace'] = repo
    for workspace in relevantworkspaces:
        workspaces[workspace['full_name']] = workspace
    if len(workspaces) == 0:
        response = github.post('https://api.github.com/repos/annonatate/{}/forks'.format(github_repo))
        time.sleep(2)
        enablepages = enablepagesfunc(response['url'])
        if enablepages.status_code > 299:
            enablepages = enablepagesfunc(response['url'])
        if enablepages.status_code > 299:
            firstbuild = 'noworkspaces'
            workspaces[response['full_name']] = response
        else:
            updates = {'homepage': enablepages.json()['html_url'], 'topics': 'annonatate'}
            updatehomepage = github.raw_request('patch', response['url'], data=json.dumps(updates))
            workspaces[response['full_name']] = response
            firstbuild = True
    session['workspaces'] = workspaces
    return firstbuild

# Function to enable GitHub pages on Repo
def enablepagesfunc(pagesurl):
    branches = {'source': {'branch': github_branch,'path': '/'}}
    enablepages = github.raw_request('post', '{}/pages'.format(pagesurl), data=json.dumps(branches), headers={'Accept': 'application/vnd.github.switcheroo-preview+json'})
    return enablepages

# Create a new workspace, by using Annonatate's template.
@app.route('/add_repos', methods=['POST'])
def add_repos():
    owner = request.form['owner']
    name = request.form['name']
    ismirador = True if 'mirador' in request.form else False
    private = True if 'private' in request.form else False
    iswax = True if 'wax' in request.form else False
    forkrepo = github_repo + '-wax' if iswax else github_repo
    repodata = {
        'owner': owner,
        'name': name,
        'private': private,
        'description': forkrepo
    }
    response = github.raw_request('post', 'https://api.github.com/repos/annonatate/{}/generate'.format(forkrepo),headers={'Accept': 'application/vnd.github.baptiste-preview+json'}, data=json.dumps(repodata)).json()
    if 'url' in response.keys():
        time.sleep(2)
        enablepages = enablepagesfunc(response['url'])
        if enablepages.status_code > 299:
            error = 'Problem enabling GitHub pages. Do it manually or delete this repository.'
            return redirect('/profile?tab=workspaces&error={}'.format(error))
        else:
            updates = {'homepage': enablepages.json()['html_url'], 'topics': ['annonatate']}
            updatehomepage = github.raw_request('patch', response['url'], data=json.dumps(updates))
        if ismirador:
            updatepreload = github.sendgithubrequest({'github_url': response['contents_url'].replace('/{+path}', ''), 'github_branch': 'main'}, 'preload.yml', open(os.path.join(githubfilefolder, "miradordata.yml")).read(), '_data')
    else:
        error = parseGitHubErrors(response.json())
        return redirect('/profile?tab=workspaces&error={}'.format(error))
    return redirect('/profile?tab=profile')

@app.route('/updatetempuser', methods=['POST'])
def updatetempuser():
    tempusername = request.form['tempusername']
    session['user_name'] = tempusername
    session['tempuser'] = tempusername
    return redirect(request.args.get('next'))

# Get error message if there is one in GitHub's API response
def parseGitHubErrors(response):
    firsterror = response['errors'][0] if 'errors' in response.keys() else response
    error = firsterror['message'] if 'message' in firsterror else firsterror
    return error

# clear everythig that is not users or workspaces from session
def clearSessionWorkspaces(): 
    for key in list(session.keys()):
        if 'user_' not in key and 'workspaces' not in key:
            del session[key]

#  clear everything but user from the session
def clearSession(dontdelete=False):
    if dontdelete: 
        for key in list(session.keys()):
            if dontdelete not in key:
                del session[key]
    else:
        session.clear()

# Get pages API contents
def populateworkspace():
    session['github_url'] = session['currentworkspace']['contents_url'].replace('/{+path}', '')
    session['github_branch'] = session['currentworkspace']['default_branch']
    try:
        pagesinfo = github.get('{}/pages'.format(session['currentworkspace']['url']))
        session['origin_url'] = pagesinfo['html_url']
        parse_permissions()
    except:
        return render_template('error.html', message="<p>There is a problem with your GitHub pages site. Try <a href='https://docs.github.com/en/github/working-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site'>enabling the website</a> or deleting/renaming the repository <a href='{}/settings'>{}/settings</a></p>".format(session['currentworkspace']['html_url'], session['currentworkspace']['html_url']))

# get all contents from Jekyll API, load contents into search
def getContents():
    arraydata = {}
    canvases = getannotations()
    tags = []
    for canvas in canvases:
        loadcanvas = canvas['json']
        if 'resources' not in loadcanvas.keys() and 'items' not in loadcanvas.keys():
            searchfields = get_search(loadcanvas)
            tags += searchfields['facets']['tags']
            loadcanvas['order'] = canvas['order']
        if canvas['canvas'] in arraydata.keys():
            arraydata[canvas['canvas']].append(loadcanvas)
        else:
            arraydata[canvas['canvas']] = [loadcanvas]
    return {'contents': arraydata, 'tags': tags}

# Get annotation content
def getannotations():
    buildstatus = checkBuildStatus()
    if 'annotations' not in session.keys() or len(buildstatus) == 0:
        content, status = origin_contents()
        for item in content['annotations']:
            item['canvas'] = getCanvas(item['json'])
        session['annotations'] = content['annotations']
        if 'preloadedcontent' in content.keys() and content['preloadedcontent'] == None:
            content['preloadedcontent'] = {'images': [], 'settings': getSettings(None)}
        if 'preloadedcontent' not in content.keys():
            updateindex()
            content['preloadedcontent'] = {'manifests': content['manifests'], 'images': content['images'], 'settings': {}}
            session['upload'] = {'manifests': [], 'images' : []}
        parsecollections(content)
        session['preloaded'] = {'images': [], 'settings': getSettings(None)}
        for preloadkey in content['preloadedcontent']:
            if content['preloadedcontent'][preloadkey]:
                if preloadkey != 'settings':
                    session['preloaded'][preloadkey] = content['preloadedcontent'][preloadkey]
                else:
                    session['preloaded'][preloadkey] = getSettings(content['preloadedcontent'][preloadkey])
        if 'version' not in content['preloadedcontent'].keys() or content['preloadedcontent']['version'] != currentversion:
            updateindex()
            if content['preloadedcontent']['manifests']:
                session['preloaded']['images'] += content['preloadedcontent']['manifests']
            session['preloaded']['version'] = currentversion
            updatedata()
        checkTempUser(session['preloaded'])
        session['upload'] = {'images': content['images'], 'manifests': content['manifests']}
        parsecustomviews(content)
        annotations = github.updateAnnos(session)
        if status > 299:
            session['annotations'] = []
        else:
            session['annotations'] = annotations
    else:
        annotations = github.updateAnnos(session)
        session['annotations'] = annotations
    return annotations

def getSettings(settings):
    defaults = {'tempuser': 'notenabled', 'viewer': 'default', 'widgets': 'comment-with-purpose, tag, geotagging'}
    if settings:
        defaults = {**defaults, **settings}
    return defaults

# Load custom views JSON into a dict that sorts custom views based on the url being read
def parsecustomviews(content):
    parseddict = {}
    customdict = {}
    for customview in content['customviews']:
        annourl = parseboard(customview['json'])['url']
        if 'editurl' in customview.keys():
            customdict[customview['filename']] = customview['editurl']
        if annourl in parseddict.keys() and customview['filename'] not in parseddict[annourl]:
            parseddict[annourl].append(customview['filename'])
        else:
            parseddict[annourl] = [customview['filename']]
    session['annocustomviews'] = parseddict
    session['customviewpage'] = customdict

# grab all collection names, group collections by url in board, if collection not in api update index
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

# grab correct index file based on defaults, read and write to GitHub
def updateindex():
    index = session['defaults']['index']
    contents = open(index).read()
    github.sendgithubrequest(session, index.replace(githubfilefolder, ''), contents)

# Using origin API get contents, if not correct add index.html to request. Parse API contents.
def origin_contents():
    if 'defaults' not in session.keys():
        session['defaults'] = getDefaults()
    apiurl = session['origin_url'] + session['defaults']['apiurl']
    response = requests.get(apiurl)
    if response.status_code > 299:
        response = requests.get(apiurl + 'index.html')
    try:
        content = json.loads(response.content.decode('utf-8').replace('&lt;', '<').replace('&gt;', '>'))
    except Exception as e:
        print(e)
        content = {'annotations': [], 'images': [], 'manifests': [], 'customviews': [], 'collections': []}
        triggerbuild()
        try:
            preloads = github.raw_request('get', session['currentworkspace']['contents_url'].replace('/{+path}', '_data/preload.yml'))
            if preloads.status_code < 299:
                yamlcontents = github.decodeContent(preloads.json()['content'])
                content['preloadedcontent'] = yaml.load(yamlcontents, Loader=yaml.FullLoader)
            else:
                content['preloadedcontent'] =  {'images': [], 'manifests': [], 'settings': {'tempuser': 'notenabled', 'viewer': 'default', 'widgets': 'comment-with-purpose, tag, geotagging'}}
        except Exception as e:
            print(e)
    return content, response.status_code

# remove escaped tags
def cleananno(data_object):
    if 'order' in data_object.keys():
        del data_object['order']
    field = 'resource' if 'resource' in data_object.keys() else 'body'
    charfield = 'chars' if 'resource' in data_object.keys() else 'value'
    if isMirador(session) and 'on' in data_object.keys() and 'selector' in data_object['on'][0].keys() and 'item' in data_object['on'][0]['selector'].keys():
        svgselector = data_object['on'][0]['selector']['item']['value']
        searchstring = re.findall(r'(?<=(data-paper-data="{))(.*?)(?=(\}"))', svgselector)
        if len(searchstring) > 0:
            searchstring = "".join(searchstring[0])
            data_object['on'][0]['selector']['item']['value'] = svgselector.replace(searchstring, '')
    if field in data_object.keys():
        for item in data_object[field]:
            if charfield in item.keys():
                replace = re.finditer(r'&lt;iiif-(.*?)&gt;&lt;\/iiif-(.*?)&gt;', item[charfield])
                for rep in replace:
                    replacestring = rep.group().replace("&lt;","<").replace("&gt;", ">").replace("&quot;", '"')
                    item[charfield] =  item[charfield].replace(rep.group(), replacestring)
    return data_object

# function to delete annotations from session and GitHub
def delete_annos(anno):
    data = github.createdatadict(session, anno, 'delete', session['defaults']['annotations'])
    if 'sha' in data['data'].keys():
        payload = {'ref': session['github_branch']}
        response = github.raw_request('delete', data['url'], data=json.dumps(data['data']), params=payload)
        if response.status_code < 400:
            session['annotations'] = [x for x in session['annotations'] if anno not in x['filename']]
        return {'message': response.content, 'status_code': response.status_code}
    else:
        return {'message': 'no annotation exists', 'status_code': 400}

def get_tabs(viewtype):
    if viewtype == 'upload':
        tabs = [
            { 'value': 'image', 'label': 'Upload Image'},
            { 'value': 'manifest', 'label': 'Copy Manifest'},
            { 'value': 'vocab', 'label': 'Upload Vocabulary'}]
        if session['defaults']['iswax']:
            tabs.append({ 'value': 'collection', 'label': 'Process Wax Collection'})
    elif viewtype == 'profile':
        tabs = [{ 'value': 'profile', 'label': 'Workspaces'},
            { 'value': 'workspaces', 'label': 'Edit Workspaces'},
            { 'value': 'uploads', 'label': 'Uploaded content'}]
        if session['permissions'] != 'read':
            tabs.insert(2,{ 'value': 'data', 'label': 'Settings'})
        if 'inprocess' in session.keys() and len(session['inprocess']) > 0:
            tabs.insert(0, {'value': 'status', 'label': 'Upload Status'})
    return tabs

def to_pretty_json(value):
    return json.dumps(value, sort_keys=True,
                      indent=4, separators=(',', ': '))

def search_params(facet, value):
    args = dict(request.args) if request.args else {'q': ''}
    args[facet] =value
    return args

def parse_permissions(permissiondict=None):
    permissioninfo = permissiondict['permissions'] if permissiondict else session['currentworkspace']['permissions']
    permissions = 'read'
    if permissioninfo['admin']:
        permissions = 'admin'
    elif permissioninfo['maintain']:
        permissions = 'maintain'
    elif permissioninfo['push']:
        permissions = 'write'
    if permissiondict is None:
        session['isadmin'] = permissions == 'admin'
        session['permissions'] = permissions
    return permissions


def getNav(session):
    nav = [{'url': url_for('index'), 'label': 'Home'},
    {'url': url_for('listannotations'), 'label': 'Annotations'},
    {'url': url_for('search'), 'label': 'Search'},
    {'url': url_for('customviews'), 'label': 'Custom views'},
    {'url': url_for('collections'), 'label': 'Collections'}
    ] 
    if session['permissions'] != 'read':
        nav.insert(3, {'url': url_for('upload'), 'label': 'Upload'})
    return nav

app.jinja_env.filters['getNav'] = getNav 
app.jinja_env.filters['parse_permissions'] = parse_permissions  

app.jinja_env.filters['search_params'] = search_params

app.jinja_env.filters['tojson_pretty'] = to_pretty_json

app.jinja_env.filters['canvas'] = getCanvas
app.jinja_env.filters['manifest'] = getManifest
app.jinja_env.filters['isMirador'] = isMirador

# Function for writing annotations to GitHub.
# If successfully written to GitHub, update session annotations
# If annotation list doesn't exist, create an annotation list
def writetogithub(filename, annotation, order):
    githuborder = 'order: {}\n'.format(order)
    folder = session['defaults']['annotations']
    response = github.sendgithubrequest(session, filename, annotation, folder, githuborder)
    if response.status_code < 400:
        canvas = getCanvas(annotation)
        manifest = getManifest(annotation)
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
            itemskey = 'items' if 'items' in session['annotations'][annolistindex]['json'].keys() else 'resources'
            session['annotations'][annolistindex]['json'][itemskey] = list(map(lambda k: k.get('json'), canvasannos))
        else:
            listdata = {'json': {'items': [data['json']]}, 'filename':annolistfilename, 'canvas': ''}
            session['annotations'].append(listdata)
        if canvas not in canvases:
            createlistpage(canvas, manifest)
    return response

# create Annotation page file, filename based on canvas, and write to GitHub
# If the manifest for the annotation is an uploaded manifest, write the annotation page to the manifest
# If the manifest is not the same as the content requested, write to GitHub
def createlistpage(canvas, manifest):
    filenameforlist = listfilename(canvas)
    filename = os.path.join(session['defaults']['annotations'], filenameforlist)
    context, annotype, itemskey = contextType(session)
    text = '---\ncanvas_id: "' + canvas + '"\n---\n{% assign annotations = site.annotations | where: "canvas", page.canvas_id | sort: "order" | map: "content" %}\n{\n"@context": "' + context + '",\n"id": "{{ site.url }}{{ site.baseurl }}{{page.url}}",\n"type": "' + annotype + '",\n"%s": [{{ annotations | join: ","}}] }'%(itemskey)
    github.sendgithubrequest(session, filename, text)
    if manifest in session['upload']['manifests']:
        response = requests.get(manifest).json()
        manifestwithlist = addAnnotationList(json.dumps(response), session)
        manifestfilename = manifest.replace(session['origin_url'], '')
        if json.loads(manifestwithlist) != response:
            manifestwithlist = '---\nlayout: none\n---\n' + manifestwithlist.replace(session['origin_url'], "{{ '/' | absolute_url }}")
            response = github.sendgithubrequest(session, manifestfilename, manifestwithlist)
            print(response.content)

app.jinja_env.filters['listfilename'] = listfilename

# Check to see if the user has access to the current workspace, check by querying the collaborator url
def workspaceCheck(method=False):
    if session['currentworkspace']['full_name'] not in session['workspaces'].keys():
        prevsession = session['currentworkspace']
        clearSession('user_')
        buildWorkspaces()
        getContents()
        g.error = '<i class="fas fa-exclamation-triangle"></i> You have lost access to {}, we have updated your workspace to {}'.format(prevsession['full_name'], session['currentworkspace']['full_name'])
    else:
        collaburl = session['currentworkspace']['collaborators_url'].split('{')[0]
        response = github.raw_request('get', collaburl)
        if response.status_code > 299 and response.status_code != 403:
            prevsession = session['currentworkspace']
            if 'bad credentials' in response.json()['message'].lower():
                clearSession()
                return redirect('/login')
            elif method == 'POST':
                return 'problem'
            else:
                clearSession('user_')
            buildWorkspaces()
            getContents()
            g.error = '<i class="fas fa-exclamation-triangle"></i> You have lost access to {}, we have updated your workspace to {}'.format(prevsession['full_name'], session['currentworkspace']['full_name'])
        elif response.status_code == 403:
            session['currentworkspace']['permissions'] = {'admin': False, 'maintain': False, 'push': False, 'triage': False, 'pull': True}
        else:
            try:
                session['currentworkspace']['permissions'] = list(filter(lambda x: x['login'] == session['user_name'], response.json()))[0]['permissions']
            except Exception as e:
                print(e)
            session['currentworkspace']['numbcollabs'] = len(response.json())
    parse_permissions()
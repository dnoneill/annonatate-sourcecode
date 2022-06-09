#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, yaml
import base64
from flask_github import GitHub
from annonatate.utils.image import listfilename
from annonatate.utils.annogetters import contextType, isMirador
class GitHubAnno(GitHub):
    def get_existing(self, session, full_url):
        payload = {'ref': session['github_branch']}
        match = False
        if '/images/' in full_url:
            full_url, match = full_url.strip('/').rsplit('/', 1)
        existing = self.raw_request('get',full_url, params=payload).json()
        if match and type(existing) == list:
            matches = list(filter(lambda x: x['name'] == match, existing))
            existing = matches[0] if len(matches) > 0 else matches
        if 'sha' in existing:
            return existing['sha']
        else:
            return ''

    def sendgithubrequest(self, session, filename, annotation, path='', order=''):
        data = self.createdatadict(session, filename, annotation, path, order)
        response = self.raw_request('put', data['url'], data=json.dumps(data['data'], indent=4))
        return response

    def createdatadict(self, session, filename, text, path, order=''):
        filename = os.path.basename(filename) if 'http' in filename else filename
        full_url = os.path.join(session['github_url'], path, filename)
        sha = self.get_existing(session, full_url)
        writeordelete = "write" if text != 'delete' else "delete"
        message = "{} {}".format(writeordelete, filename)
        if type(text) != str and type(text) != bytes:
            canvas = text['target']['source'] if 'target' in text.keys() else text['on'][0]['full']
            text = '---\ncanvas: "{}"\n{}---\n{}'.format(canvas ,order, json.dumps(text, indent=4))
        text = text.encode('utf-8') if type(text) != bytes else text
        data = {"message":message, "content": base64.b64encode(text).decode('utf-8'), "branch": session['github_branch'] }
        if sha != '':
            data['sha'] = sha
        return {'data':data, 'url':full_url}

    def decodeContent(self, content):
        return base64.b64decode(content).decode('utf-8')

    def updateAnnos(self, session):
        try:
            githubresponse = self.get(session['currentworkspace']['contents_url'].replace('{+path}', session['defaults']['annotations']))
            annotations = self.filterAnnos(githubresponse, session)
            return annotations
        except:
            return session['annotations']

    def filterAnnos(self, githubresponse, session):
        if githubresponse:
            githubfilenames = list(map(lambda x: x['name'], githubresponse))
            session['annotations'] = list(filter(lambda x: x['filename'].split('/')[-1] in githubfilenames, session['annotations']))
            filenames = list(map(lambda x: x['filename'].split('/')[-1], session['annotations']))
            notinsession = list(filter(lambda x: x['name'] not in filenames and '-list' not in x['name'],githubresponse))
            #beforefilenames = list(map(lambda x: x['filename'].split('/')[-1], annotations))
            #remove = list(set(beforefilenames).difference(filenames))
            for item in notinsession:
                try:
                    downloadresponse = self.get(item['download_url'])
                    contentssplit = downloadresponse.content.decode("utf-8").rsplit('---\n', 1)
                    yamlparse = yaml.load(contentssplit[0], Loader=yaml.FullLoader)
                    yamlparse['json'] = json.loads(contentssplit[-1])
                    yamlparse['filename'] = item['name']
                    filenamelist = listfilename(yamlparse['canvas'])
                    indexof = [idx for idx, annotation in enumerate(session['annotations']) if filenamelist in annotation['filename']]
                    session['annotations'].append(yamlparse)
                    if len(indexof) > 0:
                        itemskey = 'items' if 'items' in session['annotations'][indexof[0]]['json'].keys() else 'resources'
                        session['annotations'][indexof[0]]['json'][itemskey].append(yamlparse['json'])
                    else:
                        context, annotype, itemskey = contextType(session)
                        session['annotations'].append({'filename': filenamelist, 'order': None, 'json': {"@context": context,"id": filenamelist,"type": annotype,itemskey: [yamlparse['json']]}, 'canvas': ''})
                except Exception as e:
                    print(e)
        return session['annotations']
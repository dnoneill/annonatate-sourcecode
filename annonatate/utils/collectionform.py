#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re
class CollectionForm:
    def __init__(self, collectionid, request, collections):
        self.formvalues = {}
        self.args = request.args
        self.formvalues['annotations'] = []
        self.collections = collections
        self.collectionid = collectionid
        if collectionid:
            self.collectionIdValues()
        else:
            self.defaultValues()
            
    def collectionIdValues(self):
        self.formvalues['title'] = self.collectionid
        self.formvalues['add'] = False
        for item in self.collections[self.collectionid]['json']['items']:
            annodict = item
            annodict['url'] = parseboard(item['board'])['url']
            annodict['board'] = item['board'].replace('"', "'")
            annodict['viewtype'] = parsetype(item['board'])
            self.formvalues['annotations'].append(annodict)
    
    def defaultValues(self):
        self.formvalues['title'] = self.args.get('title')
        self.formvalues['add'] = True
        annodict = {'url': self.args.get('url'), 
            'title': self.args.get('annotitle'), 
            'description': self.args.get('desc'), 
            'viewtype': self.args.get('viewtype'),
            'board': self.args.get('tag'),
            'thumbnail': self.args.get('thumbnail')
        }
        if self.args.get('annotation'):
            annodict['annotation'] = json.loads(self.args.get('annotation'))
        self.formvalues['annotations'].append(annodict)

def parsetype(board):
    regex = r"<\/(iiif-.+)>"
    m = re.search(regex, board)
    return m.group(1)
    
def parseboard(board):
    regex = r"((annotationurls?|rangeurl)=['\"])(.+?)(?=['\"])"
    m = re.search(regex, board)
    if m:
        return {'url': m.group(3), 'type': m.group(2)}
    else:
        return {'url': '', 'type': ''}

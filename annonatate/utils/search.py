#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from bs4 import BeautifulSoup

class Search:
    def __init__(self, request_args, annotations):
        self.request_args = request_args
        self.annotations = annotations
        self.query = self.request_args.get('q')
        self.allcontent = self.querysearch(self.query)
        self.tags = self.request_args.get('tag')
        if self.tags:
            self.allcontent = self.searchfields(self.allcontent['items'], 'tags', self.tags)
        self.creator = self.request_args.get('creator')
        if self.creator:
            self.allcontent = self.searchfields(self.allcontent['items'], 'creator', self.creator)
        self.items = self.allcontent['items']
        self.facets = self.gatherfacets()

    def gatherfacets(self):
        facets = {}
        for key, value in self.allcontent['facets'].items():
            value = [x for x in value if x is not None]
            uniqtags = sorted(list(set(value)))
            tagcount = {x:value.count(x) for x in uniqtags}
            sortedtagcount = dict(sorted(tagcount.items(), key=(lambda x: (-x[1], x[0]))))
            facets[key] = sortedtagcount
        return facets

    def querysearch(self, fieldvalue):
        facets = {}
        items = []
        fieldvalue = fieldvalue if fieldvalue else ''
        for item in self.annotations:
            if '-list.json' not in item['filename']:
                results = get_search(item['json'])
                if fieldvalue.lower() in " ".join(list(results['searchfields'].values())).lower():
                    items.append(results)
                    facets = self.mergeDict(facets, results['facets'],)
        return {'items': list(sorted(items, key=lambda t: t['datemodified'], reverse=True)), 'facets': facets}

    def searchfields(self, content, field, fieldvalue):
        facets = {}
        items = []
        for anno in content:
            if fieldvalue in anno['facets'][field]:
                items.append(anno)
                facets = self.mergeDict(facets, anno['facets'])
        return {'items': items, 'facets': facets}


    def mergeDict(self, dict1, dict2):
        dict3 = {**dict1, **dict2}
        for key, value in dict3.items():
            if key in dict1 and key in dict2:
                dict3[key] = value + dict1[key]
        return dict3

def encodedecode(chars):
    if type(chars) == str:
        return chars
    else:
        return chars.encode('utf8')

def get_search(anno):
    annoid = anno['id'] if 'id' in anno.keys() else anno['@id']
    annodata_data = {'json': anno, 'searchfields': {'content': []}, 'facets': {'tags': [], 'creator': []}, 'datecreated':'', 'datemodified': '', 'id': annoid, 'basename': os.path.basename(annoid)}
    if 'oa:annotatedAt' in anno.keys():
        annodata_data['datecreated'] = encodedecode(anno['oa:annotatedAt'])
    if 'created' in anno.keys():
        annodata_data['datecreated'] = encodedecode(anno['created'])
    if 'oa:serializedAt' in anno.keys():
        annodata_data['datemodified'] = encodedecode(anno['oa:serializedAt'])
    if 'modified' in anno.keys():
        annodata_data['datemodified'] = encodedecode(anno['modified'])
    if 'oa:annotatedBy' in anno.keys():
        annodata_data['facets']['creator'] = anno['oa:annotatedBy']
    if 'creator' in anno.keys():
        annodata_data['facets']['creator'] = anno['creator']['name']
    textdata = anno['resource'] if 'resource' in anno.keys() else anno['body']
    textdata = textdata if type(textdata) == list else [textdata]
    for resource in textdata:
        chars = BeautifulSoup(resource['chars'], 'html.parser').get_text() if 'chars' in resource.keys() else ''
        chars = encodedecode(chars)
        typefield = 'type' if 'type' in resource.keys() else '@type'
        if chars and 'tag' in resource[typefield].lower():
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
        elif 'value' in resource.keys():
            annodata_data['searchfields']['content'].append(encodedecode(resource['value']))
        if 'created' in resource.keys() and annodata_data['datecreated'] < resource['created']:
            annodata_data['datecreated'] = resource['created']
        if 'modified' in resource.keys() and annodata_data['datemodified'] < resource['modified']:
            annodata_data['datemodified'] = resource['modified']
        if 'creator' in resource.keys() and resource['creator']['name'] not in annodata_data['facets']['creator']:
            annodata_data['facets']['creator'].append(resource['creator']['name'])
    annodata_data['searchfields']['content'] = " ".join(annodata_data['searchfields']['content'])
    annodata_data['searchfields']['tags'] = " ".join(annodata_data['facets']['tags'])
    return annodata_data


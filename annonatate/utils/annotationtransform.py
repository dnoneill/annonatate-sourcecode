#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from annonatate.utils.search import getTagsContent, getId, getCreator, getModifiedDate, getCreatedDate

class AnnotationTransform:
    def __init__(self, annotations, type):
        self.annojson = []
        for annotation in annotations:
            print(annotation)
            if type == 'oa':
                self.annojson.append(self.w3ToOA(annotation))
            else:
                self.annojson.append(self.w3ToOA(annotation))

    def getTargetData(self,annotation):
        svg = ''
        xywh = ''
        manifest = ''
        canvas = ''
        if 'target' in annotation.keys():
            if 'source' in annotation.keys():
                canvas = annotation['source']
            if 'selector' in annotation['target'].keys():
                if annotation['target']['selector']['type'] == 'FragmentSelector':
                    xywh = annotation['target']['selector']['value']
                else:
                    svg = annotation['target']['selector']['value']
            if "dcterms:isPartOf" in annotation['target'].keys():
                manifest = annotation['target']["dcterms:isPartOf"]["id"]
        return canvas, svg, xywh, manifest

    def buildAnnoDict(self, content, body, annotype):
        if annotype == "content":
            contdict = {"chars": content, "@type": "dctypes:Text", "format": "text/html"}
        else:
            contdict = {"chars": content, "@type": "oa:Tag"}
        creator = getCreator(body)
        moddate = getModifiedDate(body)
        created = getCreatedDate(body)
        if creator:
            contdict['oa:annotatedBy'] = creator
        if created:
            contdict['oa:annotatedAt'] = created
        if moddate:
            contdict['oa:annotatedAt'] = moddate
        if 'purpose' in body.keys() and body['purpose']:
            contdict['motivation'] = "oa:{}".format(body['purpose'].lower())
        return contdict

    def getResources(self, annotation):
        transformed = []
        bodies = annotation['body'] if 'body' in annotation.keys() else annotation['resource']
        for body in bodies:
            tags, content = getTagsContent(body)
            for cont in content:
                contdict = self.buildAnnoDict(cont, body, 'content')
                transformed.append(contdict)
            for tag in tags:
                contdict = self.buildAnnoDict(tag, body, 'tag')
                transformed.append(contdict)
        return transformed

    def w3ToOA(self, annotationdata):
        annotation = annotationdata
        created = getCreatedDate(annotation)
        print(created)
        moddate = getModifiedDate(annotation)
        canvas, svg, xywh, manifest = self.getTargetData(annotation)
        resources = self.getResources(annotation)
        default = {"@context": "http://iiif.io/api/presentation/2/context.json", 
            "@id": getId(annotation), 
            "@type": "oa:Annotation", 
            "motivation": [
                "oa:commenting"
            ],
            "resource": resources,
            "order": annotation['order'],
            "on": [
                {
                "selector": {},
                "@type": "oa:SpecificResource",
                "full": canvas,
                
                    "within": {
                        "@id": manifest,
                        "@type": "sc:Manifest"
                    }
                }
                ]
            } 
        if xywh:
            xywhdict = {
                    "@type": "oa:FragmentSelector",
                    "value": xywh
                } 
            default['on'][0]['selector']['default'] = xywhdict
        if svg:
            svgdict = {
                    "@type": "oa:SvgSelector",
                    "value": svg
                }
            default['on'][0]['selector']['item'] = svgdict
        if created:
            default["oa:annotatedAt"] = created
        if moddate:
            default["oa:serializedAt"] = moddate
        print(default)
        return default

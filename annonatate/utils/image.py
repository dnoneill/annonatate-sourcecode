#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re, json
from os.path import join as pathjoin
from os.path import splitext as pathsplitext
from iiif_prezi.loader import ManifestReader
import requests
from IIIFpres.utilities import read_API3_json_dict

class Image:
    def __init__(self, request_form, request_files, origin_url):
        self.iiifimage = request_form['upload'] # might be 'uploadimage', or a url
        self.isimage = bool(re.match("^upload(iiif|image)$", self.iiifimage.strip()))
        self.origin_url = origin_url
        self.request_form = request_form
        self.request_files = request_files
        if not self.isimage:
            # handle uploaded url
            self.imgurl, self.iiiffolder = self.iiifimage.rsplit("manifest", 1)[0].strip('/').split('/', 1)
            self.imgurl += '/'
            folderpath = self.iiiffolder.strip("/").split("/")
            self.manifestpath = pathjoin("manifests/", "/".join(folderpath[-2:]))
            self.manifesturl = "{}{}/manifest.json".format(self.origin_url, self.manifestpath)
            self.manifest = self.createmanifest()
            if type(self.manifest) != dict: # manifest creation failed
                self.manifest_markdown = "---\n---\n{}".format(self.manifest)
        else:
            # handle uploaded image
            files = request_files.getlist("file")
            self.files = []
            for filename in request_files.getlist("file"):
                filenameonly, ext = pathsplitext(filename.filename)
                cleanfilename = "".join(re.findall(r'[0-9A-Za-z]+', filenameonly)) +  ext
                self.files.append({'filename': cleanfilename, 'encodedimage': filename.stream.read(), 'label': filenameonly})

    def createActionScript(self, githubfilefolder, filenamelist, isV2=False):
        with open(pathjoin(githubfilefolder, 'iiifportion.txt')) as f:
            iiifscript = f.read().replace('\n', '\\n')
        manifestcodepath = "v2Manifest.txt" if isV2 else "v3Manifest.txt"
        with open(pathjoin(githubfilefolder, manifestcodepath)) as f:
            iiifscript = iiifscript.replace("replacewithManifestCode", f.read().replace('\n', '\\n'))
        with open(pathjoin(githubfilefolder, 'imagetoiiif.yml')) as gf:
            iiifscript = gf.read().replace('replacewithportion', iiifscript)
        iiifscript = iiifscript.replace('replacewithoriginurl', self.origin_url)
        iiifscript = iiifscript.replace('replacewithfilelist', str(filenamelist))
        replacefields = ["label", "folder", "description", "rights", "language", "direction"]
        for field in replacefields:
            replacestring = "replacewith{}".format(field)
            formvalue = self.request_form[field]
            if field == "language" and not formvalue:
                formvalue = "en"
            iiifscript = iiifscript.replace(replacestring, formvalue)
        return iiifscript

    def createmanifest(self):
        manifestresponse = requests.get(self.iiifimage).json()
        if '@id' in manifestresponse.keys():
            manifestresponse['@id'] = self.manifesturl
        elif 'id' in manifestresponse.keys():
            manifestresponse['id'] = self.manifesturl
        manifest = json.dumps(manifestresponse, indent=2)
        return manifest


def addAnnotationList(manifest, session):
    try:
        originurl = session['origin_url']
        cleanmanifest = manifest.replace("{{ '/' | absolute_url }}", originurl)
        cleanmanifest = json.loads(cleanmanifest)
        manifest = parseManifest(cleanmanifest)
        for canvas in manifest.sequences[0].canvases:
            annotationlist = pathjoin(originurl, session['defaults']['annotations'].strip('_'), listfilename(canvas.id))
            othercontentids = list(map(lambda x: x.id, canvas.otherContent))
            if annotationlist not in othercontentids:
                canvas.annotationList(annotationlist)
        stringmanifest = manifest.toString(compact=False)
    except:
        try:
            manifest = read_API3_json_dict(json.loads(manifest))
            for item in manifest.items:
                annotations = list(map(lambda x: x['id'], item.annotations)) if item.annotations else []
                annotationlist = pathjoin(originurl, session['defaults']['annotations'].strip('_'), listfilename(item.id))
                if annotationlist not in annotations:
                    annopage = item.add_annotation()
                    annopage.set_id(annotationlist)
            stringmanifest = manifest.json_dumps()
        except:
            stringmanifest = json.dumps(manifest) if type(manifest) == dict else manifest
    return stringmanifest

def parseManifest(manifest):
    reader = ManifestReader(manifest)
    manifest = reader.read()
    return manifest
        
def listfilename(canvas):
    r = re.compile("\d+")
    canvas = canvas.replace('.json', '')
    canvaslist = canvas.split('/')
    withnumbs = list(filter(r.search, canvaslist))
    filename = "-".join(withnumbs) if len(withnumbs) > 0 else canvaslist[-1]
    filename = re.sub('[^A-Za-z0-9]+', '-', filename).lower()
    return filename + '-list.json'
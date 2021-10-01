#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re, json
from os.path import join as pathjoin
from os.path import splitext as pathsplitext
from iiif_prezi.factory import ManifestFactory
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
            self.imgurl, self.iiiffolder = self.iiifimage.rstrip('/').rsplit('/', 1)
            self.imgurl += '/'
            self.manifestpath = "manifests/{}".format(self.iiiffolder)
            self.url = self.iiifimage
            self.tmpfilepath = False
            self.manifesturl = "{}{}/manifest.json".format(self.origin_url, self.manifestpath)
            self.manifest = self.createmanifest()
            if type(self.manifest) != dict: # manifest creation failed
                manifest_markdown = self.manifest.toString(compact=False).replace('canvas/info.json', 'info.json').replace('https://{{site.url}}', '{{site.url}}')
                self.manifest_markdown = "---\n---\n{}".format(manifest_markdown)
        else:
            # handle uploaded image
            files = request_files.getlist("file")
            self.files = []
            for filename in request_files.getlist("file"):
                filenameonly, ext = pathsplitext(filename.filename)
                if ext != '.jpg' and ext != '.jpeg':
                    ext =  '.jpg'
                cleanfilename = "".join(re.findall(r'[0-9A-Za-z]+', filenameonly)) +  ext
                self.files.append({'filename': cleanfilename, 'encodedimage': filename.stream.read()})

    def createActionScript(self, githubfilefolder, filenamelist):
        with open(pathjoin(githubfilefolder, 'iiifportion.txt')) as f:
            iiifscript = f.read().replace('\n', '\\n')
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
        try:
            fac = ManifestFactory()
            fac.set_base_prezi_uri(self.url)
            fac.set_base_image_uri(self.imgurl)
            fac.set_iiif_image_info(2.0, 2)
            manifest = fac.manifest(ident=self.manifesturl, label=self.request_form['label'])
            manifest.viewingDirection = self.request_form['direction']
            manifest.description = self.request_form['description']
            manifest.set_metadata({"rights": self.request_form['rights']})
            seq = manifest.sequence()
            cvs = seq.canvas(ident='info', label=self.request_form['label'])
            anno = cvs.annotation(ident="{}{}/annotation/1.json".format(self.origin_url, self.manifestpath))
            img = anno.image(self.iiiffolder, iiif=True)
        except Exception as e:
            return {'error': e}
        if self.tmpfilepath:
            img.set_hw_from_file(self.tmpfilepath)
        else:
            try:
                img.set_hw_from_iiif()
            except:
                try:
                    response = requests.get("{}{}/info.json".format(self.imgurl, self.iiiffolder))
                    if response.status_code > 299:
                        response = requests.get("{}{}".format(self.imgurl, self.iiiffolder))
                    try:
                        content = response.json()
                    except:
                        return {'error': 'No IIIF image exists at {}{}'.format(self.imgurl, self.iiiffolder)}
                        # im = Image.open(BytesIO(response.content))
                        # print(im.size)
                        # content = {'height': im.size[1], 'width': im.size[0]}
                    img.height = content['height']
                    img.width = content['width']
                except:
                    return {'error': 'Unable to get height/width for image located at {}{}'.format(self.imgurl, self.iiiffolder)}
        cvs.height = img.height
        cvs.width = img.width
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
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from iiif_prezi.factory import ManifestFactory
import requests

import pdb

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
            self.file = request_files['file']
            self.encodedimage = self.file.stream.read()

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
        
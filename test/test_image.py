import unittest

import annonatate.utils.image as ImageClass
import requests
import requests_mock
import json
from werkzeug.datastructures import FileStorage

class TestImage(unittest.TestCase):
   def setUp(self):
      self.request_form = {'upload': 'file:test/testdata/imagetest', 'label': 'This is the label', 'direction': 'left-to-right', 'description': 'This is the description', 'rights': 'This is the rights'}
      self.request_files = []
      self.request_url = 'http://session/origin_url/'
      self.image = ImageClass.Image(self.request_form, self.request_files, self.request_url)
      self.manifest = self.image.manifest.toJSON(top=True)

   def test_image_iiif(self):
      self.assertFalse(self.image.isimage)
      self.assertEqual(self.image.manifest.label, 'This is the label')
      self.assertEqual(self.manifest['sequences'][0]['canvases'][0]['width']
, 1784)
      self.assertEqual(self.manifest['sequences'][0]['canvases'][0]['images'][0]['@id'], 'http://session/origin_url/manifests/imagetest/annotation/1.json')

class TestAddAnnotationList(unittest.TestCase):
   def setUp(self):
      self.session = {'origin_url' : "https://testuser.github.io/annonatate",
      'defaults': {'annotations': '_annotations'}}
      with open('test/testdata/manifest.json') as f:
        self.manifest = f.read()
      self.matchcanvas = "https://stacks.stanford.edu/image/iiif/wh234bz9013%252Fwh234bz9013_05_0001/info.json"
      updatedManifest = ImageClass.addAnnotationList(self.manifest, self.session)
      self.updatedManifest = json.loads(updatedManifest)

   def test_add_annotation(self):
      loadedannotation = self.updatedManifest['sequences'][0]['canvases'][0]['otherContent']
      self.assertEqual(self.updatedManifest["@id"], "{}/manifests/wh234bz9013%252Fwh234bz9013_05_0001/manifest.json".format(self.session['origin_url']))
      self.assertEqual(loadedannotation[0]['@id'], "{}/annotations/wh234bz9013-252fwh234bz9013-05-0001-list.json".format(self.session['origin_url']))

class TestAddAnnotationListWithV3(unittest.TestCase):
   def setUp(self):
      self.session = {'origin_url' : "https://testuser.github.io/annonatate",
      'defaults': {'annotations': '_annotations'}}
      self.annotationlist = "https://testuser.github.io/annonatate/annotations/0002386-list.json"
      with open('test/testdata/manifestv3.json') as f:
        self.manifest = f.read()
      self.matchcanvas = "https://iiif.io/api/cookbook/recipe/0001-mvm-image/page/p1/1"
      updatedManifest = ImageClass.addAnnotationList(self.manifest, self.session)
      self.updatedManifest = json.loads(updatedManifest)
      
   def test_add_annotation(self):
      self.assertEqual(self.updatedManifest, self.manifest)

if __name__ == '__main__':
   # begin the unittest.main()
   unittest.main()

import unittest

import annonatate.utils.image as ImageClass
import requests
from unittest.mock import patch
import json, io, yaml
from werkzeug.datastructures import FileStorage, ImmutableMultiDict

class TestManifest(unittest.TestCase):
   def setUp(self):
      self.request_form = ImmutableMultiDict({'upload': 'test/testdata/manifest.json', 'added': '2022-01-20', 'user': 'testuser'})
      with patch('requests.get') as mock_request:
         url = self.request_form['upload']
         mock_request.return_value.status_code = 200
         with open(url) as f:
            mock_request.return_value.json.return_value = json.loads(f.read())
         self.request_files = []
         self.request_url = 'http://session/origin_url/'
         self.image = ImageClass.Image(self.request_form.to_dict(), self.request_files, self.request_url)
         self.manifest = json.loads(self.image.manifest)
   def test_manifest_iiif(self):
      self.assertFalse(self.image.isimage)
      self.assertEqual(self.manifest['label'], 'test upload')
      self.assertEqual(self.manifest['@id'], 'http://session/origin_url/manifests/testdata/manifest.json')

class TestImageDefault(unittest.TestCase):
   def setUp(self):
      self.request_form = ImmutableMultiDict({'upload': 'uploadimage', 'added': '2022-01-20', 'user': 'testuser', 'version': 'v3', 'label': 'This is the label', 'direction': 'left-to-right', 'description': 'This is the description: with colon', 'rights': 'This is the rights', 'language': ''})
      self.request_files = []
      self.request_files.append(("file", FileStorage(io.BytesIO(b'my file contents'), 'filename.jpg')))
      self.request_files.append(("file", FileStorage(io.BytesIO(b'my file contents'), 'filename2.png')))
      self.filenamelist = []
      self.request_files = ImmutableMultiDict(self.request_files)
      self.request_url = 'http://session/origin_url/'
      self.image = ImageClass.Image(self.request_form.to_dict(), self.request_files, self.request_url)
      for files in self.image.files:
         self.filenamelist.append(files['filename'])
      self.actionscript = self.image.createActionScript('annonatate/static/githubfiles/', self.filenamelist)
   
   def test_manifest_iiif(self):
      self.assertTrue(self.image.isimage)
      self.assertEqual(self.image.files, [{'filename': 'filename.jpg', 'encodedimage': b'my file contents', 'label': 'filename'}, {'filename': 'filename2.png', 'encodedimage': b'my file contents', 'label': 'filename2'}])
      self.maxDiff = None
      self.parsedActionScript= yaml.load(self.actionscript, Loader=yaml.FullLoader)['jobs']['convertimages']['steps']
      self.assertTrue("iiifpapi3.BASE_URL" in self.parsedActionScript[4]['run'])
      self.assertFalse("fac.set_iiif_image_info(2.0, 2)" in self.parsedActionScript[4]['run'])
      # self.assertEqual(self.parsedActionScript[5]['run'], 'echo -e "---\\n---\\n$(cat img/derivatives/iiif/Thisisthelabel/manifest.json)" > img/derivatives/iiif/Thisisthelabel/manifest.json')

class TestImageV2(unittest.TestCase):
   def setUp(self):
      self.request_form = ImmutableMultiDict({'upload': 'uploadimage', 'added': '2022-01-20', 'user': 'testuser', 'version': 'v2', 'label': 'This is the label', 'direction': 'left-to-right', 'description': 'This is the description', 'rights': 'This is the rights', 'language': ''})
      self.request_files = []
      self.request_files.append(("file", FileStorage(io.BytesIO(b'my file contents'), 'filename.jpg')))
      self.request_files.append(("file", FileStorage(io.BytesIO(b'my file contents'), 'filename2.png')))
      self.filenamelist = []
      self.request_files = ImmutableMultiDict(self.request_files)
      self.request_url = 'http://session/origin_url/'
      self.image = ImageClass.Image(self.request_form.to_dict(), self.request_files, self.request_url)
      for files in self.image.files:
         self.filenamelist.append(files['filename'])
      self.actionscript = self.image.createActionScript('annonatate/static/githubfiles/', self.filenamelist)
   
   def test_manifest_iiif(self):
      self.assertTrue(self.image.isimage)
      self.assertEqual(self.image.files, [{'filename': 'filename.jpg', 'encodedimage': b'my file contents', 'label': 'filename'}, {'filename': 'filename2.png', 'encodedimage': b'my file contents', 'label': 'filename2'}])
      self.maxDiff = None
      self.parsedActionScript= yaml.load(self.actionscript, Loader=yaml.FullLoader)['jobs']['convertimages']['steps']
      self.assertFalse("iiifpapi3.BASE_URL" in self.parsedActionScript[4]['run'])
      self.assertTrue("fac.set_iiif_image_info(2.0, 2)" in self.parsedActionScript[4]['run'])
      # self.assertEqual(self.parsedActionScript[5]['run'], 'echo -e "---\\n---\\n$(cat img/derivatives/iiif/Thisisthelabel/manifest.json)" > img/derivatives/iiif/Thisisthelabel/manifest.json')

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
      updatedManifest = ImageClass.addAnnotationList(updatedManifest, self.session)
      self.updatedManifest = json.loads(updatedManifest)
      
   def test_add_annotation(self):
      self.assertEqual(len(self.updatedManifest['items'][0]['annotations']), 1)
      self.assertEqual(self.updatedManifest['items'][0]['annotations'][0]['id'], "https://testuser.github.io/annonatate/annotations/0001-mvm-image-p1-list.json")
      self.assertNotEqual(self.updatedManifest, self.manifest)

class TestAddAnnotationListWithNoManifest(unittest.TestCase):
   def setUp(self):
      self.session = {'origin_url' : "https://testuser.github.io/annonatate",
      'defaults': {'annotations': '_annotations'}}
      self.annotationlist = "https://testuser.github.io/annonatate/annotations/0002386-list.json"
      self.manifest = {'context': 'https://test.com'}
      self.matchcanvas = "https://iiif.io/api/cookbook/recipe/0001-mvm-image/page/p1/1"
      updatedManifest = ImageClass.addAnnotationList(self.manifest, self.session)
      updatedManifest = ImageClass.addAnnotationList(updatedManifest, self.session)
      self.updatedManifest = json.loads(updatedManifest)
      
   def test_add_annotation(self):
      self.assertEqual(self.updatedManifest, self.manifest)
if __name__ == '__main__':
   # begin the unittest.main()
   unittest.main()

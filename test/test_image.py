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

if __name__ == '__main__':
   # begin the unittest.main()
   unittest.main()

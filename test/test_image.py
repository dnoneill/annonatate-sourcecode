import unittest
import image as ImageClass
import requests
import requests_mock
import json
from werkzeug.datastructures import FileStorage

import pdb

class Test(unittest.TestCase):
   def test_image_iiif(self):
      request_form = {'upload': 'file:testdata/imagetest', 'label': 'This is the label', 'direction': 'left-to-right', 'description': 'This is the description', 'rights': 'This is the rights'}
      request_files = []
      request_url = 'http://session/origin_url/'

      image = ImageClass.Image(request_form, request_files, request_url)
      self.assertFalse(image.isimage)
      self.assertEqual(image.manifest.label, 'This is the label')
      mfst = image.manifest.toJSON(top=True)
      self.assertEqual(mfst['sequences'][0]['canvases'][0]['width']
, 1784)
      self.assertEqual(mfst['sequences'][0]['canvases'][0]['images'][0]['@id'], 'http://session/origin_url/manifests/imagetest/annotation/1.json')

if __name__ == '__main__':
   # begin the unittest.main()
   unittest.main()

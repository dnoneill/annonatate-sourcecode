import unittest

import annonatate.utils.collectionform as CollectionForm
import ast

class TestCollectionForm(unittest.TestCase):
   def setUp(self):
      with open('test/testdata/collections.txt') as f:
        self.collections = ast.literal_eval(f.read())
      self.formvalues = CollectionForm.CollectionForm('test', {'args': {}}, {'test': {'json': self.collections}}).formvalues

   def test_collection_form(self):
      self.assertEqual(self.formvalues['add'], False)
      self.assertEqual(self.formvalues['title'], 'test')
      self.assertEqual(len(self.formvalues['annotations']), 2)
      self.assertEqual(self.formvalues['annotations'][0]['url'], "https://dnoneill.github.io/annonatate/annotations/mc00336-1911bldg-may2017-list.json")

class TestCollectionFormWithAdd(unittest.TestCase):
   def setUp(self):
      with open('test/testdata/collections.txt') as f:
        self.collections = ast.literal_eval(f.read())
      self.args = {'url': 'https://testing.com/annotations/1.json',
      'desc': '',
      'annotitle': 'annotitle',
      'viewtype': 'storyboard',
      'thumbnail': '',
      'title': 'test'
      }
      self.formvalues = CollectionForm.CollectionForm('', self.args, {'test': {'json': self.collections}}).formvalues

   def test_collection_form_with_add(self):
      self.assertEqual(self.formvalues['add'], True)
      self.assertEqual(self.formvalues['title'], 'test')
      self.assertEqual(len(self.formvalues['annotations']), 1)
      self.assertEqual(self.formvalues['annotations'][0]['url'], "https://testing.com/annotations/1.json")

if __name__ == '__main__':
   # begin the unittest.main()
   unittest.main()

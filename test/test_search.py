#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import search as anno
import json
import ast

import pdb

class Test(unittest.TestCase):

    # TODO: trim this down to just the fields needed by search, and anonymize it
    def setUp(self):
      with open('testdata/annotations.txt') as f:
        self.annotations = ast.literal_eval(f.read())

    def test_search_query_none(self):
      search = anno.Search({'q': 'stringnotfound', 'creator': '', 'tag': ''}, self.annotations)

      self.assertEqual(len(search.items), 0)

    def test_search_query(self):
      search = anno.Search({'q': 'branch', 'creator': '', 'tag': ''}, self.annotations)

      self.assertEqual(len(search.items), 1)
      self.assertEqual(search.items[0]['basename'], '19547cb3-f588-4724-878b-e4f81415fa86.json')

    def test_search_creator(self):
      search = anno.Search({'q': '', 'creator': 'Test User', 'tag': ''}, self.annotations)

      self.assertEqual(len(search.items), 2)
      self.assertEqual(search.items[0]['basename'], '142a41cd-6bb8-4052-a2b3-a300bfd15a9a.json')

    def test_search_tag(self):
      search = anno.Search({'q': '', 'creator': '', 'tag': 'Machinery'}, self.annotations)

      self.assertEqual(len(search.items), 1)
      self.assertEqual(search.items[0]['basename'], '142a41cd-6bb8-4052-a2b3-a300bfd15a9a.json')

if __name__ == '__main__':
   # begin the unittest.main()
   unittest.main()

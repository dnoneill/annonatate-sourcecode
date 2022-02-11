#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import annonatate.utils.annogetters as annogetters
import ast

class TestGetters(unittest.TestCase):

    def setUp(self):
      with open('test/testdata/annotations.txt') as f:
        self.annotations = ast.literal_eval(f.read())
      self.v3canvas = annogetters.getCanvas(self.annotations[1]['json'])
      self.v3manifest = annogetters.getManifest(self.annotations[1]['json'])
      self.v3canvas2 = annogetters.getCanvas(self.annotations[3]['json'])
      self.v3manifest2 = annogetters.getManifest(self.annotations[3]['json'])
      self.v2canvas = annogetters.getCanvas(self.annotations[4]['json'])
      self.v2manifest = annogetters.getManifest(self.annotations[4]['json'])
      

    def test_getters(self):
        self.assertEqual(self.v3canvas, "https://iiif.lib.ncsu.edu/iiif/0002386/info.json")
        self.assertEqual(self.v3manifest, "")
        self.assertEqual(self.v3canvas2, "https://testuser.github.io/annonatate/images/scan_20210223050407_0019.jpg")
        self.assertEqual(self.v3manifest2, "placeholdermanifest")
        self.assertEqual(self.v2canvas, "https://d.lib.ncsu.edu/collections/canvas/nubian-message-2002-04-18_0002")
        self.assertEqual(self.v2manifest, "https://d.lib.ncsu.edu/collections/catalog/nubian-message-2002-04-18/manifest")

if __name__ == '__main__':
   # begin the unittest.main()
   unittest.main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock
from unittest.mock import patch
import flask_github

import annonatate.utils.github as anno
import json
import ast

class TestGitHub(unittest.TestCase):

  def setUp(self):
    print("setup")
    self.github = anno.GitHubAnno(None)
    self.session = {'github_branch': 'gb', 'github_url': 'https://api.github.com/repos/testuser/annonatate/contents'}

    @self.github.access_token_getter
    def get_token_getter():
        return 'asdf'

  mock_raw_request = Mock()
  mock_raw_request.return_value.json.return_value = {'test': 'test'}
  @patch('annonatate.utils.github.GitHubAnno.raw_request', mock_raw_request)
  def test_search_query_none(self):
    mock_session = {
      'github_url': 'https://api.github.com/repos/testuser/annonatate/contents',
      'github_branch': 'gb'
    }

    datadict = self.github.createdatadict(
      mock_session,
      'testimage.jpg',
      'text of image',
      'images',
      ''
    )
    self.assertEqual(datadict['data']['message'], 'write testimage.jpg')
    self.assertEqual(datadict['data']['content'], 'dGV4dCBvZiBpbWFnZQ==')
    self.assertNotIn('sha', datadict['data'])
    self.assertEqual(datadict['url'], 'https://api.github.com/repos/testuser/annonatate/contents/images/testimage.jpg')


  # with uploaded file: this will result in raw_request returning a sha value
  mock_raw_request = Mock()
  mock_raw_request.return_value.json.return_value = {'sha': 'sha-abcdef'}
  @patch('annonatate.utils.github.GitHubAnno.raw_request', mock_raw_request)
  def test_search_query_upload(self):
    mock_session = {
      'github_url': 'https://api.github.com/repos/testuser/annonatate/contents',
      'github_branch': 'gb'
    }
    datadict = self.github.createdatadict(
      mock_session,
      'testimage.jpg',
      'text of image',
      'images',
      ''
    )
    self.assertEqual(datadict['data']['sha'], 'sha-abcdef')

if __name__ == '__main__':
   # begin the unittest.main()
   unittest.main()

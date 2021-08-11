#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, MagicMock
from unittest.mock import patch
import flask_github

import annonatate.utils.github as anno
import json
import ast

class TestGitHub(unittest.TestCase):

    def setUp(self):
        self.github = anno.GitHubAnno(None)
        self.session = {'github_branch': 'gb', 'github_url': 'https://api.github.com/repos/testuser/annonatate/contents'}

        @self.github.access_token_getter
        def get_token_getter():
            return 'asdf'

    mock_github_get = Mock()
    mock_github_get.return_value.json.return_value = {'test': 'test'}
    @patch('annonatate.utils.github.GitHubAnno.raw_request', mock_github_get)
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
    mock_github_get = Mock()
    mock_github_get.return_value.json.return_value = {'sha': 'sha-abcdef'}
    @patch('annonatate.utils.github.GitHubAnno.raw_request', mock_github_get)
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

    # test deletion of session annotations that have been deleted in Github repo (e.g. by another user)
    keep_annotation_github = { "name": "annotation_to_keep" }
    keep_annotation_session = { "filename": "http://test/annotation_to_keep" }
    delete_annotation_session = { "filename": "http://test/annotation_to_delete" }

    mock_github_get = MagicMock()
    mock_github_get.return_value = [keep_annotation_github]
    @patch('annonatate.utils.github.GitHubAnno.get', mock_github_get)
    def test_updateAnnos(self):
        test_session = {
            'currentworkspace': {
                'contents_url': 'https://api.github.com/repos/testuser/annonatate/contents/{+path}'
            },
            'annotations': [self.keep_annotation_session, self.delete_annotation_session]
        }
        filepath = '_annotations'
        self.github.updateAnnos(test_session, filepath)
        self.assertEqual(len(test_session['annotations']), 1) # one has been deleted
        self.assertEqual(test_session['annotations'][0]['filename'], self.keep_annotation_session['filename']) # right one has been kept

if __name__ == '__main__':
    # begin the unittest.main()
    unittest.main()

import glob, json, os, shutil

def annotations():
    if len(glob.glob('_annotations')) > 0:
        shutil.rmtree('_annotations')
    os.mkdir('_annotations')
    for file in glob.glob('annotations/*'):
        if '.json' in file and 'collection.json' not in file:
            jsoncontents = json.load(open(file, 'rb'))
            annolist = jsoncontents['resources'] if 'resources' in jsoncontents.keys() else jsoncontents['items']
            canvas = annolist[0]['on'][0]['full']
            filename = os.path.basename(file).replace('.json', '') + '-list.json'
            with open('_annotations/{}'.format(filename), 'w') as f:
                context = jsoncontents['@context']
                if '3' in context:
                    annotype = 'AnnotationPage'
                    itemskey = 'items'
                else:
                    annotype = 'oa:AnnotationList'
                    itemskey = 'resources'
                text = '''---\ncanvas_id: '{}'\n---\n'''.format(canvas)
                text += '''{% assign annotations = site.annotations | where: 'canvas', page.canvas_id | sort: 'order' | map: 'content' %}\n'''
                text += '''{\n"@context": "%s",\n
                "id": "{{ site.url }}{{ site.baseurl }}{{page.url}}",
                \n"type": "%s",\n"%s": [{{ annotations | join: ','}}] }'''%(context, annotype, itemskey)
                f.write(text)
            for order, item in enumerate(annolist):
                idfield = 'id' if 'id' in item.keys() else '@id'
                filename = item[idfield].split('/')[-1]
                with open('_annotations/{}'.format(filename), 'w') as f:
                    text = '''---\ncanvas: '{}'\norder: {}\n---\n{}'''.format(canvas, order, json.dumps(item,indent=4))
                    f.write(text)
    shutil.rmtree('__pycache__')


def _annotations():
    os.system("jekyll build")
    for file in glob.glob('_site/annotations/*-list.json'):
        jsoncontents = json.load(open(file))
        filename = os.path.basename(file).replace('-list', '')
        with open(os.path.join('annotations/{}'.format(filename)), 'w') as f:
            f.write(json.dumps(jsoncontents, indent=4))
    shutil.rmtree('_site')
    shutil.rmtree('__pycache__')

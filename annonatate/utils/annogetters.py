def getCanvas(annotation):
    canvas = ''
    if 'target' in annotation.keys():
        canvas = annotation['target']['source']
    elif 'on' in annotation.keys():
        canvas = annotation['on'][0]['full']
    return canvas

def getManifest(annotation):
    manifest = ''
    if 'target' in annotation.keys() and 'dcterms:isPartOf' in annotation['target'].keys():
        manifest = annotation['target']['dcterms:isPartOf']['id']
    elif 'on' in annotation.keys():
        manifest = annotation['on'][0]['within']['@id']
    return manifest
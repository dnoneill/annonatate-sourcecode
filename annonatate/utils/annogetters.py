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

def contextType(session):
    ismirador = isMirador(session)
    if ismirador:
        context =  "http://iiif.io/api/presentation/2/context.json"
        annotype = "oa:AnnotationList"
        itemskey = "resources"
    else:
        context = "http://iiif.io/api/presentation/3/context.json"
        annotype = "AnnotationPage"
        itemskey = "items"
    return context, annotype, itemskey

def isMirador(content):
    ismirador = True if 'settings' in content['preloaded'].keys() and 'viewer' in content['preloaded']['settings'].keys() and content['preloaded']['settings']['viewer'] == 'mirador' else False
    return ismirador

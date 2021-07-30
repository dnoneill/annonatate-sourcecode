from iiif_prezi.loader import ManifestReader

def addAnnotationList(manifest, matchcanvas, annotationlist, originurl):
	manifest = parseManifest(manifest)
	for canvas in manifest.sequences[0].canvases:
		if canvas.id == matchcanvas:
			canvas.annotationList(annotationlist)
	stringmanifest = manifest.toString(compact=False).replace(originurl, "{{ '/' | absolute_url }}")
	pagecontent = '---\nlayout: none\n---\n' + stringmanifest
	return pagecontent

def parseManifest(manifest):
	reader = ManifestReader(manifest)
	manifest = reader.read()
	return manifest


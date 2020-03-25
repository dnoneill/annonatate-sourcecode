function make_embed_code(id){
	if ($("#" + id + "_embeditem").css("display") == 'none'){
    $("#" + id + "_embeditem").css("display", "flex")
    $("#" + id + "_button").html("Hide embed code")
  } else {
    $("#" + id + "_embeditem").css("display", "none")
    $("#" + id + "_button").html("Show embed code")
  }
}

function copytoclipboard(id) {
	var copyText = document.getElementById(id);
	copyText.select();
	document.execCommand("copy");
	var tooltip_id = id.replace("_embedcode", "_tooltip")
	var tooltip = document.getElementById(tooltip_id);
  tooltip.innerHTML = "Copied!";
}

function outFunc(id) {
  var tooltip = document.getElementById(id);
  tooltip.innerHTML = "Copy to clipboard";
}

function write_annotation(senddata, method, apiserver, annotation=false) {
  jQuery.ajax({
    url:  apiserver + method + '_annotations/',
    type: "POST",
    dataType: "json",
    data: JSON.stringify(senddata),
    contentType: "application/json; charset=utf-8",
    success: function(data) {
      if (annotation) {
        annotation['id'] = data['@id']
      }
    },
    error: function() {
      returnError();
    }
  });
}

function buildAnno(annotation, annotorious, baseurl, height, width){
    var tags = getTags()
    var xywh = annotation.shapes[0].geometry;
    var x = parseInt(xywh['x']*width);
    var y = parseInt(xywh['y']*height);
    var w = parseInt(xywh['width']*width);
    var h = parseInt(xywh['height']*height);
    var targetid = baseurl + `#xywh=${x},${y},${w},${h}`
    var shape_type = document.getElementById("shapetype") ? document.getElementById("shapetype").value : "";
    var popuptags = document.getElementById("tags") ? document.getElementById("tags").value : "";
    var author = document.getElementById("author") ? document.getElementById("author").value.split(",") : "";
    author = author ? author.map(element=>element.trim()) : '';
    annotation['shapetype'] = shape_type;
    annotation['tags'] = popuptags;
    annotation['author'] = author;
    var date = new Date().toISOString();
    var annotation_data = annotation.text;
    var body = [{
      "value": `${annotation_data}`,
      "type": "TextualBody",
      "format": "text/html",
      "selector": {
      	"type": "FragmentSelector",
      	"value": `${shape_type}`
      }
    }]
    body = body.concat(tags)
    var w3_annotation = {
      "type": "Annotation",
      "@context": "http://www.w3.org/ns/anno.jsonld",
      "creator" : author,
      "@id" : `${annotation['id']}`,
      "body": body,
      "target": {
        "id": `${targetid}`,
        "type": "Image"
      }
    }
    if (annotation['created']) {
      w3_annotation['modified'] = date;
      annotation['modified'] = date;
			w3_annotation['created'] = annotation['created'];
    } else {
      w3_annotation['created'] = date;
      annotation['created'] = date;
    }
    return w3_annotation
}

function getTags() {
  var tagging_json = [];
  if(document.getElementById("tags")){
    var tags =  document.getElementById("tags").value.split(",")
    for (var i=0; i<tags.length; i++){
      if (tags[i].trim()){
        tagging_json.push({
          "value": tags[i].trim(),
          "type": "TextualBody",
          "purpose": "tagging",
          "format": "text/plain"
        })
      }
    }
  }
  return tagging_json;
}

function escapetags(stringjson) {
	var regex = /<iiif-(.*?)><\/iiif-(.*?)>/gm;
	var matches = stringjson.match(regex);
	if (matches) {
		for (var ma=0; ma<matches.length; ma++){
			var replacematch = matches[ma].replace(/</g, "&lt;").replace(/>/g, "&gt;")
			stringjson = stringjson.replace(matches[ma], replacematch)
		}
	}
	return stringjson;
}

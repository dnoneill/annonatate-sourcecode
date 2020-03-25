---
layout: null
---
var docs = 
{
{% for anno in site.annotation_data %}
"{{anno.slug}}" : {{anno | jsonify}}
{% unless forloop.last %}, {% endunless %}
{% endfor %}
}

var lunr_settings = {{site.lunr_settings| jsonify}}

var view_facets = "{{site.view_facets}}"

var baseurl = "{{site.baseurl}}"

var liveidx = lunr(function() {
   this.pipeline.remove(lunr.stemmer);
  this.searchPipeline.remove(lunr.stemmer);
  this.pipeline.remove(lunr.stopWordFilter);
  this.searchPipeline.remove(lunr.stopWordFilter);
  this.tokenizer.separator = /[\s,.;:/?!()]+/;
  for (var l=0; l<lunr_settings['fields'].length; l++){
    this.field(lunr_settings['fields'][l]['searchfield'], {'boost': lunr_settings['fields'][l]['boost']}); 	
  }

  {% for anno in site.annotation_data %}
  	var fields = {{site.lunr_settings.fields | jsonify }}
	var anno_data = {{anno | jsonify}}
	var doc = {"id": "{{anno['slug']}}"}
	for (var k =0; k<fields.length; k++){
		for (var m=0; m<fields[k]['jekyllfields'].length; m++){
			var field_data = anno_data[fields[k]['jekyllfields'][m]];
			var cleaned_data = Array.isArray(field_data) ? field_data.join(" ") : field_data;
			cleaned_data = cleaned_data.replace(/<(?:.|\n)*?>/gm, '').replace(/\n|\r/g, "");
			doc[fields[k]['searchfield']] = cleaned_data;
		}
    }
	this.add(doc)
  {% endfor %}  
});

var index = JSON.stringify(liveidx)


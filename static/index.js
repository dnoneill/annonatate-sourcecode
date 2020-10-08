const annoview = Vue.component('annoview', {
  template: `<div>
  <div v-for="manifest in existing['manifests']">
    <a v-on:click="getManifest(manifest)">{{manifest}}</a>
  </div>
  <div v-for="image in existing['images']">
    <a v-on:click="inputurl = image; currentmanifest='';loadAnno(image)">{{image}}</a>
  </div>
  <div>
    <label>Manifest</label>
    <input v-on:change="getManifest(currentmanifest)" v-model="currentmanifest"></input>
    <button v-on:click="showManThumbs = !showManThumbs" v-if="currentmanifest">
      <span v-if="showManThumbs">Hide</span><span v-else>Show</span> Manifest Thumbnails
    </button>
  </div>
  <div class="manifestthumbs" v-show="showManThumbs && currentmanifest">
    <div v-for="item in manifestdata" style="display: inline-block;">
      <div v-on:click="manifestLoad(item)">
        <img :src="item['image']" style="max-width:100px;padding:5px;">
      </div>
    </div>
  </div>
  <div>
    <label>Image URL</label>
    <input v-on:change="currentmanifest = '';loadAnno()" v-model="inputurl"></input>
  </div>
  <label for="current-tool" v-if="anno">Current Annotation drawing shape: </label>
  <button id="current-tool" v-if="anno" v-on:click="toggle()">{{drawtool}}</button>
  <div v-for="item in alltiles" v-if="alltiles.length > 1">
    <input type="checkbox" class="tagscheck" v-on:click="setOpacity(item)" v-model="item.checked">
    <span v-html="item.label"></span>
    <div class="slidecontainer">Opacity: <input v-on:change="setOpacity(item, $event)" type="range" min="0" max="100" v-bind:value="item.opacity*100" class="slider"></div>
    <img :src="item['thumbnail']" style="max-width:100px;padding:5px;">
  </div>
  <div id="openseadragon1" style="height:100vh"></div>
  </div>
  `,
  props: {
    'existing': Object,
    'filepaths': Object,
    'userinfo': Object,
    'tags': Array
  },
  data: function() {
  	return {
      inputurl: '',
      drawtool: 'rectangle',
      anno: '',
      manifestdata: '',
      currentmanifest: '',
      showManThumbs: true,
      canvas: '',
      alltiles: []
  	}
  },
  mounted() {
  },
  methods: {
    manifestLoad: function(item) {
      this.canvas = item['canvas'];
      this.inputurl = item['tiles'][0]['id'];
      this.alltiles = item['tiles'];
      this.loadAnno()
      this.showManThumbs = false;
    },
    loadAnno: function() {
      document.getElementById('openseadragon1').innerHTML = '';
      var tilesources = [this.inputurl]
      if (this.inputurl.indexOf('.jpg') > 1) {
        tilesources = {
            type: "image",
            url: this.inputurl
        }
      }
      var viewer = OpenSeadragon({
        id: "openseadragon1",
        prefixUrl: "/assets/openseadragon/images/",
        tileSources: tilesources
      });
      var vue = this;
      for (var k=1; k<this.alltiles.length; k++){
        this.setLayers(this.alltiles[k], k, viewer)
      } 

      var id = this.inputurl;
      //localStorage.setItem('')
      // Initialize the Annotorious plugin
      var existing = this.currentmanifest ? this.filepaths[this.canvas] : this.filepaths[this.inputurl];

      this.anno = OpenSeadragon.Annotorious(viewer, 
        { image: 'openseadragon1',
          widgets: [ 
                    {widget: 'COMMENT', editable: 'MINE_ONLY'},
                    {widget: 'TAG', vocabulary: vue.tags},
                    vue.languagePlugin,
                    vue.inputPlugin
                  ]});
    // Load annotations in W3C WebAnnotation format
      if (existing){
        var annotation = this.anno.setAnnotations(existing); 
      }
      this.addListeners();
      this.anno.setAuthInfo({
        id: this.userinfo["id"],
        displayName: this.userinfo["name"]
      });
    },
    setLayers: function(layer, position, viewer){
      var vue = this;
      tiledimage = viewer.addTiledImage({
        tileSource: layer['id'],
        opacity: layer['opacity'],
        success: function (obj) {
          vue.alltiles[position]['osdtile'] = obj.item;
        }
      });
    },
    inputPlugin: function(args) {
      var currentRightsBody = args.annotation ? args.annotation.bodies.find(function(b) {
        return b.rights;
      }) : null;
      var currentRightsValue = currentRightsBody ? currentRightsBody.rights : '';

      var addTag = function(evt) {
        if (currentRightsBody) {
          args.onUpdateBody(currentRightsBody, {
            rights: evt.target.value
          });
        } else { 
          args.onAppendBody({
            rights: evt.target.value
          });
        }
      }

      var createInput = function() {
        var div = document.createElement('div');
        div.className = "r6o-autocomplete"
        var input = document.createElement('input');
        input.value = currentRightsValue;
        input.placeholder = 'Add rights statement'
        input.addEventListener('change', addTag); 
        div.appendChild(input)
        return div;
      }

      var container = document.createElement('div');
      container.className = 'r6o-widget r6o-tag';
      
      var rights = createInput();
      container.appendChild(rights);

      return container;
    },
    languagePlugin: function(args) {
      var currentLangBody = args.annotation ? args.annotation.bodies.find(function(b) {
        return b.language;
      }) : null;
      var currentLangValue = currentLangBody ? currentLangBody.language : '';
      currentLangValue = currentLangValue && Array.isArray(currentLangValue) ? currentLangValue.map(langcd => ISO6391.getName(langcd) ? ISO6391.getName(langcd) : langcd) : currentLangValue;
      var addTag = function(evt) {
        const langs = evt.target.value.split(',').map(elem => ISO6391.getCode(elem.trim()) ? ISO6391.getCode(elem.trim()) : elem.trim())
        if (currentLangValue) {
          args.onUpdateBody(currentLangBody, {
            language: langs
          });
        } else { 
          args.onAppendBody({
            language: langs
          });
        }
      }

      var createInput = function() {
        var div = document.createElement('div');
        div.className = "r6o-autocomplete"
        var input = document.createElement('input');
        input.placeholder = 'Add language. Use comma for multiple languages'
        
        input.addEventListener('change', addTag); 
        var datalist = document.createElement('datalist');
        datalist.id = 'languages'
        var langs = ISO6391.getAllNativeNames().concat(ISO6391.getAllNames());
        langs = _.uniq(langs);
        for (var i=0; i<langs.length; i++){
          const option = document.createElement('option');
          option.value = langs[i];
          datalist.appendChild(option)
        }
        div.appendChild(input)
        div.appendChild(datalist)
        input.setAttribute('list','languages')
        input.setAttribute('type','text')
        input.setAttribute('multiple','')
        return div;
      }

      var container = document.createElement('div');
      container.className = 'r6o-widget r6o-tag';
      
      var lang = createInput();
      container.appendChild(lang);

      return container;
    },
    setOpacity: function(layerdata, event=false){
      var opacity = event ? event.target.value/100 : layerdata.opacity > 0 ? 0 : 1;
      layerdata.osdtile.setOpacity(opacity);
      layerdata.opacity = opacity;
      var checked = opacity != 0 ? true : false;
      layerdata.checked = checked;
    },
    getManifest: function(manifest) {
      this.currentmanifest = manifest;
      this.showManThumbs = true;
      var vue = this;
      jQuery.ajax({
        url: manifest,
        type: "GET",
        success: function(data) {
          var images = [];
          const manifestdata = data.sequences[0].canvases;
          for (var i=0; i<manifestdata.length; i++){
            var tiles = [];
            var canvas = manifestdata[i]['id'] ? manifestdata[i]['id'] : manifestdata[i]['@id'];
            var thumb = manifestdata[i]['thumbnail'] ? manifestdata[i]['thumbnail'] : manifestdata[i]['images'][0]['resource']
            thumb = thumb['id'] ? thumb['id'] : thumb['@id'] ? thumb['@id'] : thumb;  
            const resource = manifestdata[i]['images'].map(elem => elem['resource']);
            for (var j=0; j<resource.length; j++){
              const resourceitem = resource[j];
              const thumb = resourceitem['id'] ? resourceitem['id'] : resourceitem['@id'];
              const id = resourceitem['service']['id'] ? resourceitem['service']['id'] : resourceitem['service']['@id'] + '/info.json';
              const opacity = j == 0 ? 1 : 0;
              const checked = j == 0 ? true : false;
              console.log(resource)
              tiles.push({'id': id, 'label': resourceitem['label'], 
                thumbnail: thumb.replace('/full/0', '/100,/0'), 'opacity': opacity,
                'checked': checked
              })
            }
            thumb = thumb.replace('/full/0', '/100,/0')
            images.push({'image': thumb, 'canvas': canvas, 'tiles': tiles})
          }
          vue.manifestdata = images
        },
        error: function() {
          returnError();
        }
      });
    },
    toggle: function() {
      this.drawtool = this.drawtool == 'rectangle' ? 'polygon' : 'rectangle';
      const drawtool = this.drawtool.replace('angle', '');
      this.anno.setDrawingTool(drawtool);
    },
    addListeners: function() {
      // Attach handlers to listen to events
      var vue = this;
      this.anno.on('createAnnotation', function(annotation) {
        var target = vue.inputurl;
        if (vue.currentmanifest){
          annotation.target['dcterms:isPartOf'] = {
            "id": vue.currentmanifest,
            "type": "Manifest"
          }
          target = vue.canvas;
        }
        annotation.body[0].rights = 'Placeholderforrights'
        annotation.target.id = target;
        var senddata = {'json': annotation }
        vue.write_annotation(senddata, 'create', annotation)
      });
    
      this.anno.on('updateAnnotation', function(annotation) {
        var senddata = {'json': annotation,'id': annotation['id'], 'order': annotation['order']}
        vue.write_annotation(senddata, 'update')
      });

      this.anno.on('deleteAnnotation', function(annotation) {
        var senddata = {'id': annotation['id'] }
        vue.write_annotation(senddata, 'delete')
      });
    },
    write_annotation: function(senddata, method, annotation=false) {
      jQuery.ajax({
        url: `/${method}_annotations/`,
        type: "POST",
        dataType: "json",
        data: JSON.stringify(senddata),
        contentType: "application/json; charset=utf-8",
        success: function(data) {
          if (annotation) {
            annotation['id'] = data['id']
            annotation['order'] = data['order'];
          }
        },
        error: function() {
          returnError();
        }
      });
    } 
  }
})

var app = new Vue({
  el: '#app'
})
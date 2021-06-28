const annoview = Vue.component('annoview', {
  template: `<div>
  <div class="manifestimages">
    <div v-for="manifest in existing['manifests']">
      <button class="linkbutton" v-on:click="getManifest(manifest)">
        {{manifest}}
      </button>
    </div>
    <div v-for="image in existing['images']">
      <button class="linkbutton" v-on:click="inputurl = image; currentmanifest='';loadAnno()">
        {{image}}
      </button>
    </div>
  </div>
  <div>
    <label for="manifesturl">Manifest</label>
    <input id="manifesturl" v-on:change="getManifest(currentmanifest)" v-model="currentmanifest"></input>
    <button v-on:click="showManThumbs = !showManThumbs" v-if="currentmanifest">
      <span v-if="showManThumbs">Hide</span><span v-else>Show</span> Manifest Thumbnails
    </button>
  </div>
  <div class="manifestthumbs" v-show="showManThumbs && currentmanifest">
    <div v-if="manifestdata == 'failure'"><i class="fas fa-exclamation-triangle"></i> {{currentmanifest}} failed to load! Please check your manifest.</div>
    <div v-else-if="manifestdata.length == 0">Loading...</div>
    <div v-else v-for="item in manifestdata" style="display: inline-block;">
      <button v-on:click="manifestLoad(item)" class="linkbutton">
        <img :src="item['image']" style="max-width:100px;padding:5px;" alt="manifest thumbnail">
      </button>
    </div>
  </div>
  <div>
    <label for="imageurl">Image URL</label>
    <input id="imageurl" v-on:change="currentmanifest = '';loadAnno()" v-model="inputurl"></input>
  </div>
  <div class="drawingtools" v-if="anno">
    <label for="current-tool">Current Annotation drawing shape: </label>
    <div id="current-tool" v-for="drawtool in drawtools" v-on:change="updateDrawTool()">
      <label class="toolbutton" v-bind:for="drawtool.name">
        <input type="radio" v-bind:id="drawtool.name" v-bind:name="drawtool.name" v-bind:value="drawtool.name" v-model="currentdrawtool">
        <span>{{drawtool.label}}</span></label>
    </div>
    <p>
      <b>Hold <code>SHIFT</code> while clicking and dragging the mouse to create a new annotation.
      <br>
      To stop Polygon annotation selection double click.</b>
    </p>
  </div>
  <div class="layers gridparent">
    <div v-for="item in alltiles" v-if="alltiles.length > 1">
      <input type="checkbox" class="tagscheck" v-on:click="setOpacity(item)" v-model="item.checked">
      <span v-html="item.label"></span>
      <div class="slidecontainer">Opacity: <input v-on:change="setOpacity(item, $event)" type="range" min="0" max="100" v-bind:value="item.opacity*100" class="slider"></div>
      <img :src="item['thumbnail']" style="max-width:100px;padding:5px;"  alt="tile thumbnail">
    </div>
  </div>
  <div id="openseadragon1" v-bind:class="{'active' : inputurl !== ''}"></div>
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
      drawtools: [{'name': 'rect', 'label':'Rectangle'},{'name': 'polygon', 'label':'Polygon'}],
      currentdrawtool: 'rect',
      anno: '',
      viewer: '',
      manifestdata: '',
      currentmanifest: '',
      showManThumbs: true,
      canvas: '',
      alltiles: []
  	}
  },
  mounted() {
    const params = new URLSearchParams(window.location.search);
    const manifesturl = params.get('manifesturl');
    const imageurl = params.get('imageurl');
    if (manifesturl){
      this.currentmanifest = manifesturl;
      this.getManifest(manifesturl, params.get('canvas'));
    }
    if (imageurl) {
      this.inputurl = imageurl;
      this.loadAnno();
    }
  },
  methods: {
    manifestLoad: function(item) {
      this.canvas = item['canvas'];
      this.inputurl = item['tiles'][0]['id'];
      this.alltiles = item['tiles'];
      this.loadAnno()
      if (this.manifestdata.length == 1){
        this.showManThumbs = false;
      }
    },
    loadAnno: function() {
      document.getElementById('openseadragon1').innerHTML = '';
      var tilesources = [this.inputurl]
      const imgext = /(.jpeg|.png|.jpg|.bmp|.gif|.tif|.tiff|.apng|.avif|.jfif|.pjpeg|.pjp|.svg|.webp|.ico|.cur)/gm;
      if (imgext.test(this.inputurl.toLowerCase())) {
        tilesources = {
            type: "image",
            url: this.inputurl
        }
        this.alltiles = []
      }
      var viewer = OpenSeadragon({
        id: "openseadragon1",
        prefixUrl: "/assets/openseadragon/images/",
        tileSources: tilesources
      });
      this.viewer = viewer;
      var vue = this;
      viewer.addHandler('open', function(){
        if (vue.alltiles.length > 1){
          for (var k=0; k<vue.alltiles.length; k++){
            vue.alltiles[k]['order'] = k;
            if (k > 0){
              vue.setLayers(vue.alltiles[k], k)
            } else {
              vue.alltiles[k]['osdtile'] = vue.viewer.world.getItemAt(0);
            }
          }
        }
      })

      var id = this.inputurl;
      //localStorage.setItem('')
      // Initialize the Annotorious plugin
      var existing = this.currentmanifest ? this.filepaths[this.canvas] : this.filepaths[this.inputurl];
      this.anno = OpenSeadragon.Annotorious(viewer, 
        { image: 'openseadragon1',
          allowEmpty: true,
          widgets: [ 
                    {widget: 'COMMENT', editable: 'MINE_ONLY', purposeSelector: true},
                    {widget: 'TAG', vocabulary: vue.tags}
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
    setLayers: function(layer, position){
      var vue = this;
      const xywh = layer['xywh'];
      var rect = this.viewer.world.getItemAt(0).imageToViewportRectangle(parseInt(xywh[0]), parseInt(xywh[1]), parseInt(xywh[2]), parseInt(xywh[3]));
      tiledimage = this.viewer.addTiledImage({
        tileSource: layer['id'],
        opacity: layer['opacity'],
        x: rect.x,
        y: rect.y,
        width: rect.width,
        success: function (obj) {
          vue.alltiles[position]['osdtile'] = obj.item;
        }
      });
    },
    setOpacity: function(item, event){
      var opacity = event ? event.target.value/100 : item.opacity > 0 ? 0 : 1;
      item['osdtile'].setOpacity(opacity)
      item.opacity = opacity;
      var checked = opacity != 0 ? true : false;
      item.checked = checked;
    },
    getManifest: function(manifest, loadcanvas=false) {
      this.currentmanifest = manifest;
      this.showManThumbs = true;
      this.manifestdata = [];
      var vue = this;
      jQuery.ajax({
        url: manifest,
        type: "GET",
        success: function(data) {
          var images = [];
          const manifestdata = data.sequences ? data.sequences[0].canvases : data.items;
          if (!manifestdata) {
            vue.manifestdata = 'failure';
            return;
          }
          for (var i=0; i<manifestdata.length; i++){
            var tiles = [];
            var canvas = vue.getId(manifestdata[i]);
            var thumb = manifestdata[i]['thumbnail'] ? manifestdata[i]['thumbnail'] : manifestdata[i]['images'][0]['resource']
            thumb = thumb['service'] ? thumb['service'] : thumb;
            thumb = vue.getId(thumb);
            if (thumb.indexOf('.jpg') == -1){
              thumb += '/full/100,/0/default.jpg'
            }
            const manifestimages = manifestdata[i]['images'];
            for (var j=0; j<manifestimages.length; j++){
              const resourceitem = manifestimages[j]['resource'];
              const thumb = vue.getId(resourceitem);
              const id = resourceitem['service']['id'] ? resourceitem['service']['id'] : resourceitem['service']['@id'] + '/info.json';
              const opacity = j == 0 ? 1 : 0;
              const checked = j == 0 ? true : false;
              const resourceid = manifestimages[j].resource ? vue.getId(manifestimages[j].resource) : '';
              var xywh = resourceid && resourceid.constructor.name === 'String' && resourceid.indexOf('xywh') > -1 ? resourceid : vue.on_structure(manifestimages[j]) && vue.on_structure(manifestimages[j])[0].constructor.name === 'String' ? vue.on_structure(manifestimages[j])[0] : '';
              xywh = xywh ? xywh.split("xywh=").slice(-1)[0].split(",") : xywh;
              tiles.push({'id': id, 'label': resourceitem['label'], 
                thumbnail: thumb.replace('/full/0', '/100,/0'), 'opacity': opacity,
                'checked': checked, 'xywh': xywh
              })
            }
            thumb = thumb.replace('/full/0', '/100,/0')
            images.push({'image': thumb, 'canvas': canvas, 'tiles': tiles})
            if (loadcanvas == canvas) {
              vue.manifestLoad({'image': thumb, 'canvas': canvas, 'tiles': tiles})
            }
          }
          vue.manifestdata = images;
        },
        error: function(err) {
          vue.manifestdata = 'failure';
          console.log(err)
        }
      });
    },
    getId: function(iddata) {
      return iddata['id'] ? iddata['id'] : iddata['@id'] ? iddata['@id'] : iddata;
    },
    on_structure: function(manifest){
      if (!manifest['on'] || typeof manifest['on'] === 'undefined'){
        return undefined;
      } else if (manifest['on'].constructor.name === 'Array'){
        return manifest['on'];
      } else {
        return [manifest['on']];
      }
    },
    updateDrawTool: function() {
      this.anno.setDrawingTool(this.currentdrawtool);
    },
    addManifestAnnotation: function(annotation){
      var target = this.inputurl;
      if (this.currentmanifest){
        annotation.target['dcterms:isPartOf'] = {
          "id": this.currentmanifest,
          "type": "Manifest"
        }
        target = this.canvas;
      }
      annotation.target.source = target;
      return annotation;
    },
    addListeners: function() {
      // Attach handlers to listen to events
      var vue = this;
      this.anno.on('createAnnotation', function(annotation) {
        var annotation = vue.addManifestAnnotation(annotation);
        var senddata = {'json': annotation }
        vue.write_annotation(senddata, 'create', annotation)
      });
    
      this.anno.on('updateAnnotation', function(annotation) {
        var annotation = vue.addManifestAnnotation(annotation);
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
        error: function(err) {
          console.log(err)
          alert(err.responseText)
        }
      });
    }
  }
})

var app = new Vue({
  el: '#app'
})
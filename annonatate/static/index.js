const annoview = Vue.component('annoview', {
  template: `<div>
  <div v-if="isMobile && anno" style="position:fixed;right: 8px;">
    <button v-on:click="enableDrawing(!drawingenabled)" style="width: 50px;height:50px;border-radius: 10px;">
      <span class="fa-stack fa-2x">
        <i class="fas fa-pencil-alt fa-stack-1x"></i>
        <i v-if="!drawingenabled" class="fas fa-slash fa-stack-1x" style="color:Tomato"></i>
      </span>
    </button>
  </div>
  <div class="manifestimages">
    <div v-for="manifest in existing['manifests']">
      <button v-if="manifest" class="linkbutton" v-on:click="getManifest(manifest)">
        • {{manifest}}
      </button>
    </div>
    <div v-for="image in existing['images']">
      <button v-if="image" class="linkbutton" v-on:click="inputurl = image; ingesturl = image; loadImage()">
        • {{image}}
      </button>
    </div>
  </div>
  <div>
    <label for="ingesturl">Manifest or Image URL: </label>
    <input id="ingesturl" v-on:change="getManifest(ingesturl)" v-model="ingesturl"></input>
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
  <div class="drawingtools" v-if="anno">
    <label for="current-tool">Current Annotation drawing shape: </label>
    <div id="current-tool" v-for="drawtool in drawtools" v-on:change="updateDrawTool()">
      <label class="toolbutton" v-bind:for="drawtool.name">
        <input type="radio" v-bind:id="drawtool.name" v-bind:name="drawtool.name" v-bind:value="drawtool.name" v-model="currentdrawtool">
        <span>{{drawtool.label}}</span></label>
    </div>
    <div v-if="isMobile">
      <b>Tap and drag to create new annotation
      <span v-if="currentdrawtool == 'polygon'">
        <br>
        To stop Polygon annotation selection long touch the screen.
      </span>
      </b>
    </div>
    <div v-else>
      <b>Hold <code>SHIFT</code> while clicking and dragging the mouse to create a new annotation.
      <span v-if="currentdrawtool == 'polygon'">
        <br>
        To stop Polygon annotation selection double click.
      </span>
      </b>
    </div>
  </div>
  <div v-else>
    <p>
    The links above are a list of demo images you can click on and they will be loaded into the annotation viewer. These links can be edited on the <a href="/profile?tab=data">profile page</a>.<br>
    You can also add in your own link to an image or <a href="https://iiif.io" target="_blank">IIIF manfiest</a> into the box next to "Manifest or Image URL".
    </p>
  </div>
  <div class="layers gridparent" v-if="alltiles.length > 1">
    <div v-for="item in alltiles">
      <input type="checkbox" class="tagscheck" v-on:click="setOpacity(item)" v-model="item.checked">
      <span v-html="item.label"></span>
      <div class="slidecontainer">Opacity: <input v-on:change="setOpacity(item, $event)" type="range" min="0" max="100" v-bind:value="item.opacity*100" class="slider"></div>
      <img :src="item['thumbnail']" style="max-width:100px;padding:5px;"  alt="tile thumbnail">
    </div>
  </div>
  <div v-if="title" style="font-weight:900">{{title[0]['value']}}: 
  <span v-if="alltiles.length > 0 && alltiles[0]['label']">{{alltiles[0]['label']}}</span>
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
      drawtools: [],
      currentdrawtool: 'rect',
      anno: '',
      viewer: '',
      manifestdata: '',
      currentmanifest: '',
      showManThumbs: false,
      canvas: '',
      title: '',
      isMobile: false,
      alltiles: [],
      drawingenabled: false,
      ingesturl: ''
  	}
  },
  mounted() {
    this.isMobile = /Mobi/.test(navigator.userAgent);
    console.log(navigator.userAgent)
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
    loadImage: function() {
      this.currentmanifest='';
      this.title = '';
      this.loadAnno();
    },
    manifestLoad: function(item) {
      this.canvas = item['canvas'];
      this.inputurl = item['tiles'][0]['id'];
      this.alltiles = item['tiles'];
      this.loadAnno()
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
          messages: { "Ok": "Save" },
          allowEmpty: true,
          widgets: [ 
                    {widget: 'COMMENT', editable: 'MINE_ONLY', purposeSelector: true},
                    {widget: 'TAG', vocabulary: vue.tags}
                  ]});
    // Load annotations in W3C WebAnnotation format
      if (existing){
        var annotation = this.anno.setAnnotations(existing); 
      }
      Annotorious.SelectorPack(this.anno);
      this.drawtools = []
      const drawingtools = this.anno.listDrawingTools();
      for (var dt=0; dt<drawingtools.length; dt++){
        const name = drawingtools[dt];
        const label = name == 'rect' ? 'Rectangle' : name.charAt(0).toUpperCase() + name.slice(1);
        this.drawtools.push({'name': name, 'label': label})
      }
      this.addListeners();
      this.enableDrawing(this.drawingenabled);
      this.anno.setAuthInfo({
        id: this.userinfo["id"],
        displayName: this.userinfo["value"]
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
      this.manifestdata = [];
      this.ingesturl = manifest;
      var vue = this;
      jQuery.ajax({
        url: manifest,
        type: "GET",
        success: function(data) {
          if (data.constructor.name == 'String' || data['@context'] && data['@context'].indexOf('presentation') == -1){
            vue.inputurl = manifest;
            vue.currentmanifest = '';
            vue.loadImage();
          }
          var images = [];
          var m = manifesto.parseManifest(data);
          vue.title = m.getLabel();
          const sequence = m.getSequenceByIndex(0);
          const manifestdata = sequence.getCanvases();
          if (!manifestdata) {
            vue.manifestdata = 'failure';
            return;
          }
          for (var i=0; i<manifestdata.length; i++){
            var tiles = [];
            var canvas = manifestdata[i].id;
            var thumb = manifestdata[i].getThumbnail();
            thumb ? thumb = vue.getId(thumb['__jsonld']) : ''
            var manifestimages = manifestdata[i]['__jsonld']['images'] ? manifestdata[i]['__jsonld']['images'] : manifestdata[i]['__jsonld']['items'];
            manifestimages = manifestimages[0]['items'] ? manifestimages[0]['items'] : manifestimages;
            for (var j=0; j<manifestimages.length; j++){
              const resourceitem = manifestimages[j]['resource'] ? manifestimages[j]['resource'] : manifestimages[j]['body'];
              const imagethumb = vue.getId(resourceitem);
              if (!thumb){
                thumb = imagethumb;
              }
              
              var id = resourceitem['service'] && resourceitem['service']['id'] ? resourceitem['service']['id'] : resourceitem['service'] && resourceitem['service']['@id']  ? resourceitem['service']['@id'] + '/info.json' : resourceitem['service'] ? resourceitem['service'][0]['id'] : resourceitem['id'];
              id = resourceitem['service'] ? id.split('/info')[0] + '/info.json' : id;
              const opacity = j == 0 ? 1 : 0;
              const checked = j == 0 ? true : false;
              const resourceid = resourceitem ? vue.getId(resourceitem) : '';
              var xywh = resourceid && resourceid.constructor.name === 'String' && resourceid.indexOf('xywh') > -1 ? resourceid : vue.on_structure(manifestimages[j]) && vue.on_structure(manifestimages[j])[0].constructor.name === 'String' ? vue.on_structure(manifestimages[j])[0] : '';
              xywh = xywh ? xywh.split("xywh=").slice(-1)[0].split(",") : xywh;
              const tilelabel = manifestdata[i].getLabel().length > 0 ? manifestdata[i].getLabel()[0]['value'] : ""
              tiles.push({'id': id, 'label': tilelabel,
                thumbnail: imagethumb.replace('/full/0', '/100,/0'), 'opacity': opacity,
                'checked': checked, 'xywh': xywh
              })
            }
            thumb = thumb.replace('/full/0', '/100,/0')
            images.push({'image': thumb, 'canvas': canvas, 'tiles': tiles})
            if (loadcanvas == canvas) {
              vue.manifestLoad({'image': thumb, 'canvas': canvas, 'tiles': tiles})
            }
          }
          if (images.length > 1){
            vue.showManThumbs = true;
          }
          vue.manifestdata = images;
          if (!loadcanvas){
            vue.manifestLoad(images[0]);
          }
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
    enableDrawing: function(enable=true){
      if (this.isMobile){
        this.drawingenabled = enable;
        this.anno.setDrawingEnabled(enable);
      }
    },
    addListeners: function() {
      // Attach handlers to listen to events
      var vue = this;
      this.anno.on('cancelSelected', function() {
        vue.enableDrawing();
      });
      this.anno.on('createAnnotation', function(annotation) {
        var annotation = vue.addManifestAnnotation(annotation);
        vue.write_annotation(annotation, 'create');
        vue.enableDrawing();
      });
    
      this.anno.on('updateAnnotation', function(annotation) {
        var annotation = vue.addManifestAnnotation(annotation);
        vue.write_annotation(annotation, 'update');
        vue.enableDrawing();
      });

      this.anno.on('deleteAnnotation', function(annotation) {
        vue.write_annotation(annotation, 'delete');
        vue.enableDrawing();
      });
    },
    write_annotation: function(annotation, method) {
      var senddata = {'json': annotation, 'canvas': annotation['target']['source'], 'id': annotation['id']}
      if (annotation['order']){
        senddata['order'] = annotation['order'];
      }
      jQuery.ajax({
        url: `/${method}_annotations/`,
        type: "POST",
        dataType: "json",
        data: JSON.stringify(senddata),
        contentType: "application/json; charset=utf-8",
        success: function(data) {
          if (annotation && method != 'delete') {
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
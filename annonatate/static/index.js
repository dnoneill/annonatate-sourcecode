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
  <div style="position:absolute;right: 10px;top: 52px;">
    Switch to <a v-on:click="updateIsMobile()" class="linkbutton">{{this.isMobile ==true ? 'Desktop' : 'Mobile' }} view.</a><br>
  </div>
  <h2 style="margin:0px" v-on:click="manimageshown = !manimageshown">Image List <i class="fas" v-bind:class="[manimageshown ? 'fa-caret-up' : 'fa-caret-down']"></i></h2>
  <div v-if="manimageshown">
    <div>This is a list of images and manifests you have uploaded. You can change these via <a href="profile/?tab=data">settings.</a></div>
    <div class="manifestimages" :class="{'noanno' : !anno}">
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
  </div>
  <div class="ingesturlcontainer" :class="{'noanno' : !anno}">
    <label for="ingesturl">Manifest or Image URL: </label>
    <input id="ingesturl" v-on:change="getManifest(ingesturl)" v-model="ingesturl"></input>
    <button v-on:click="showManThumbs = !showManThumbs" v-if="currentmanifest">
      <span v-if="showManThumbs">Hide</span><span v-else>Show</span> Manifest Thumbnails
    </button>
  </div>
  <div class="manifestthumbs" v-show="showManThumbs && currentmanifest">
    <div v-if="manifestdata == 'failure'"><i class="fas fa-exclamation-triangle"></i> {{currentmanifest}} failed to load! Please check your manifest.</div>
    <div v-else-if="manifestdata.length == 0">Loading...</div>
    <div v-else v-for="(item, index) in manifestdata" class="manifestimagelist">
      <button v-on:click="currentposition = index;manifestLoad(item)" class="linkbutton">
        <img :src="item['image']" alt="manifest thumbnail">
        <div class="manthumblabel">
        {{item['tiles'][0]['label']}}
        </div>
      </button>
    </div>
  </div>
  <div v-if="isMobile && anno">
      <b>Click pencil icon (<i class="fas fa-pencil-alt"></i>) so there is no slash through it.<br>
      Then tap and drag to create new annotation.
      <span v-if="currentdrawtool == 'polygon'">
        <br>
        To stop Polygon annotation selection long touch the screen.
      </span>
      </b>
    </div>
    <div v-else-if="anno">
      <b>Hold <code>SHIFT</code> while clicking and dragging the mouse to create a new annotation.
      <span v-if="currentdrawtool == 'polygon'">
        <br>
        To stop Polygon annotation selection double click.
      </span>
      </b>
    </div>
  <div v-if="title" style="font-weight:900">
  <span v-html="title[0]['value'] + ':'"></span>
  <span v-if="alltiles.length > 0 && alltiles[0]['label']">{{alltiles[0]['label']}}</span>
  </div>
  <div v-else>
    <p style="background:#e7e7e7; padding: 10px">
    Welcome to Annonatate. A platform for annotating images.<br>
    Click on a link in the <span style="color: #61177C">purple</span> box or add a URL to the <span style="color: #004EC2">blue</span> box to start annotating images.
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
  <div class="drawingtools" v-if="anno">
    <div id="current-tool" v-for="drawtool in drawtools" v-on:change="updateDrawTool()">
      <label class="toolbutton" v-bind:for="drawtool.name">
        <input type="radio" v-bind:id="drawtool.name" v-bind:name="drawtool.name" v-bind:value="drawtool.name" v-model="currentdrawtool">
        <span v-html="drawtool.label"></span></label>
    </div>
    <button v-bind:title="annosvisible ? 'Hide Annotations' : 'Show Annotations'" v-on:click="setVisible()" style="height: 22px; width: 35px; font-size: 15px;">
      <i class="fas fa-eye" v-if="!annosvisible"></i>
      <i class="fas fa-eye-slash" v-else-if="annosvisible"></i>
    </button>
  </div>
  <a class="prev prevnext" v-on:click="next('prev')" v-if="manifestdata && manifestdata[currentposition-1]">&lt;</a>
  <a class="next prevnext" v-on:click="next('next')" v-if="manifestdata && manifestdata[currentposition+1]">&gt;</a>
  <div id="openseadragon1" v-bind:class="{'active' : inputurl !== ''}"></div>
  </div>
  `,
  props: {
    'existing': Object,
    'filepaths': Object,
    'userinfo': Object,
    'tags': Array,
    'originurl': String,
    'updatepage': String
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
      ingesturl: '',
      fragmentunit: 'pixel',
      currentposition: 0,
      widgets: ['comment-with-purpose','tag','geotagging'],
      draftannos: [],
      annosvisible: true, 
      manimageshown: true
  	}
  },
  mounted() {
    this.isMobile = /Mobi/.test(navigator.userAgent);
    if (this.existing.settings && this.existing.settings.widgets){
      this.widgets = this.existing.settings.widgets.split(",").map(elem => elem.trim());
    }
    console.log(navigator.userAgent)
    const params = new URLSearchParams(window.location.search);
    const mobileparam = params.get('view');
    if (mobileparam) {
      this.isMobile = mobileparam == 'desktop' ? false : true;
    }
    const manifesturl = params.get('manifesturl');
    const imageurl = params.get('imageurl');
    const mode = params.get('mode');
    this.checkErrorAnnos();
    if (mode){
      this.fragmentunit = mode;
    }
    if (manifesturl){
      this.currentmanifest = manifesturl;
      this.getManifest(manifesturl, params.get('canvas'));
    }
    if (imageurl) {
      this.inputurl = imageurl;
      this.loadAnno();
    }
    if (this.updatepage){
      this.setUpdate();
    }
  },
  methods: {
    setUpdate: function() {
      setInterval(() => {
        var vue = this;
        if (this.anno) {
          jQuery.ajax({
            url: "/update",
            type: "GET",
            success: function(data) {
              vue.filepaths = data;
              const selected = vue.anno.getSelected();
              if (!selected || (selected && selected['type'] != 'Selection')){
                vue.anno.clearAnnotations();
                vue.annoLoadOSD(true);
                if (selected){
                  vue.anno.selectAnnotation(selected['id']);
                }
              }
            }
          });
        }
      }, "60000")
    },
    next: function(nextorprev) {
      this.currentposition = nextorprev == 'next' ? this.currentposition + 1 : this.currentposition -1;
      this.manifestLoad(this.manifestdata[this.currentposition])
    },
    checkErrorAnnos: function(){
      const erroranno = JSON.parse(localStorage.getItem('erranno'));
      if (erroranno) {
        for (var ea=0; ea<erroranno.length; ea++){
          const annotation = erroranno[ea]['annotation'];
          this.write_annotation(annotation, erroranno[ea]['method']);
        }
        localStorage.removeItem('erranno');
      }
    },
    updateIsMobile: function() {
      const switchUnit = this.isMobile ? 'desktop' : 'mobile' ;
      this.updateUrl('view', switchUnit);
    },
    updateUnit: function() {
      const switchUnit = this.fragmentunit =='pixel' ? 'percent' : 'pixel' ;
      this.updateUrl('mode', switchUnit);
    },
    updateUrl: function(param, variable) {
      var url = new URL(location.href);
      if (url.searchParams.get(param)){
        url.searchParams.set(param, variable);
      } else{
        url.searchParams.append(param, variable);
      }
      window.location.href = url.toString();
    },
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
    buildWidgetList: function() {
      var widgets = []
      var widgettypes =
        {'comment-with-purpose': {widget: 'COMMENT', editable: 'MINE_ONLY', purposeSelector: true},
        'comment': {widget: 'COMMENT', editable: 'MINE_ONLY'},
        'tag': {widget: 'TAG', vocabulary: this.tags},
        'geotagging': {widget: recogito.GeoTagging({defaultOrigin: [ 48, 16 ]})}}
      for (var wi=0; wi<this.widgets.length; wi++){
        widgets.push(widgettypes[this.widgets[wi]])
      }
      return widgets;
    },
    annoLoadOSD: function(clearold=false) {
      var existing = this.currentmanifest ? this.filepaths[this.canvas] : this.filepaths[this.inputurl];
    // Load annotations in W3C WebAnnotation format
      if (existing){
        const clean = existing.map(elem => JSON.parse(JSON.stringify(elem).replace("pct:", "percent:")))
        var annotation = this.anno.setAnnotations(clean);
      }

    },
    setVisible: function() {
      this.annosvisible = !this.annosvisible;
      this.anno.setVisible(this.annosvisible);
    },
    loadAnno: function() {
      document.getElementById('openseadragon1').innerHTML = '';
      var tilesources = [this.inputurl]
      const imgext = /(.jpeg|.png|.jpg|.bmp|.gif|.tif|.tiff|.apng|.avif|.jfif|.pjpeg|.pjp|.svg|.webp|.ico|.cur)/gm;
      if (imgext.test(this.inputurl.toLowerCase()) && this.inputurl.indexOf('info.json') == -1) {
        tilesources = {
            type: "image",
            url: this.inputurl
        }
        this.alltiles = []
      }
      var viewer = OpenSeadragon({
        id: "openseadragon1",
        prefixUrl: "/assets/openseadragon/images/",
        tileSources: tilesources,
        zoomPerScroll: 1,
        navigationControlAnchor: OpenSeadragon.ControlAnchor.TOP_RIGHT
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
      // Initialize the Annotorious plugin
      var widgets = this.buildWidgetList();
      this.anno = OpenSeadragon.Annotorious(viewer, 
        { image: 'openseadragon1',
          messages: { "Ok": "Save" },
          fragmentUnit: this.fragmentunit,
          allowEmpty: true,
          widgets: widgets});
    // Load annotations in W3C WebAnnotation format
      this.annoLoadOSD();
      Annotorious.SelectorPack(this.anno);
      Annotorious.TiltedBox(this.anno);
      this.drawtools = []
      const drawingtools = this.anno.listDrawingTools();
      for (var dt=0; dt<drawingtools.length; dt++){
        const name = drawingtools[dt];
        var cleanname = name.replaceAll("annotorious", "").replaceAll("-", " ").trim();
        const label = name == 'rect' ? 'Rectangle' : cleanname.charAt(0).toUpperCase() + cleanname.slice(1);
        this.drawtools.push({'name': name, 'label': label})
      }
      this.drawtools = this.drawtools.sort((a, b) => (a.label > b.label) ? 1 : -1)
      this.addListeners();
      this.enableDrawing(this.drawingenabled);
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
      this.manifestdata = [];
      this.ingesturl = manifest;
      var vue = this;
      jQuery.ajax({
        url: manifest,
        type: "GET",
        success: function(data) {
          const context = data['@context'] && Array.isArray(data['@context']) ? data['@context'].join("") : data['@context'];
          if (data.constructor.name == 'String' || context && context.indexOf('presentation') == -1){
            vue.inputurl = manifest;
            vue.currentmanifest = '';
            vue.loadImage();
          }
          var images = [];
          var m = manifesto.parseManifest(data);
          vue.title = m ? m.getLabel() : "";
          const sequence = m.getSequenceByIndex(0);
          const manifestdata = sequence.getCanvases();
          if (!manifestdata) {
            vue.manifestdata = 'failure';
            return;
          }
          for (var i=0; i<manifestdata.length; i++){
            var tiles = [];
            var manifesthumb = m.getThumbnail();
            var size = manifesthumb && manifesthumb.id && manifesthumb.id.indexOf('full') > -1 ? manifesthumb.id.split('full/').slice(-1)[0].split('/0')[0] : '100,'
            var canvas = manifestdata[i].id;
            var thumb = manifestdata[i].getThumbnail();
            thumb ? thumb = vue.getId(thumb['__jsonld']) : ''
            var manifestimages = manifestdata[i]['__jsonld']['images'] ? manifestdata[i]['__jsonld']['images'] : manifestdata[i]['__jsonld']['items'];
            manifestimages = manifestimages[0]['items'] ? manifestimages[0]['items'] : manifestimages;
            var fullvalue = m.context.indexOf('3') > -1 ? 'max' : 'full';
            for (var j=0; j<manifestimages.length; j++){
              var resourceitem = manifestimages[j]['resource'] ? manifestimages[j]['resource'] : manifestimages[j]['body'] ? manifestimages[j]['body'] :  Array.isArray(manifestimages[j]['items']) ? manifestimages[j]['items'][0] : manifestimages[j]['items'];
              const imagethumb = vue.getId(resourceitem);
              if (!thumb){
                thumb = imagethumb;
              }
              const resourceservice = resourceitem['service'] && Array.isArray(resourceitem['service']) ? resourceitem['service'][0] : resourceitem['service'];
              var id = resourceservice ? vue.trimCharacter(vue.getId(resourceservice), '/') + '/info.json' : resourceitem['id'];
              id = resourceservice ? vue.trimCharacter(id.split('/info')[0], '/') + '/info.json' : id;
              const opacity = j == 0 ? 1 : 0;
              const checked = j == 0 ? true : false;
              const resourceid = resourceitem ? vue.getId(resourceitem) : '';
              var xywh = resourceid && resourceid.constructor.name === 'String' && resourceid.indexOf('xywh') > -1 ? resourceid : vue.on_structure(manifestimages[j]) && vue.on_structure(manifestimages[j])[0].constructor.name === 'String' ? vue.on_structure(manifestimages[j])[0] : '';
              xywh = xywh ? xywh.split("xywh=").slice(-1)[0].split(",") : xywh;
              const getLabel = manifestdata[i].getLabel();
              const tilelabel = getLabel && getLabel.length > 0 ? getLabel[0]['value'] : ""
              tiles.push({'id': id, 'label': tilelabel,
                thumbnail: imagethumb.replace(`/${fullvalue}/0`, `/${size}/0`), 'opacity': opacity,
                'checked': checked, 'xywh': xywh
              })
            }
            thumb = thumb ? thumb.replace(`/${fullvalue}/0`, `/${size}/0`) : thumb;
            images.push({'image': thumb, 'canvas': canvas, 'tiles': tiles})
            if (loadcanvas == canvas) {
              this.currentposition = i;
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
    trimCharacter: function(word, char) {
      return word.slice(-1)[0] == char ? word.slice(0, -1) : word;
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
      annotation['motivation'] = 'commenting';
      if (this.currentmanifest){
        annotation.target['dcterms:isPartOf'] = {
          "id": this.currentmanifest,
          "type": "Manifest"
        }
        target = this.canvas;
      }
      annotation.target.source = target;
      annotation = this.cleanPixel(annotation);
      return annotation;
    },
    cleanPixel: function(annotation) {
      var annoString = JSON.stringify(annotation);
      annoString = annoString.replace('xywh=pixel:', 'xywh=').replace('xywh=percent:', 'xywh=pct:')
      return JSON.parse(annoString);
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
        vue.enableDrawing(vue.drawingenabled);
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
      this.anno.on('selectAnnotation', function(annotation, element) {
        if (vue.draftannos.indexOf(annotation['id']) > -1) {
          if (document.getElementsByClassName('delete-annotation').length> 0){
            document.getElementsByClassName('delete-annotation')[0].style.display = 'none';
          }
        }
      });
    },
    write_annotation: function(annotation, method) {
      var vue = this;
      var senddata = {'json': annotation, 'canvas': annotation['target']['source'], 'id': annotation['id']}
      if (annotation['order']){
        senddata['order'] = annotation['order'];
      }
      const key = senddata['json']['target']['source'];
      this.draftannos.push(senddata['id'])
      const index = this.draftannos.length-1;
      jQuery.ajax({
        url: `/${method}_annotations/`,
        type: "POST",
        dataType: "json",
        data: JSON.stringify(senddata),
        contentType: "application/json; charset=utf-8",
        success: function(data) {
          const inlist = vue.filepaths[key] ? vue.filepaths[key].findIndex(x => x['id'] === senddata['id']) : false;
          if (annotation && method != 'delete') {
            delete vue.draftannos[index]
            vue.anno.removeAnnotation(annotation);
            annotation['id'] = data['id']
            annotation['order'] = data['order'];
            vue.anno.addAnnotation(annotation);
            if (typeof(inlist) == 'number') {
              vue.filepaths[key][inlist] = annotation
            } else {
              vue.filepaths[key] = [annotation]
            }
          } else if (method == 'delete' && typeof(inlist) == 'number') {
            delete vue.filepaths[key][inlist]
          }
        },
        error: function(err) {
          alert(`${err.responseText}`);
          if (err.status == 418){
            var errorannoget = localStorage.getItem('erranno');
            errorannoget = errorannoget ? errorannoget : [];
            const errorcontent = {'annotation': annotation, 'method': method, 'image': vue.canvas ? vue.canvas : vue.inputurl}
            errorannoget.push(errorcontent);
            localStorage.setItem('erranno', JSON.stringify(errorannoget));
            location.href = location.origin + `/login?next=${location.origin}/?manifesturl=${vue.currentmanifest}&imageurl=${vue.inputurl}&canvas=${vue.canvas}`
          }
        }
      });
    }
  }
})

var app = new Vue({
  el: '#app'
})
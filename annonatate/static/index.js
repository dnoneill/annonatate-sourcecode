const annoview = Vue.component('annoview', {
  template: `<div>
  <div id="myModal" class="modal" v-if="showModal">
    <div class="modal-content">
      <span class="close-modal" v-on:click="showModal=false;externalModal=false;">&times;</span>
      <span class="back" style="float:left" v-if="externalModal" v-on:click="externalModal=false;"><i class="fas fa-arrow-left"></i></span>
      <div class="optionsmodal" v-if="!externalModal">
        <div class="modal-options icontextbutton">
          <a href="/upload">
          Upload your own image
          <i class="fas fa-upload"></i>
          </a>
        </div>
        <div class="modal-options icontextbutton">
          <a v-on:click="externalModal=true">
          Use external image
            <i class="fas fa-link"></i>
          </a>
        </div>
        <hr>
        Not ready to add images? Try our demo images:
        <div class="demoimages">
          <div v-for="image in demoimages">
              <button v-if="image['url']" class="linkbutton" v-on:click="checkType(image); showModal=false;">
                <img class="imgthumb" v-bind:alt="image['alt']" v-if="image['thumbnail']" v-bind:src="image['thumbnail']"/>
                <figcaption>{{image['title']}}</figcaption>
              </button>
          </div>
        </div>
      </div>
      <div v-if="externalModal">
        <div v-if="modalerror" v-html="modalerror" class="error"></div>
        <h2>Add external link</h2>
        <input id="ingesturl" v-model="externalurl" placeholder="The URL of an image or IIIF resource" aria-label="The URL of an image or IIIF resource"></input>
        <button class="button modal-button" title="This will add your image to the My Images section and will open your added image." v-on:click="externalClick('addtodata', externalurl);"><i class="fas fa-plus"></i> Add to My Images</button>
        <button class="button modal-button" title="This will make a copy of your manifest that you will host. It also ensures links to your annotations will be automatically added to your manifest. It will also add it to the my images section and open your manifest." v-on:click="externalClick('copy', externalurl);" v-if="externalurl.indexOf('manifest') > -1 || (externalurl.indexOf('.json') > -1 && externalurl.indexOf('info.json') == -1)">
          <i class="fas fa-copy"></i> Make Copy
        </button>
        <button class="button modal-button" title="This will open your image for annotation without adding it to the My images section." v-on:click="externalClick('noadd', externalurl);"><i class="fas fa-eye"></i> View</button>
      </div>
    </div>
  </div>
  <div class="my-images">
    <h2>
    My Images
    <div class="my-images-icons">
        <div v-if="!editMode" v-on:click="manimageshown=true;editMode=!editMode">
          <i class="fas fa-edit"></i>
        </div>
        <div v-else>
          <!-- <span v-on:click="editMode=!editMode;">
             <i class="fas fa-save"></i>
          </span> -->
          <span v-on:click="editMode=!editMode;">
            <i class="fas fa-window-close"></i>
          </span>
        </div>
        <div v-on:click="manimageshown = !manimageshown;" title="Click to expand/collapse image list">
          <i class="fas" v-bind:class="[manimageshown ? 'fa-minus-square' : 'fa-plus-square']"></i>
        </div>
      </div>
      
    </h2>
    <div v-if="manimageshown" style="display:flex;">
      <div class="addimage">
          <div v-on:click="showModal=true" class="icontextbutton">
            <i class="fas fa-plus"></i>
          </div>
          Add Image
        </div>
      <div class="manifestimages" :class="{'noanno' : !anno}">
        <div v-for="image in imageslist" class="imagecontainer">
          <span v-if="image['url']">
            <img class="linkbutton" v-on:click="checkType(image)" class="imgthumb" v-bind:alt="image['title'] ? image['title'] : image['url']" v-if="image['thumbnail']" v-bind:src="image['thumbnail']"/>
            <img class="linkbutton" v-on:click="checkType(image)" class="imgthumb" v-bind:alt="image['title'] ? image['title'] : image['url']" v-else-if="!image['iiif']" v-bind:src="image['url']"/>
            <figcaption class="linkbutton" v-on:click="checkType(image)">{{image['title'] ? image['title'] : image['url']}}</figcaption>
            <button class="deletebutton button" v-if="editMode" v-on:click="deleteManifest(image)">
              <i class="fas fa-trash-alt"></i>
            </button>
          </span>
        </div>
      </div>
    </div>
  </div>
  <div class="annotorious-viewer" v-bind:class="{'noanno' : !anno}">
    <div id="header-toolbar">
      <div v-if="title" class="image-title">
        <span v-html="title[0]['value'] + ':'"></span>
        <span v-if="alltiles.length > 0 && alltiles[0]['label']">{{alltiles[0]['label']}}</span>
      </div>
      <div id="savemessage" v-if="anno" v-html="savemessage"></div>
      <div class="tools">
        <button v-on:click="showManThumbs = !showManThumbs" v-if="currentmanifest && manifestdata.length > 1">
          <i class="fas" v-bind:class="[showManThumbs ? 'fa-minus-square' : 'fa-plus-square']"></i> Thumbnails
        </button>
        <div class="dropdown share homepagedrop" v-if="anno">
          <button class="dropbtn" onclick="dropdownToggle('homepageshare')" aria-label="share">
            <i class="fas fa-share-alt"></i> Share
          </button>
          <div class="dropdown-content" id="homepageshare">
            <a target="_blank" v-bind:href="'https://ncsu-libraries.github.io/annona/tools/#/display?url='+annolistname+ '&viewtype=iiif-storyboard&settings=%7B%22fullpage%22%3Atrue%7D'">
              Dynamic annotation view for current image <i class="fas fa-link"></i></a>
            <a target="_blank" v-bind:href="'https://ncsu-libraries.github.io/annona/tools/#/display?url='+annolistname+'&viewtype=iiif-annotation&settings=%7B%22fullpage%22%3Atrue%7D'">
              Annotations as list for current image <i class="fas fa-link"></i></a>
            <a v-if="currentmanifest" id="displaystoryboard" target="_blank" v-bind:href="'https://ncsu-libraries.github.io/annona/tools/#/display?url=' + currentmanifest + '&viewtype=iiif-storyboard&settings=%7B%22fullpage%22%3Atrue%7D'">
              Dyanmic annotation view of all images <i class="fas fa-link"></i>
            </a>
            <a v-if="currentmanifest" id="mirador3" target="_blank" v-bind:href="'https://projectmirador.org/embed/?iiif-content=' + currentmanifest">
              View in Mirador 3 <i class="fas fa-link"></i>
            </a>
          </div>
        </div>
        <button v-if="anno" class="hide-annos" v-bind:title="annosvisible ? 'Hide Annotations' : 'Show Annotations'" v-on:click="setVisible()">
          <i class="fas fa-eye" v-if="!annosvisible"></i>
          <i class="fas fa-eye-slash" v-else-if="annosvisible"></i>
          <span v-if="annosvisible"> Hide</span><span v-else> Show</span> Annotations
        </button>
        <div style="height:15px" v-else></div>
      </div>
    </div>
    <div class="manifestthumbs" v-show="showManThumbs && currentmanifest && manifestdata.length > 1">
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
    <div class="layers gridparent" v-if="alltiles.length > 1">
      <div v-for="item in alltiles">
        <input type="checkbox" class="tagscheck" v-on:click="setOpacity(item)" v-model="item.checked">
        <span v-html="item.label"></span>
        <div class="slidecontainer">Opacity: <input v-on:change="setOpacity(item, $event)" type="range" min="0" max="100" v-bind:value="item.opacity*100" class="slider"></div>
        <img :src="item['thumbnail']" style="max-width:100px;padding:5px;"  alt="tile thumbnail">
      </div>
    </div>  
    <div class="drawingtools">
      <div id="drawing-toolbar-container"></div>
      <div id="helptext" class="helptext"></div>
    </div>
    <a class="prev prevnext" v-on:click="next('prev')" v-if="manifestdata && manifestdata[currentposition-1]">&lt;</a>
    <a class="next prevnext" v-on:click="next('next')" v-if="manifestdata && manifestdata[currentposition+1]">&gt;</a>
    <div id="openseadragon1" v-bind:class="{'active' : inputurl !== ''}">
      <div v-if="!anno">Select an image to begin annotating</div>
    </div>
  </div>
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
      anno: '',
      viewer: '',
      manifestdata: '',
      modalerror: '',
      currentmanifest: '',
      showManThumbs: false,
      canvas: '',
      title: '',
      alltiles: [],
      drawingenabled: false,
      ingesturl: '',
      fragmentunit: 'pixel',
      currentposition: 0,
      widgets: ['comment-with-purpose','tag','geotagging'],
      draftannos: [],
      annosvisible: true, 
      manimageshown: true,
      annolistname: '',
      imageslist: [],
      externalurl: '',
      savemessage: '<i class="fas fa-save"></i>',
      showModal: false,
      externalModal: false,
      editMode: false,
      demoimages: [{'alt': 'Four squares with colorful illustrations of insects.', 'title': 'Demo image (IIIF manifest): Insectes. [patterns]', 'url': 'https://d.lib.ncsu.edu/collections/catalog/segIns_020/manifest.json', 'thumbnail': 'https://iiif.lib.ncsu.edu/iiif/segIns_020/full/120,/0/default.jpg'},
        {'alt': 'Painting of a man in side view','title': 'Demo images (IIIF manifest): National Gallery of Art Collection Highlights', 'url': 'https://media.nga.gov/public/manifests/nga_highlights.json', 'thumbnail': 'https://media.nga.gov/iiif/public/objects/1/0/6/3/8/2/106382-primary-0-nativeres.ptif/full/120,/0/default.jpg'},
        {'alt': 'Sepia tinted map of an island','title': 'Demo IIIF image: from Duke Collection', 'url': 'https://repository.duke.edu/fcgi-bin/iipsrv.fcgi?IIIF=/nas/repo_deriv/hydra/multires_image/40/58/a6/28/4058a628-c593-463e-9736-8a821e178fee/info.json', 'thumbnail': 'https://repository.duke.edu/fcgi-bin/iipsrv.fcgi?IIIF=/nas/repo_deriv/hydra/multires_image/40/58/a6/28/4058a628-c593-463e-9736-8a821e178fee/full/120,/0/default.jpg'},
        {'alt': 'Orange quilt with silhouette figures', 'title': 'Demo image: from Wikimedia', 'url': 'https://upload.wikimedia.org/wikipedia/commons/7/7e/PowersBibleQuilt_1886.jpg', 'thumbnail': 'https://upload.wikimedia.org/wikipedia/commons/7/7e/PowersBibleQuilt_1886.jpg'}
      ]
  	}
  },
  watch: {
    externalModal: function() {
      this.modalerror = '';
    },
    canvas: function() {
      this.annolistname = listfilename(this.canvas);
      this.updateUrlParams('canvas', this.canvas);
      this.updateUrlParams('imageurl', '');
    },
    inputurl: function() {
      if (!this.canvas || !this.currentmanifest){
        this.updateUrlParams('imageurl', this.inputurl);
        this.updateUrlParams('manifesturl', '');
        this.updateUrlParams('canvas', '');
      }
    },
    currentmanifest: function() {
      this.updateUrlParams('manifesturl', this.currentmanifest);
    }    
  },
  created(){
    this.parseExisting();
  },
  mounted() {
    if (this.existing.settings && this.existing.settings.widgets){
      this.widgets = this.existing.settings.widgets.split(",").map(elem => elem.trim());
    }
    const params = new URLSearchParams(window.location.search);
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
      this.ingesturl = imageurl;
      this.loadAnno();
    }
    if (this.updatepage){
      this.setUpdate();
    }
  },
  methods: {
    deleteManifest: function(image) {
      const imagetitle = image['title'] ? image['title'] : image['url']
      const check = confirm(`Are you sure you want to delete ${imagetitle}?`);
      if (check){
        var form_data = new FormData();
        if (image['upload']) {
          form_data.append('file', JSON.stringify(image));
          form_data.append('returnjson', true);
          this.deleteManifestRequest(image, '/deletefile', form_data);
        } else {
          form_data.append('removeurl', JSON.stringify(image));
          this.deleteManifestRequest(image, '/updatedata', form_data);
        }
      }
    },
    deleteManifestRequest: function(image, deleteurl, form_data) {
      var vue = this;
      jQuery.ajax({
        url: deleteurl,
        type: "POST",
        data: form_data,
        contentType: false, 
        processData: false,
        success: function(data) {
          const index = vue.imageslist.indexOf(image);
          if (index > -1) { 
            vue.imageslist.splice(index, 1);
          }
        }, error: function(err) { 
          console.log(err)
          alert(`Unable to delete ${image['title'] ? image['title']: image['url']}`)
          return 0;
        }
      });
    },
    checkType: function(manifetdict) {
      if (manifetdict.constructor.name == 'String'){
        this.getManifest(manifetdict)
      } else if (manifetdict['iiif'] || manifetdict['url'].indexOf('/manifest') > -1) {
        this.getManifest(manifetdict)
      } else {
        this.inputurl = manifetdict['url'];
        this.ingesturl = manifetdict['url'];
        this.loadImage();
      }
    },
    parseExisting: function() {
      const manifests = this.existing['images'].filter(elem => elem);
      for (var em=0; em<manifests.length; em++){
        var man = manifests[em];
        if (man['json']) {
          var manifestmeta = this.getManifestMeta(man);
          var title = man['title'];
          const titlelang = Array.isArray(title) && title.length > 0 ? title.filter(elem => elem['locale'] == navigator.language || elem == navigator.language) : [];
          title = titlelang.length > 0 ? titlelang[0] :Array.isArray(title) ? title[0] : title;
          title = title['value'] ? title['value'] : title instanceof Object ? title[Object.keys(title)][0] : title;
          man['title'] = title;
          this.imageslist.push(man)
        } else {
          if (man.constructor.name == 'String') {
            man = {'title': '', 'url': man, 'thumbnail': ''}
          }
          this.imageslist.push(man)
        }
      }
    },
    cleanCheckAdd: function(url) {
      var cleanurl =  url.replace(`${this.originurl}manifests/`, '').replace('://', '');
      return cleanurl.slice(cleanurl.indexOf('/'))
    },
    externalClick: function(type, url){
      var vue = this;
      this.modalerror = '';
      const urls = this.imageslist.map(elem => this.cleanCheckAdd(elem['url']));
      if (type != 'noadd' && urls.indexOf(this.cleanCheckAdd(url)) > -1) {
        this.modalerror = 'This image is already in your My Images list.'
        this.externalurl = '';
        return 0;
      }
      if (type == 'noadd'){
        this.getManifest(url);
      } else if (type == 'addtodata') {
        var form_data = new FormData();
        form_data.append('addurl', url);
        jQuery.ajax({
          url: "/updatedata",
          type: "POST",
          data: form_data,
          contentType: false, 
          processData: false,
          success: function(data) {
            if (data['images'][0]['url'] == url) {
              vue.externalAfterLoad(data['images'][0])
            }
          }, error: function(err) { 
            console.log(err)
            return 0;
          }
        });
      } else if (type=='copy') {
        var form_data = new FormData();
        form_data.append('returnjson', true);
        form_data.append('upload', url);
        jQuery.ajax({
          url: "/createimage",
          type: "POST",
          data: form_data,
          contentType: false, 
          processData: false,
          success: function(data) {
            if (data['output'] == true) {
              vue.externalAfterLoad(data);
            }
          }, error: function(err) { 
            console.log(err)
            return 0;
          }
        });
      }
      this.externalModal=false;
      this.showModal=false;
    },
    externalAfterLoad: function(data) {
      this.imageslist.unshift(data);
      this.getManifest(data);
      this.externalurl = '';
    },
    getManifestMeta: function(manifest){
      var m = manifesto.parseManifest(JSON.parse(manifest['json']));
      var title = m ? m.getLabel() : "";
      var fullvalue = m.context.indexOf('3') > -1 ? 'max' : 'full';
      const sequence = m.getSequenceByIndex(0);
      const firstcanvas = sequence.getCanvasByIndex(0);
      var thumbnail = m.getThumbnail();
      thumbnail = thumbnail ? thumbnail : firstcanvas.getThumbnail();
      thumbnail ? thumbnail = this.getId(thumbnail['__jsonld']) : ''
      if (!thumbnail){
        var manifestimages = firstcanvas['__jsonld']['images'] ? firstcanvas['__jsonld']['images'] : firstcanvas['__jsonld']['items'];
        manifestimages = manifestimages[0]['items'] ? manifestimages[0]['items'] : manifestimages;  
        var resourceitem = manifestimages[0]['resource'] ? manifestimages[0]['resource'] : manifestimages[0]['body'] ? manifestimages[0]['body'] :  Array.isArray(manifestimages[0]['items']) ? manifestimages[0]['items'][0] : manifestimages[0]['items'];
        thumbnail = this.getId(resourceitem);     
      }
      thumbnail = thumbnail.replace(`/${fullvalue}/0`, `/100,/0`).replace("{{ '/' | absolute_url }}", this.originurl)
      manifest['thumbnail'] = thumbnail;
      manifest['title'] = title;
      return manifest;
    },
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
    updateUrlParams: function(field, replacement) {
      var url = new URL(window.location);
      url.searchParams.set(field, replacement);
      window.history.pushState({}, '', url);
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
      const annoverlays = document.getElementsByClassName('a9s-annotation');
      for (var ao=0; ao<annoverlays.length; ao++){
        annoverlays[ao].style.display = this.annosvisible ? 'block' : 'none';
      }
    },
    loadAnno: function() {
      var seadragoncontainer =  'openseadragon1';
      var toolbarcontainer = 'drawing-toolbar-container';
      const toolbardiv = document.getElementById(toolbarcontainer);
      var currentdrawtool = toolbardiv.innerHTML != '' ? toolbardiv.getElementsByClassName('active')[0].classList[1] : '';
      document.getElementById(seadragoncontainer).innerHTML = '';
      toolbardiv.innerHTML = '';
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
        id: seadragoncontainer,
        prefixUrl: "/assets/openseadragon/images/",
        tileSources: tilesources,
        zoomPerScroll: 1,
        navigationControlAnchor: OpenSeadragon.ControlAnchor.BOTTOM_RIGHT
      });
      this.viewer = viewer;
      var vue = this;
      viewer.addHandler('open', function(){
        if (currentdrawtool){
          document.getElementsByClassName(currentdrawtool)[0].click();
        }
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
        { image: seadragoncontainer,
          messages: { "Ok": "Save" },
          fragmentUnit: this.fragmentunit,
          allowEmpty: true,
          widgets: widgets});
    // Load annotations in W3C WebAnnotation format
      this.annoLoadOSD();
      Annotorious.SelectorPack(this.anno);
      Annotorious.TiltedBox(this.anno);
      this.addListeners();
      Annotorious.Toolbar(this.anno, toolbardiv, {'withLabel': true, 'withMouse': true, 'infoElement': document.getElementById('helptext')});
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
    getManifestFunctions: function(data, manifest, loadcanvas=false){
      this.manimageshown = false;
      const context = data['@context'] && Array.isArray(data['@context']) ? data['@context'].join("") : data['@context'];
      if (data.constructor.name == 'String' || context && context.indexOf('presentation') == -1){
        this.inputurl = manifest;
        this.currentmanifest = '';
        this.loadImage();
      }
      var images = [];
      var m = manifesto.parseManifest(data);
      this.title = m ? m.getLabel() : "";
      const sequence = m.getSequenceByIndex(0);
      const manifestdata = sequence.getCanvases();
      if (!manifestdata) {
        this.manifestdata = 'failure';
        return;
      }
      for (var i=0; i<manifestdata.length; i++){
        var tiles = [];
        var manifesthumb = m.getThumbnail();
        var size = manifesthumb && manifesthumb.id && manifesthumb.id.indexOf('full') > -1 ? manifesthumb.id.split('full/').slice(-1)[0].split('/0')[0] : '100,'
        var canvas = manifestdata[i].id;
        var thumb = manifestdata[i].getThumbnail();
        thumb ? thumb = this.getId(thumb['__jsonld']) : ''
        var manifestimages = manifestdata[i]['__jsonld']['images'] ? manifestdata[i]['__jsonld']['images'] : manifestdata[i]['__jsonld']['items'];
        manifestimages = manifestimages[0]['items'] ? manifestimages[0]['items'] : manifestimages;
        var fullvalue = m.context.indexOf('3') > -1 ? 'max' : 'full';
        for (var j=0; j<manifestimages.length; j++){
          var resourceitem = manifestimages[j]['resource'] ? manifestimages[j]['resource'] : manifestimages[j]['body'] ? manifestimages[j]['body'] :  Array.isArray(manifestimages[j]['items']) ? manifestimages[j]['items'][0] : manifestimages[j]['items'];
          resourceitem = Array.isArray(resourceitem) ? resourceitem[0] : resourceitem;
          const resourceservice = resourceitem['service'] && Array.isArray(resourceitem['service']) ? resourceitem['service'][0] : resourceitem['service'];
          var id = resourceservice ? this.trimCharacter(this.getId(resourceservice), '/') + '/info.json' : this.getId(resourceitem);
          id = resourceservice ? this.trimCharacter(id.split('/info')[0], '/') + '/info.json' : id;
          const opacity = j == 0 ? 1 : 0;
          const checked = j == 0 ? true : false;
          const resourceid = resourceitem ? this.getId(resourceitem) : '';
          var xywh = resourceid && resourceid.constructor.name === 'String' && resourceid.indexOf('xywh') > -1 ? resourceid : this.on_structure(manifestimages[j]) && this.on_structure(manifestimages[j])[0].constructor.name === 'String' ? this.on_structure(manifestimages[j])[0] : '';
          xywh = xywh ? xywh.split("xywh=").slice(-1)[0].split(",") : xywh;
          const getLabel = manifestdata[i].getLabel();
          const tilelabel = getLabel && getLabel.length > 0 ? getLabel[0]['value'] : ""
          const imagethumb = id.replace('/info.json',`/full/${size}/0/default.jpg`)
          if (!thumb){
            thumb = imagethumb;
          }
          tiles.push({'id': id, 'label': tilelabel,
            thumbnail: imagethumb, 'opacity': opacity,
            'checked': checked, 'xywh': xywh
          })
        }
        thumb = thumb ? thumb.replace(`/${fullvalue}/0`, `/${size}/0`) : thumb;
        images.push({'image': thumb, 'canvas': canvas, 'tiles': tiles})
        if (loadcanvas == canvas) {
          this.currentposition = i;
          this.manifestLoad({'image': thumb, 'canvas': canvas, 'tiles': tiles})
        }
      }
      if (images.length > 1){
        this.showManThumbs = true;
      }
      this.manifestdata = images;
      if (!loadcanvas){
        this.manifestLoad(images[0]);
      }
    },
    getManifest: function(manifestdata, loadcanvas=false) {
      var manifest;
      var manifestjson;
      if (manifestdata.constructor.name == 'String'){
        manifest = manifestdata;
      } else {
        manifest = manifestdata['url'];
        if (manifestdata['json']){
          manifestjson = JSON.parse(manifestdata['json'].replaceAll("{{ '/' | absolute_url }}", this.originurl));
        }
      }
      this.currentmanifest = manifest;
      this.manifestdata = [];
      this.ingesturl = manifest;
      var vue = this;
      if (manifestjson) {
        this.getManifestFunctions(manifestjson, manifest, loadcanvas);
      } else {
        jQuery.ajax({
          url: manifest,
          type: "GET",
          success: function(data) {
            vue.getManifestFunctions(data, manifest, loadcanvas)
          },
          error: function(err) {
            if (err.status < 300){
              vue.inputurl = manifest;
              vue.loadImage();
            } else {
              vue.manifestdata = 'failure';
            }
          }
        });
      }
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
      this.drawingenabled = enable;
      this.anno.setDrawingEnabled(enable);
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
            vue.savemessage = `<i class="fas fa-save"></i> Annotations last saved: ${new Date(Date.now()).toLocaleTimeString(navigator.language)}`
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
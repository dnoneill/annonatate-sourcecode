const annoview = Vue.component('annoview', {
    template: `<div id="mirador" style="height:600px; position:relative;">
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
            mirador: '',
            loadedManifest: ''
        }
    },
    created() {
        
        
    },
    mounted() {
        const params = new URLSearchParams(window.location.search);
        const manifesturl = params.get('manifesturl');
        const canvas = params.get('canvas');
        const manifests = this.existing['manifests'];
        const loadedManifest = manifesturl ? manifesturl.toString() : manifests[0];
        var manifestload = manifests.map(ma => JSON.parse(`{ "manifestUri": "${ma}"}`));
        manifestload.push({"manifestUri": loadedManifest})
        const api_server = "/"
        this.mirador = Mirador({
            id: "mirador",
            data: manifestload,
            windowObjects: [
              {
                "loadedManifest" : loadedManifest,
                "sidePanelVisible": false,
                "canvasID": canvas
               }
            ], 
            annotationEndpoint: { 'name':'Local Annotation Endpoint', 'module': 'LocalAnnotationEndpoint', 
                'options': {'server': api_server, 'allannotations' : this.filepaths, 'creator': this.userinfo['name']}},
            sidePanelOptions : {
          'tocTabAvailable': true,
          'layersTabAvailable': true,
          'searchTabAvailable': true
        }
        });
    }
  })
  
  var app = new Vue({
    el: '#app'
  })
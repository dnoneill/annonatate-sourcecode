const annoview = Vue.component('annoview', {
    template: `<div id="mirador" style="height:600px; position:relative;">
    </div>
    `,
    props: {
      'existing': Object,
      'filepaths': Object,
      'userinfo': Object,
      'tags': Array,
      'originurl': String
    },
    data: function() {
        return {
            mirador: '',
            loadedManifest: ''
        }
    },
    mounted() {
        const params = new URLSearchParams(window.location.search);
        const manifesturl = params.get('manifesturl');
        const canvas = params.get('canvas');
        const manifests = this.existing['manifests'];
        const loadedManifest = manifesturl ? manifesturl.toString() : manifests[0];
        var manifestload = manifests.map(ma => JSON.parse(`{ "manifestUri": "${ma}"}`));
        manifestload.push({"manifestUri": loadedManifest})
        const check = loadedManifest.indexOf(this.originurl) > -1;
        const layout = check ? "1x2" : "1x1";
        windowObjs = [{
          "loadedManifest" : loadedManifest,
          "sidePanelVisible": false,
          "canvasID": canvas
         }]
         if (check) {
           var newObj = JSON.parse(JSON.stringify(windowObjs[0]));
           console.log(windowObjs)
           windowObjs[0]["id"] = "slot1";
           windowObjs[0]["slotAddress"] = "row1.column1";
           newObj["slotAddress"] = "row1.column2";
           windowObjs.push(newObj)
         }
        const api_server = "/"
        this.mirador = Mirador({
            id: "mirador",
            layout: layout,
            data: manifestload,
            windowObjects: windowObjs,
            annotationEndpoint: { 'name':'Local Annotation Endpoint', 'module': 'LocalAnnotationEndpoint', 
                'options': {'originurl': this.originurl, 'server': api_server, 'allannotations' : this.filepaths, 'creator': this.userinfo['name']}},
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
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
        this.loadedManifest = manifesturl ? manifesturl : manifests[0];
        const manifestload = manifests.map(ma => JSON.parse(`{ "manifestUri": "${ma}"}`));
        const api_server = "/"
        console.log(this.loadedManifest)
        this.mirador = Mirador({
            "id": "mirador",
            "data": manifestload,
            "windowObjects": [
              {
                "loadedManifest": this.loadedManifest
              }
            ], 
            annotationEndpoint: { 'name':'Local Annotation Endpoint', 'module': 'LocalAnnotationEndpoint', 
                'options': {'server': api_server, 'allannotations' : this.filepaths, 'creator': this.userinfo['value']}},
            sidePanelOptions : {
          'tocTabAvailable': true,
          'layersTabAvailable': true,
          'searchTabAvailable': true
        }
        });
        console.log(this.mirador)
    },
    methods: {
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
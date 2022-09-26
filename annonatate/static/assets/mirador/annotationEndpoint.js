(function($) {
  $.LocalAnnotationEndpoint = function(options) {
    jQuery.extend(
      this,
      {
        token: null,
        uri: null,
        url: options.url,
        dfd: null,
        creator: null,
        annotationsList: [],
        idMapper: {},
        originurl: null,
        hasbeenreloaded: false
      },
      options
    );
    this.init();
  };

  $.LocalAnnotationEndpoint.prototype = {
    init: function() {
      this.checkErrorAnnos();
      this.removeItem();
      var _this = this;
      this.eventEmitter.subscribe('windowUpdated', function(event, params) {
        if (Object.keys(params).indexOf('loadedManifest') > -1) {
          _this.manifesturl = params.loadedManifest;
          _this.eventEmitter.publish('REMOVE_SLOT_FROM_WINDOW', 'slot1')
        }
      });
      setInterval(() => {
        jQuery.ajax({
          url: "/update",
          type: "GET",
          success: function(data) {
            _this.allannotations = data;
            _this.eventEmitter.publish('updateAnnotationList.'+_this.windowID);
          }
        });
      }, "60000")
    },
    checkErrorAnnos: function(){
      const erroranno = JSON.parse(localStorage.getItem('erranno'));
      if (erroranno) {
        for (var ea=0; ea<erroranno.length; ea++){
          const annotation = erroranno[ea]['annotation'];
          if (erroranno[ea]['method'] == 'create'){
            this.create(annotation)
          } else if (erroranno[ea]['method'] == 'update'){
            this.update(annotation)
          } else {
            this.deleteAnnotation(erroranno[ea]['annotation'], '', '', erroranno[ea]['image'])
          }
        }
        localStorage.removeItem('erranno');
      }
    },
    errorAlert: function(err, annotation) {
      alert(`${err.responseText}`);
      var _this = this;
      if (err.status == 418){
        var errorannoget = localStorage.getItem('erranno');
        errorannoget = errorannoget ? errorannoget : [];
        const canvas = annotation['canvas'] ? annotation['canvas'] : _this.options.uri;
        const errorcontent = {'annotation': annotation['json'], 'method': annotation['method'], 'image': canvas}
        errorannoget.push(errorcontent);
        localStorage.setItem('erranno', JSON.stringify(errorannoget));
        location.href = location.origin + `/login?next=${location.origin}/?manifesturl=${this.manifesturl}&canvas=${canvas}`
      }
    },
    search: function(options) {
      var _this = this;
      _this.uri = options.uri;
      _this.annotationsList = [];
      _this.options = options;
      const resources = this.allannotations[options['uri']];
      if (resources){
        _this.annotationsList = resources
        resources.forEach(function(a) {
          a.endpoint = _this;
        });
      }
      _this.dfd.resolve(false);
    },
    removeItem:function() {
      const id = this.imagesList[0]['@id'] ? '@id' : 'id';
      for (var index=0; index < this.imagesList.length; index++ ) {
        const stringJSON = JSON.stringify(this.imagesList[index].otherContent)
        if (stringJSON && stringJSON.indexOf(this.originurl)){
          this.imagesList[index].otherContent =this.imagesList[index].otherContent.filter(elem => elem[id].indexOf(this.originurl) == -1);
        }
      }
    },
    deleteAnnotation: function(annotationID, returnSuccess, returnError, canvas=false) {
      split = annotationID.split("/");
      const ID = split[split.length - 1];
      var _this = this;
      const sendcanvas = this.uri ? this.uri : canvas;
      const content = {'id':ID, 'canvas': sendcanvas, 'json': ID};
      this.sendAnnotation(content, 'delete', returnSuccess, returnError)
    },
    successFunction: function(method, annotation) {
      var _this = this;
      if (_this.annotationsList.length === 0) {
        _this.annotationsList = [];
      }
      if (method == 'create'){
        _this.annotationsList.push(annotation);
      } else if (method == 'update'){
        jQuery.each(_this.annotationsList, function(index, value) {
          if (value['@id'] === annotation['@id']) {
            _this.annotationsList[index] = annotation;
            return false;
          }
        });
      } else {
        _this.annotationsList = jQuery.grep(_this.annotationsList, function(value, index) {
          return value['@id'] !== annotation['id'];
        });
        //_this.eventEmitter.publish('removeOverlay.'+_this.windowID, annotation['id']);
        // _this.eventEmitter.publish("ANNOTATIONS_LIST_UPDATED",{windowId:_this.id,annotationsList:_this.annotationsList});
      }
      _this.annotationsList.forEach(function(a) {
        delete a.endpoint;
      });
      _this.annotationsList.forEach(function(a) {
        a.endpoint = _this;
      });
      _this.allannotations[_this.uri] = _this.annotationsList;
      _this.dfd.resolve(false);
      _this.eventEmitter.publish('updateAnnotationList.'+_this.windowID);
    },
    update: function(annotation, returnSuccess, returnError) {
      var updated = new Date().toISOString();
      delete annotation.endpoint;
      annotation['oa:serializedAt'] = updated;
      var creator = this.creator;
      if (annotation['oa:annotatedBy']) {
        annotation['oa:annotatedBy'].indexOf(creator) == -1 ? annotation['oa:annotatedBy'].push(creator) : ''
      } else {
        annotation['oa:annotatedBy'] = [creator]
      }
      var senddata = {'json': annotation, 'canvas': this.uri, 'id': annotation['@id'], 'order': annotation['order']}
      this.sendAnnotation(senddata, 'update', returnSuccess, returnError)
    },
    sendAnnotation: function(senddata, method, returnSuccess, returnError){
      var _this = this;
      var send = senddata;
      const anno = send['anno'] ? send['anno'] : send['json'];
      if (Object.keys(anno).indexOf('endpoint')){
        delete anno['endpoint']
      }
      jQuery.ajax({
        url: this.server + `${method}_annotations/`,
        type: "POST",
        dataType: "json",
        data: JSON.stringify(send),
        contentType: "application/json; charset=utf-8",
        success: function(data) {
          data.endpoint = _this;
          const successdata = method == 'delete' ? senddata : data;
          if (typeof returnSuccess === "function") {
            returnSuccess(successdata);
          } else {
            _this.successFunction(method, successdata)
          }
        },
        error: function(err) {
          senddata['method'] = method;
          _this.errorAlert(err, senddata);
          if (typeof returnError === "function") {
            returnError();
          }
        }
      });
    },
    create: function(annotation, returnSuccess, returnError) {
      var created = new Date().toISOString();
      annotation['oa:annotatedAt'] = created;
      annotation['@id'] = Mirador.genUUID();
      annotation['oa:annotatedBy'] = [this.creator];
      var senddata = {'json': annotation, 'canvas': this.uri, 'id': annotation['@id']}
      this.sendAnnotation(senddata, 'create', returnSuccess, returnError)
    },

    set: function(prop, value, options) {
      if (options) {
        this[options.parent][prop] = value;
      } else {
        this[prop] = value;
      }
    },
    userAuthorize: function(action, annotation) {
      //console.log(this.creator)
      //console.log(annotation['oa:annotatedBy'].indexOf(this.creator))
      return true; // allow all
    }
  };
}(Mirador));

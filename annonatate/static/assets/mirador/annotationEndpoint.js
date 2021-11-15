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
        idMapper: {}
      },
      options
    );
    this.init();
  };

  $.LocalAnnotationEndpoint.prototype = {
    init: function() {
    },

    search: function(options) {
      var _this = this;
      _this.uri = options.uri;
      _this.annotationsList = [];
      const resources = this.allannotations[options['uri']];
      if (resources){
        _this.annotationsList = resources
        resources.forEach(function(a) {
          a.endpoint = _this;
        });
      }
      _this.dfd.resolve(false);
    },

    deleteAnnotation: function(annotationID, returnSuccess, returnError) {
      split = annotationID.split("/");
      ID = split[split.length - 1];
      jQuery.ajax({
        url: this.server + 'delete_annotations/',
        type: "DELETE",
        contentType: 'application/json',
        data: JSON.stringify({'id':ID, 'canvas': this.uri}),
        dataType: "json",
        success: function(data) {
          returnSuccess();
        },
        error: function() {
          console.log('error')
          returnError();
        }
      });
    },

    update: function(annotation, returnSuccess, returnError) {
      var _this = this;
      var updated = new Date().toISOString();
      delete annotation.endpoint;
      annotation['oa:serializedAt'] = updated;
      var creator = this.creator;
      if (annotation['oa:annotatedBy']) {
        annotation['oa:annotatedBy'].indexOf(creator) == -1 ? annotation['oa:annotatedBy'].push(creator) : ''
      } else {
        annotation['oa:annotatedBy'] = [creator]
      }
      var senddata = {'json': annotation}
      jQuery.ajax({
        url: _this.server + 'update_annotations/',
        type: "POST",
        dataType: "json",
        data: JSON.stringify(senddata),
        contentType: "application/json; charset=utf-8",
        success: function(data) {
          data.endpoint = _this;
          returnSuccess(data);
        },
        error: function() {
          returnError();
        }
      });
      annotation.endpoint = this;
    },

    create: function(annotation, returnSuccess, returnError) {
      var _this = this;
      var created = new Date().toISOString();
      annotation['oa:annotatedAt'] = created;
      annotation['@id'] = Mirador.genUUID();
      annotation['oa:annotatedBy'] = [this.creator];
      var senddata = {'json': annotation, 'canvas': this.uri}
      jQuery.ajax({
        url: this.server + 'create_annotations/',
        type: "POST",
        dataType: "json",
        data: JSON.stringify(senddata),
        contentType: "application/json; charset=utf-8",
        success: function(data) {
          data.endpoint = _this;
          returnSuccess(data);
        },
        error: function() {
          returnError();
        }
      });
    },

    set: function(prop, value, options) {
      if (options) {
        this[options.parent][prop] = value;
      } else {
        this[prop] = value;
      }
    },
    userAuthorize: function(action, annotation) {
      console.log(this.creator)
      console.log(annotation['oa:annotatedBy'].indexOf(this.creator))
      return true; // allow all
    }
  };
})(Mirador);
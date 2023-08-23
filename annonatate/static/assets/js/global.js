function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
    if (history.pushState) {
        let searchParams = new URLSearchParams(window.location.search);
        searchParams.set('tab', tabName);
        let newurl = window.location.protocol + "//" + window.location.host + window.location.pathname + '?' + searchParams.toString();
        window.history.pushState({path: newurl}, '', newurl);
    }
}
function UrlExists(url){
    var status = false;
    var senddata = '';
    $.ajax({url: url,
        type: 'GET',
        async: false,
        cache: false,
        success: function(data) {
            status = true;
            senddata = data;
            return {'status': status, 'data': senddata};
        }, error: function(err) { 
            senddata = err.responseText;
            return {'status': status, 'data': err.responseText};
        }
      });
      return {'status': status, 'data': senddata};
}

function getTitle(image){
    var title = image['title'] ? image['title'] : image['url'] ? image['url'] : image;
    const titlelang = Array.isArray(title) && title.length > 0 ? title.filter(elem => elem['locale'] == navigator.language || elem == navigator.language) : [];
    title = titlelang.length > 0 ? titlelang[0] :Array.isArray(title) ? title[0] : title;
    if (titlelang.length == 0 && title.constructor.name == 'Object'){        
      title = title[navigator.language] ? title[navigator.language] : title[navigator.language.split('-')[0]] ? title[navigator.language.split('-')[0]] : title;
    }
    title = title['value'] ? title['value'] : title instanceof Object ? title[Object.keys(title)[0]] : title;
    return title
}

function dropdownToggle(tag) {
    document.getElementById(tag).classList.toggle("show");
}

  // // Close the dropdown if the user clicks outside of it
window.onclick = function(e) {
    if (!e.target.matches('.dropbtn') && !e.target.parentElement.matches('.dropbtn')) {
    var myDropdown = document.getElementsByClassName('dropdown-content');
        for (var i=0; i<myDropdown.length; i++){
        if (myDropdown[i].classList.contains('show')) {
            myDropdown[i].classList.remove('show');
        }
        }
    }
  }


  function checkImages(images) {
    var message = ''
    for (var i=0; i<images.files.length; i++){
        if(images.files[i].size > 100000000){
            if (message){
                message += '<br>'
            }
            message += `${images.files[i].name} is bigger than 100MB! Choose different images.`;
        }
    }
    if (message) {
        alert(message.replaceAll("<br>", "\n"))
        var imageerror = document.getElementById('imagerror');
        imageerror.innerHTML = `<i class="fas fa-exclamation-triangle"></i>${message}<i class="fas fa-exclamation-triangle"></i>`;
        document.getElementById("imagesubmit").disabled = true;
    } else {
        document.getElementById('imagerror').innerHTML = '';
        var preview = document.createElement('img');
        preview.style.height = "150px";
        var files = document.querySelector('input[type=file]').files;
        var imgpreview = document.getElementById('imagepreview');
        imgpreview.innerHTML = ''
        for (file of files) {
            if (file.size > 30453078){
                imgpreview.innerHTML += `<div><img src="" alt='${file.name} too large to preview'/>
                <figcaption style="text-align:right">${file.name}</figcaption></div>`
            } else {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.fileName = file.name;
                reader.onload = (event) => {
                const fileName = event.target.fileName;
                const content = event.currentTarget.result;
                imgpreview.innerHTML = `<div><img style="height: 150px" src="${content}"/>
                <figcaption style="text-align:right">${fileName}</figcaption></div>` + imgpreview.innerHTML
            }
            };
            if (!imgpreview.style.marginBottom){
                imgpreview.style.marginBottom = '20px';
            }
         }
        document.getElementById("imagesubmit").disabled = false;
    }
}
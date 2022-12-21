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
        }
      });
      return {'status': status, 'data': senddata};
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
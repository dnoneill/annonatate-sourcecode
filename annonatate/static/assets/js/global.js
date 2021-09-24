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
    $.ajax({url: url,
        type: 'GET',
        async: false,
        cache: false,
        success: function(data) {
            status = true;
        }
      });
      return status;
}
window.onload = function() {
    
    const defaultOpen = document.getElementById("defaultOpen");
    let params = Object.fromEntries(new URLSearchParams(window.location.search).entries());
	let tabid = params['tab'] + 'tab';
	const tab = document.getElementById(tabid)
    if (tab){
        tab.click();
    } else if (defaultOpen) {
        defaultOpen.click();
    }
}
(function(){
const button=document.getElementById('sf-code-toggle');
if(button){document.body.classList.add('sf-hide-code');button.hidden=false;
button.addEventListener('click',function(){const hidden=document.body.classList.toggle('sf-hide-code');button.textContent=hidden?'Показати код':'Приховати код';button.setAttribute('aria-pressed',hidden?'false':'true');});}
// All navigation uses native anchors; no JavaScript is required for fragment links.
}());

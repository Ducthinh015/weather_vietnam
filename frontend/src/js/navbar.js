(function(){
  async function loadNavbar(){
    try{
      const res = await fetch('/partials/navbar.html', { cache: 'no-store' });
      if(!res.ok) throw new Error('Không tải được navbar');
      const html = await res.text();
      let host = document.getElementById('navbar');
      if(!host){
        host = document.createElement('div');
        host.id = 'navbar';
        document.body.insertBefore(host, document.body.firstChild);
      }
      host.innerHTML = html;
      const scripts = host.querySelectorAll('script');
      scripts.forEach((oldScript)=>{
        const s = document.createElement('script');
        if (oldScript.type) s.type = oldScript.type;
        if (oldScript.src) {
          s.src = oldScript.src;
        } else {
          s.textContent = oldScript.textContent;
        }
        document.head.appendChild(s);
        oldScript.remove();
      });
    }catch(e){ console.error(e); }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', loadNavbar);
  else loadNavbar();
})();

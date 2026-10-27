#!/usr/bin/env python3
"""
Adds a 5th ("fifth" = black, LEFT wheel piece) and 6th ("sixth" = blue, RIGHT wheel piece)
colorway to the compiled site that is served by server.py.

Run from the repo root (the folder with server.py and assets/):
    python add_colorways.py
Safe to re-run: it rewrites its own patches, so you can change the settings below and run again.
Backups are saved once as *.bak.
"""
import json, re, shutil, sys
from pathlib import Path

ROOT = Path(".")
ASSETS = ROOT / "assets"
JS  = next(iter(sorted(ASSETS.glob("the-watch.*.js"))), None)
CSS = next(iter(sorted(ASSETS.glob("index-BDKORhKJ.css"))), None) or next(
    (p for p in ASSETS.glob("index-*.css") if "data-config=first" in p.read_text(encoding="utf-8", errors="ignore")), None)
IMG = ASSETS / "the-watch" / "img" / "images-section"
PUB = ROOT / "public" / "assets" / "the-watch" / "img" / "images-section"

# ======================= EDIT THESE SETTINGS ==================================
# Left wheel piece = "fifth", right wheel piece = "sixth".
NAMES  = {"fifth": "Bronze", "sixth": "Forest Green"}        # label shown on the page
# Metal tint. TIP: metals multiply this color into bright reflections, so use PALE, low-saturation
# tints (like the original gold #ffebc6). Dark or saturated values look muddy.
#   Other tested presets:  Ice Blue #bcd2ef | Titanium #d0d6de | Champagne Titanium #e6e0d6 | Sage #d9e6d3
METAL  = {"fifth": "#f2d7b8",     "sixth": "#c6dcc8"}
RING   = {"fifth": "#e6bd8f",     "sixth": "#a9cbb2"}        # cursor "swap" ring + wheel rim highlight
# page colors when selected: [gradient A, gradient B, text color, text gradient A, text gradient B]
THEME  = {
    "fifth": ["#7a4a2a", "#e0b48a", "#ffffff", "#e0b48a", "#7a4a2a"],
    "sixth": ["#1f4d3a", "#a9cbb2", "#ffffff", "#a9cbb2", "#1f4d3a"],
}
# Which 3D model the site uses:
#   "fs60p"  = the original model (full experience)
#   "monaco" = the converted Tag Heuer Monaco model (CC BY 4.0, credit the author). Needs the file
#              watch-monaco.glb next to this script. Sections that need the exploded-movement parts
#              (Disassembly, Mechanism, Movement, Presentation, Straps) are removed.
MODEL = "fs60p"
# Monaco only. The case/dial use the model's own texture, so each colorway is a TINT multiplied over it
# (#ffffff = the model's own colors). The strap has its own neutral texture, so its tint works like paint.
MONACO_TINT = {"first": "#ffffff", "second": "#ffffff", "third": "#ffffff",
               "fourth": "#ffffff", "fifth": "#ffffff", "sixth": "#ffffff"}
STRAP_TINT  = {"first": "#8aa0d0", "second": "#6a6a6e", "third": "#e8bd7c",
               "fourth": "#f0b89c", "fifth": "#e8a45c", "sixth": "#7cc99a"}
# ---- Monaco: STRAP section (the flat strap band) -------------------------------------
STRAP_SCALE = 17.4    # bigger number = bigger band (about 17 fills the screen width)
STRAP_Y     = -0.36   # up/down: 0 = middle of the screen, negative = lower, positive = higher
STRAP_X     = 0.0     # left/right: positive = to the right, negative = to the left
# ---- Monaco: DIAL COLOURS. For every colourway three colours: [base, light stripe, orange stripe]
#      (on the original silver dial these are the navy field, the light-blue stripe and the orange stripe).
#      Edit any hex colour and re-run. The white sub-dials, markers and printed text keep their own colours. ----
DIAL_COLORS = {
    "first":  ["#2e445a", "#4c80bd", "#df8c50"],   # silver : original navy / blue / orange
    "second": ["#545556", "#afb1b4", "#dfdcda"],   # black  : greys
    "third":  ["#322a24", "#685646", "#eacb74"],   # gold   : dark brown / brown / gold
    "fourth": ["#38272c", "#754b57", "#f5ab94"],   # rose   : burgundy / mauve / salmon
    "fifth":  ["#2d2521", "#5f4b3f", "#df9250"],   # bronze : dark brown / brown / bronze
    "sixth":  ["#24362c", "#427158", "#b4df87"],   # green  : dark green / green / lime
}
_DIAL_DEFAULTS = {   # the colours baked into the model (do not edit)
    "first":  ["#2e445a", "#4c80bd", "#df8c50"], "second": ["#545556", "#afb1b4", "#dfdcda"],
    "third":  ["#322a24", "#685646", "#eacb74"], "fourth": ["#38272c", "#754b57", "#f5ab94"],
    "fifth":  ["#2d2521", "#5f4b3f", "#df9250"], "sixth":  ["#24362c", "#427158", "#b4df87"],
}
DIAL_CUSTOM = {k: v for k, v in DIAL_COLORS.items() if [c.lower() for c in v] != _DIAL_DEFAULTS[k]}   # only the ones you changed
# ---- Monaco: extra tint on each colorway's DIAL (the dial colours themselves are baked into the model;
#      this multiplies a colour over them. #ffffff = unchanged, darker colour = darker dial) ----
DIAL_TINT = {"first": "#ffffff", "second": "#ffffff", "third": "#ffffff",
             "fourth": "#ffffff", "fifth": "#ffffff", "sixth": "#ffffff"}
# Dial tint for the original FS 60P model (#8c8c8c = original look).
DIAL   = {"first": "#8c8c8c", "second": "#8c8c8c", "third": "#8c8c8c",
          "fourth": "#8c8c8c", "fifth": "#8c8c8c", "sixth": "#8c8c8c"}
# SITE BACKGROUND for each colorway (the light page color; it fades smoothly when you swap).
# Keep these fairly light, because most text on the page is black. #ebebeb = original.
SITE_BG = {"first": "#ebebeb",   # silver
           "second": "#d9d9dd",  # deep black
           "third": "#f2e8cc",   # pure gold
           "fourth": "#f3dfd5",  # rose gold
           "fifth": "#f1e2d0",   # bronze
           "sixth": "#dde8df"}   # forest green
# Set to True ONLY if you run this with no internet. It removes the online font import
# (otherwise the page can get stuck on "Now loading" offline). Fonts then fall back.
REMOVE_TYPEKIT = False
# ==============================================================================

if MODEL == "monaco":
    TINTS = {"watch": dict(MONACO_TINT), "strap": dict(STRAP_TINT)}
else:
    TINTS = {"dial": dict(DIAL)}
TMS = list(TINTS)                       # materials that get tinted per colorway
CLONE = TMS + ([f"dface-{i}" for i in range(1, 7)] if MODEL == "monaco" else [])   # materials each bottom-row watch needs its own copy of
if JS is None or CSS is None:
    sys.exit("Could not find assets/the-watch.*.js or the CSS file. Run this from the repo root.")

def backup(p):
    b = p.with_suffix(p.suffix + ".bak")
    if not b.exists():
        shutil.copy(p, b)

backup(JS); backup(CSS)
src = JS.read_text(encoding="utf-8")

# ---- 1) colorway list ------------------------------------------------------
NEWLIST = '["first","second","third","fourth","fifth","sixth"]'
p_old = re.compile(r'\[\s*"first"\s*,\s*"second"\s*,\s*"third"\s*,\s*"fourth"\s*(?:,\s*"fifth"\s*,\s*"sixth"\s*)?\]')
if not p_old.search(src):
    sys.exit("ERROR: colorway list not found in " + JS.name)
src = p_old.sub(NEWLIST, src)
print("[js] colorway list = 6 entries")

# ---- 2) remove any earlier injected blocks (so re-running updates them) ------
src = re.sub(r'/\*extra-colorways\*/\(function\(\)\{.*?\}\)\(\);', '', src, flags=re.S)           # legacy
src = re.sub(r'/\*xc-start\*/.*?/\*xc-end\*/', '', src, flags=re.S)

# ---- 3) materials + helper functions (injected after "ls = { ...Bo };") ------
p_ls = re.compile(r'ls\s*=\s*\{\s*\.\.\.Bo\s*\}\s*;')
if not p_ls.search(src):
    sys.exit("ERROR: could not find 'ls = { ...Bo };' in " + JS.name)

HELPERS = r"""
/*xc-start*/
(function(){var m=ls.materials,C=__METAL__;for(var k in C)['metal-brushed-ext','metal-glossy-ext','single-metal-brushed','single-metal-glossy'].forEach(function(x){m[k+x]=Object.assign({},m['fourth'+x],{color:C[k]})});var T=__TINTS__;for(var nm in T){var B=Object.assign({},m[nm]||{});for(var c in T[nm])m[c+nm]=Object.assign({},B,{color:T[nm][c]});m[nm]=Object.assign({},B,{color:T[nm].first})}if(T.strap){var CF0=['first','second','third','fourth','fifth','sixth'],FT=__FT__;for(var j=1;j<=6;j++){var hx=FT[CF0[j-1]];m['dface-'+j]={color:hx};CF0.forEach(function(c){m[c+'dface-'+j]={color:hx}})}}})();
var __XC={names:__NAMES__,ring:__RING__,tints:__TINTS__,bg:__BG__,monaco:__MONACO__,strap:{scale:__SSCALE__,y:__SY__,x:__SX__},faceTint:__FT__,dialCustom:__DC__,order:['fifth','sixth']};
function __xc_dom(){
  if(document.querySelector('[data-config="fifth"]'))return;
  var NS='http://www.w3.org/2000/svg',P=function(r,a){a=a*Math.PI/180;return(350+r*Math.cos(a)).toFixed(2)+' '+(350-r*Math.sin(a)).toFixed(2)};
  var ANG={fifth:[135,225],sixth:[-45,45]};
  var prev={};
  document.querySelectorAll('[data-config="fourth"]').forEach(function(f){
    var last=f;
    __XC.order.forEach(function(id){
      var n;
      if(f.namespaceURI===NS){
        var a=ANG[id];n=document.createElementNS(NS,'g');n.setAttribute('data-config',id);
        var mk=function(cls,d,attrs){var e=document.createElementNS(NS,'path');e.setAttribute('class',cls);e.setAttribute('d',d);for(var k in attrs)e.setAttribute(k,attrs[k]);n.appendChild(e)};
        var wedge=function(r){return'M350 350 L'+P(r,a[0])+' A'+r+' '+r+' 0 0 0 '+P(r,a[1])+' Z'};
        mk('fill',wedge(345.5),{fill:'currentColor','fill-opacity':'.07'});
        mk('stroke',wedge(345),{stroke:'currentColor','stroke-opacity':'.1'});
        mk('border','M'+P(343.5,a[0])+' A343.5 343.5 0 0 0 '+P(343.5,a[1]),{stroke:'#fff','stroke-width':'3'});
      }else{
        n=f.cloneNode(true);n.setAttribute('data-config',id);n.classList.remove('selected');
        var par=f.parentNode,isNum=par&&par.classList.contains('config-w');
        var txt=isNum?('0'+(id==='fifth'?5:6)):__XC.names[id];
        var w=document.createTreeWalker(n,NodeFilter.SHOW_TEXT),t=w.nextNode();
        if(t){t.nodeValue=txt}else{n.textContent=txt}
      }
      last.parentNode.insertBefore(n,last.nextSibling);last=n;
    });
  });
  document.querySelectorAll('.counter div').forEach(function(d){if(d.children.length===0&&/\/\s*0?4/.test(d.textContent))d.textContent=' / 06'});
}
function __xc_cursor(el){
  var inside=el.querySelector('.inside');if(!inside||inside.querySelector('[data-icon="fifth"]'))return;
  var src=inside.querySelector('[data-icon="fourth"]');if(!src)return;
  __XC.order.forEach(function(id){
    var c=src.cloneNode(true);c.setAttribute('data-icon',id);c.classList.remove('visible');
    c.querySelectorAll('ellipse').forEach(function(e){e.setAttribute('stroke',__XC.ring[id])});
    src.parentNode.appendChild(c);
  });
}
function __xc_strapMake(sec){
  var sc=d.webgl&&d.webgl.scene,w=sc&&sc.watch,hero=w&&w.getObjectByName('monaco-strap'),flat=d.assetsManager.get('model').getObjectByName('strap-flat');
  if(!hero||!flat)return false;
  var m=flat.clone();m.material=hero.material;m.frustumCulled=false;
  var wrap=new As;wrap.add(m);wrap.visible=false;d.webgl.scene.add(wrap);sec.strapWrap=wrap;return true;
}
function __xc_strapInit(sec){
  sec.hoverIntensity=0;sec.sv={on:0};
  sec.sst={x:__XC.strap.x+3.4,y:__XC.strap.y,z:0,rx:1.25,ry:0,rz:0,s:__XC.strap.scale};
  __xc_strapMake(sec);
}
function __xc_strapUpdate(sec){
  if(!sec.strapWrap&&!__xc_strapMake(sec))return;
  var t=sec.sst,w=sec.strapWrap;w.position.set(t.x,t.y,t.z);w.rotation.set(t.rx,t.ry,t.rz);w.scale.setScalar(t.s);
}
function __xc_strapTl(sec,e){
  var t=sec.sst;
  var vis=function(){if(!sec.strapWrap)__xc_strapMake(sec);if(sec.strapWrap)sec.strapWrap.visible=sec.sv.on>.5};
  e.to(sec.sv,{on:1,duration:.05,onUpdate:vis,onComplete:vis,onReverseComplete:vis},0);
  var ox=__XC.strap.x;
  e.to(t,{x:ox,duration:.4,ease:'power2.out'},0);
  e.to(t,{rx:0,duration:.4,ease:'power3.out'},0);
  e.to(t,{x:ox-0.12,duration:.2,ease:'none'},.4);
  e.to(t,{x:ox-3.6,duration:.3,ease:'power2.in'},.6);
  e.to(t,{rx:-1.25,duration:.3,ease:'power2.in'},.6);
  e.to(sec.sv,{on:0,duration:.05,onUpdate:vis,onComplete:vis,onReverseComplete:vis},.95);
}
function __xc_dialRecolor(cfg,cols){
  var sc=d.webgl&&d.webgl.scene;if(!sc||!sc.watch)return false;
  var CFn=['first','second','third','fourth','fifth','sixth'],k=CFn.indexOf(cfg)+1;if(!k)return false;
  var tex=null,t1=null;
  sc.watch.traverse(function(o){var q=/dface-(\d)$/.exec(o.name||'');if(q&&o.isMesh&&o.material&&o.material.map){if(+q[1]===k)tex=o.material.map;if(+q[1]===1)t1=o.material.map}});
  if(!tex||!t1)return false;
  var O=__XC.origPix;
  if(!O){
    var im=t1.image,cv=document.createElement('canvas');cv.width=im.width;cv.height=im.height;var cx=cv.getContext('2d');cx.drawImage(im,0,0);
    var id=cx.getImageData(0,0,cv.width,cv.height),W=cv.width,H=cv.height,D=new Uint8ClampedArray(id.data),N=W*H,fam=new Int8Array(N),vv=new Float32Array(N);
    for(var i=0;i<N;i++){var r=D[4*i]/255,g=D[4*i+1]/255,b=D[4*i+2]/255,mx=Math.max(r,g,b),mn=Math.min(r,g,b),dd=mx-mn,h=0;
      if(dd){if(mx===r)h=((g-b)/dd)%6;else if(mx===g)h=(b-r)/dd+2;else h=(r-g)/dd+4;h*=60;if(h<0)h+=360}
      var sat=mx?dd/mx:0;vv[i]=mx;var f=-1;if(sat>=0.2&&mx>=0.06){if(h>=185&&h<=265)f=mx<0.55?0:1;else if(h<=60||h>=335)f=2}fam[i]=f}
    var bins=[[],[],[]],x0=Math.round(W*500/1024),x1=Math.round(W*850/1024),y0=Math.round(H*450/1024),y1=Math.round(H*720/1024);
    for(var y=y0;y<y1;y++)for(var x=x0;x<x1;x++){var p=y*W+x,f2=fam[p];if(f2>=0)bins[f2].push(vv[p])}
    var vm=bins.map(function(a){a.sort(function(u,w){return u-w});return a.length?a[a.length>>1]:0.6});
    O=__XC.origPix={w:W,h:H,d:D,fam:fam,v:vv,vm:vm};
  }
  var T=cols.map(function(h){h=h.replace('#','');return[parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)]});
  var out=document.createElement('canvas');out.width=O.w;out.height=O.h;var oc=out.getContext('2d'),od=oc.createImageData(O.w,O.h),R=od.data,S=O.d,N2=O.w*O.h;
  for(var j=0;j<N2;j++){var ff=O.fam[j],q4=4*j;
    if(ff<0){R[q4]=S[q4];R[q4+1]=S[q4+1];R[q4+2]=S[q4+2]}
    else{var fac=O.v[j]/O.vm[ff];if(fac<0.3)fac=0.3;else if(fac>1.6)fac=1.6;var c=T[ff];R[q4]=c[0]*fac;R[q4+1]=c[1]*fac;R[q4+2]=c[2]*fac}
    R[q4+3]=S[q4+3]}
  oc.putImageData(od,0,0);tex.image=out;tex.needsUpdate=true;return true;
}
function __xc_secRot(){var t=new Date();return -((t.getSeconds()+t.getMilliseconds()/1000)/60)*2*Math.PI}
function __xc_minRot30(){var t=new Date();return -(((t.getMinutes()%30)+t.getSeconds()/60)/30)*2*Math.PI}
function __xc_m(){return __XC.monaco?-1:1}
function __xc_prune(){
  if(!__XC.monaco||__XC.pruned)return;__XC.pruned=true;
  var S=[],G=[];
  document.querySelectorAll('#the-watch [data-section],#the-watch [data-webgl]').forEach(function(e){
    if(S.indexOf(e.dataset.section)>=0||G.indexOf(e.dataset.webgl)>=0)e.remove();
  });

  /* credit required by the model's CC BY 4.0 license */
  if(!document.getElementById('xc-credit')){var c=document.createElement('div');c.id='xc-credit';
    c.style.cssText='position:fixed;right:14px;bottom:8px;z-index:9;font:11px/1.3 Inter,sans-serif;opacity:.65;color:#222;text-align:right;max-width:60vw';
    c.innerHTML='3D model \u201cTag Heuer Monaco X GULF Watch\u201d by <a href="https://sketchfab.com/ar-watches" target="_blank" rel="noopener" style="color:inherit">ar-watches</a> \u2014 <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener" style="color:inherit">CC BY 4.0</a>';
    document.body.appendChild(c)}
}
function __xc_dial(){
  if(__XC.dialHooked)return;__XC.dialHooked=true;
  var mats=function(root,name){var out=[];root&&root.traverse(function(o){if(o.material&&o.material.name===name&&out.indexOf(o.material)<0)out.push(o.material)});return out};
  var apply=function(cfg,dur){
    var w=d.webgl&&d.webgl.scene&&d.webgl.scene.watch;
    for(var nm in __XC.tints){var hex=__XC.tints[nm][cfg];if(!hex)continue;
      mats(w,nm).forEach(function(m){var t=new m.color.constructor(hex);oe.to(m.color,{r:t.r,g:t.g,b:t.b,duration:dur,ease:'power3.inOut'})});}
  };
  var rgb=function(h){h=h.replace('#','');if(h.length===3)h=h.replace(/./g,function(c){return c+c});return{r:parseInt(h.slice(0,2),16),g:parseInt(h.slice(2,4),16),b:parseInt(h.slice(4,6),16)}};
  var cur=rgb(__XC.bg.first||'#ebebeb');
  var paint=function(){document.documentElement.style.setProperty('--site-bg-rgb',Math.round(cur.r)+','+Math.round(cur.g)+','+Math.round(cur.b))};
  var bg=function(cfg,dur){
    var hex=__XC.bg[cfg];if(!hex)return;var t=rgb(hex);
    oe.killTweensOf(cur);
    if(!dur){cur.r=t.r;cur.g=t.g;cur.b=t.b;paint();return}
    oe.to(cur,{r:t.r,g:t.g,b:t.b,duration:dur*1.2,ease:'power3.inOut',onUpdate:paint});
  };
  paint();
  /* per-colorway dial faces (monaco model): only the face of the current colorway is visible */
  var CF=['first','second','third','fourth','fifth','sixth'];
  var faceIdx=function(name){var q=/dface-(\d)$/.exec(name||'');return q?+q[1]:0};
  var swapFace=function(cfg,du){
    var sc=d.webgl&&d.webgl.scene,w=sc&&sc.watch;if(!w)return;var k=CF.indexOf(cfg)+1,cur=[],nxt=null;
    w.traverse(function(o){var i=faceIdx(o.name);if(!i||!o.isMesh)return;if(i===k)nxt=o;else if(o.visible)cur.push(o)});
    if(!nxt||(nxt.visible&&!cur.length))return;
    if(!du){cur.forEach(function(o){o.visible=false});nxt.visible=true;return}
    var half=du*.5,tc=function(o){var h=__XC.faceTint[CF[faceIdx(o.name)-1]]||'#ffffff';return new o.material.color.constructor(h)};
    cur.forEach(function(o){var c=o.material.color,t=tc(o);oe.to(c,{r:0,g:0,b:0,duration:half,ease:'power2.in',onComplete:function(){o.visible=false;c.setRGB(t.r,t.g,t.b)}})});
    var tn=tc(nxt);nxt.material.color.setRGB(0,0,0);nxt.visible=true;oe.to(nxt.material.color,{r:tn.r,g:tn.g,b:tn.b,duration:half,delay:half,ease:'power2.out'});
  };
  var initFaces=function(){
    for(var cc in __XC.dialCustom)try{__xc_dialRecolor(cc,__XC.dialCustom[cc])}catch(e){}
    var sc=d.webgl.scene,g=sc.watchesGroup&&sc.watchesGroup.watchesInsideGroup;
    g&&g.traverse(function(o){var k=faceIdx(o.name);if(!k||!o.isMesh||!o.material)return;var cfg=o.material.name.replace(/dface-\d$/,'');o.visible=(CF.indexOf(cfg)+1===k)});
    var cur=d.store.get(Ke.CURRENT_CONFIG)||'first';
    sc.watch.traverse(function(o){var k=faceIdx(o.name);if(k&&o.isMesh)o.visible=(CF.indexOf(cur)+1===k)});
  };
  if(__XC.monaco){var tries=0,iv=setInterval(function(){var sc=d.webgl&&d.webgl.scene;tries++;
    if(sc&&sc.watch&&sc.watchesGroup&&sc.watchesGroup.watchesInsideGroup&&sc.watchesGroup.watchesInsideGroup.children.length){clearInterval(iv);initFaces()}else if(tries>100)clearInterval(iv)},200)}
  window.xcSwapDial=function(cfg,du){swapFace(cfg,du==null?1:du)};
  /* live tuning: xcSetFace('third','#ffcc88') tints that colourway's dial */
  window.xcSetDialColors=function(cfg,cols){return __xc_dialRecolor(cfg,cols)};
  window.xcSetFace=function(cfg,hex){var k=CF.indexOf(cfg)+1;if(!k)return;__XC.faceTint[cfg]=hex;
    var sc=d.webgl&&d.webgl.scene,paint=function(root,test){root&&root.traverse(function(o){if(o.isMesh&&o.material&&test(o))o.material.color.set(hex)})};
    paint(sc.watch,function(o){return faceIdx(o.name)===k});
    paint(sc.watchesGroup&&sc.watchesGroup.watchesInsideGroup,function(o){return faceIdx(o.name)===k});};
  d.state.on(L.CONFIG_CHANGE,function(e){var du=e.duration==null?1:e.duration;apply(e.configName,du);bg(e.configName,du);if(__XC.monaco)swapFace(e.configName,du)});
  /* preview a metal color on the main watch: xcMetal('#a4a9b2')  (temporary until you swap) */
  window.xcMetal=function(hex){var w=d.webgl&&d.webgl.scene&&d.webgl.scene.watch,K=['metal-brushed-ext','metal-glossy-ext','single-metal-brushed','single-metal-glossy'];
    w&&w.traverse(function(o){if(o.material&&K.indexOf(o.material.name)>=0)o.material.color.set(hex)})};
  window.xcSetBg=function(cfg,hex){__XC.bg[cfg]=hex;if(d.store.get(Ke.CURRENT_CONFIG)===cfg)bg(cfg,0)};
  /* live tuning from the browser console: xcSetDial('fifth','#334455') / xcSetStrap('fifth','#aa7733') */
  var setTint=function(nm,cfg,hex){
    if(!__XC.tints[nm])return;__XC.tints[nm][cfg]=hex;
    var sc=d.webgl&&d.webgl.scene,g=sc&&sc.watchesGroup&&sc.watchesGroup.watchesInsideGroup;
    g&&g.traverse(function(o){if(o.material&&o.material.name===cfg+nm)o.material.color.set(hex)});
    if(d.store.get(Ke.CURRENT_CONFIG)===cfg)apply(cfg,0);
  };
  window.xcSetDial=function(cfg,hex){setTint(Object.keys(__XC.tints)[0],cfg,hex)};
  window.xcSetStrap=function(cfg,hex){setTint('strap',cfg,hex)};
}
/*xc-end*/
""".replace('__MONACO__', 'true' if MODEL == 'monaco' else 'false').replace('__SSCALE__', repr(STRAP_SCALE)).replace('__SY__', repr(STRAP_Y)).replace('__SX__', repr(STRAP_X)).replace('__FT__', json.dumps(DIAL_TINT)).replace('__DC__', json.dumps(DIAL_CUSTOM)).replace('__BG__', json.dumps(SITE_BG)).replace('__TINTS__', json.dumps(TINTS)).replace('__FT__', json.dumps(DIAL_TINT)).replace('__METAL__', json.dumps(METAL)).replace('__NAMES__', json.dumps(NAMES)).replace('__RING__', json.dumps(RING))
src = p_ls.sub(lambda m: m.group(0) + HELPERS, src, count=1)
print("[js] injected materials + wheel/cursor helpers")

# ---- 4) call the helpers at the right moments --------------------------------
def show_context(needle, what):
    print("ERROR: could not find the %s code in %s (your file differs from the one I tested)." % (what, JS.name))
    i = src.find(needle)
    if i >= 0:
        print("Please send me this text from your file so I can match it:")
        print("-----")
        print(src[max(0, i - 250): i + 350])
        print("-----")
    sys.exit(1)

def has_call(name):
    return (name + "(") in src.replace("function " + name + "(", "")

# 4a) wheel: build the extra pieces just before the wheel code reads the DOM
if not has_call("__xc_dom"):
    pat = re.compile(r'(this\.contentWrapper\s*=\s*this\.el\.querySelector\(\s*["\']\.content-wrapper["\']\s*\)\s*,\s*this\.configs)')
    if pat.search(src):
        src = pat.sub(lambda m: '__xc_dom(), ' + m.group(1), src, count=1)
        print("[js] wheel now builds the extra pieces")
    else:
        show_context("content-wrapper", "wheel")
# 4b) cursor: add the swap icons before the cursor reads its icon list
if not has_call("__xc_cursor"):
    pat = re.compile(r'(this\.icons\s*=\s*Array\.from\(\s*this\.el\.querySelectorAll\(\s*["\']\.inside \[data-icon\]["\']\s*\)\s*\))')
    if pat.search(src):
        src = pat.sub(lambda m: '__xc_cursor(this.el), ' + m.group(1), src, count=1)
        print("[js] cursor now has swap icons for the new colors")
    else:
        show_context("data-icon]", "cursor")

# 4c) bottom-row watches: give each watch its own copy of the tinted material
src = re.sub(r'\(\s*Ki\.includes\(\s*v\.material\.name\s*\)\s*\|\|\s*(?:v\.material\.name\s*===\s*(?:"[^"]*"|\'[^\']*\')|\[[^\]]*\]\.includes\(\s*v\.material\.name\s*\))\s*\)', 'Ki.includes(v.material.name)', src)
p_aw = re.compile(r'(v\.material\s*&&\s*)Ki\.includes\(\s*v\.material\.name\s*\)(\s*\)\s*\{\s*if\s*\(\s*r\.includes\(\s*v\.material\.name\s*\)\s*\)\s*return)')
if p_aw.search(src):
    src = p_aw.sub(lambda m: m.group(1) + '(Ki.includes(v.material.name)||' + json.dumps(CLONE) + '.includes(v.material.name))' + m.group(2), src, count=1)
    print("[js] every watch now has its own copy of: " + ", ".join(CLONE))
else:
    show_context("addWatches", "watch-row")

# 4e) skip sections that cannot work without the exploded-movement parts (monaco only; no-op otherwise)
p1 = re.compile(r'(this\.el\s*=\s*document\.querySelector\(\s*"#the-watch"\s*\)\s*;\s*)(const\s+t\s*=\s*Array\.from\(this\.el\.querySelectorAll\()')
p2 = re.compile(r'(this\.sections\s*=\s*Array\.from\(document\.querySelectorAll\(`\[data-\$\{this\.selector\}\]`\)\))')
if "__xc_prune()" not in src.replace("function __xc_prune()", ""):
    if p1.search(src) and p2.search(src):
        src = p1.sub(lambda m: m.group(1) + '__xc_prune(); ' + m.group(2), src, count=1)
        src = p2.sub(lambda m: '__xc_prune(), ' + m.group(1), src, count=1)
        print("[js] section pruning hooks installed")
    else:
        show_context("data-${this.selector}", "section-list")
# 4h) Straps section: show the REAL strap of the model (monaco only; the original code runs for other models)
if "__xc_strapInit(" not in src.replace("function __xc_strapInit(", ""):
    p_ctor = re.compile(r'(this\.progressWebgl\s*<=\s*0\s*\|\|\s*this\.progressWebgl\s*>=\s*1\s*\|\|\s*this\._updateMatrices\(\)\s*\}\)\s*;)')
    p_upd = re.compile(r'(_updateMatrices\(\)\s*\{)(\s*this\.instances\.forEach)')
    p_tl = re.compile(r'(braceletTl\(e\)\s*\{)')
    if p_ctor.search(src) and p_upd.search(src) and p_tl.search(src):
        src = p_ctor.sub(lambda m: m.group(1) + ' if (__XC.monaco) { __xc_strapInit(this); return; }', src, count=1)
        src = p_upd.sub(lambda m: m.group(1) + ' if (__XC.monaco) return __xc_strapUpdate(this);' + m.group(2), src, count=1)
        src = p_tl.sub(lambda m: m.group(1) + ' if (__XC.monaco) return __xc_strapTl(this, e);', src, count=1)
        print("[js] Straps section can show the real strap")
    else:
        show_context("braceletTl", "straps-section")

# 4i) start the seconds hand and the sub-dial needles at the real time (monaco only; removed again for other models)
p_s_old = re.compile(r'"dial-xploded-2":\s*__xc_secRot\(\),\s*"dial-xploded-6":\s*__xc_secRot\(\),\s*"dial-xploded-7":\s*__xc_minRot30\(\),\s*')
src = p_s_old.sub('', src)
if MODEL == "monaco":
    p_s = re.compile(r'(_s\s*=\s*\{\s*)(?="dial-xploded-4")')
    if p_s.search(src):
        src = p_s.sub(lambda m: m.group(1) + '"dial-xploded-2": __xc_secRot(), "dial-xploded-6": __xc_secRot(), "dial-xploded-7": __xc_minRot30(), ', src, count=1)
        print("[js] seconds hand starts at the real second")
    else:
        print("[js] note: hand start-angle table not found (hands still run)")

# 4g) side view: the original round watch has its crown on the RIGHT, the Monaco on the LEFT -> mirror the turn
mir_done = "__xc_m()" in src.replace("function __xc_m()", "")
if not mir_done:
    reps = [
      (r'y:\s*Math\.PI\s*\*\s*2,\s*x:\s*0,\s*duration:\s*\.2', 'y: Math.PI * 2 * __xc_m(), x: 0, duration: .2'),
      (r'z:\s*Math\.PI\s*\*\s*-\.5,\s*x:\s*Math\.PI\s*\*\s*-\.6', 'z: Math.PI * -.5 * __xc_m(), x: Math.PI * -.6'),
      (r'z:\s*Math\.PI\s*\*\s*-\.5,\s*x:\s*Math\.PI\s*\*\s*-\.5,\s*y:\s*Math\.PI\s*\*\s*2\s*\}', 'z: Math.PI * -.5 * __xc_m(), x: Math.PI * -.5, y: Math.PI * 2 * __xc_m() }'),
    ]
    ok = 0
    for pat, rep in reps:
        if re.search(pat, src):
            src = re.sub(pat, rep, src, count=1); ok += 1
    print("[js] side-view turn can mirror for the Monaco (%d/3 spots)" % ok)

# 4f) tolerate a model without the tourbillon parts (safe for every model)
p3 = re.compile(r'(this\.watchParts\.hairSpring\.scale\.x\s*=\s*ss,\s*this\.watchParts\.hairSpring\.scale\.y\s*=\s*ss,\s*this\.watchParts\.hairSpring\.rotation\.z\s*=\s*Math\.sin\(e\s*\*\s*20\),\s*this\.watchParts\.balanceWheel\.rotation\.z\s*=\s*ss\s*\*\s*4)')
if p3.search(src):
    src = p3.sub(lambda m: '(this.watchParts.hairSpring && this.watchParts.balanceWheel) && (' + m.group(1) + ')', src, count=1)
    print("[js] per-frame animation made safe for models without tourbillon parts")

# 4d) main watch: tint the dial when the colorway changes
if not has_call("__xc_dial"):
    pat = re.compile(r'(d\.state\.on\(\s*L\.CONFIG_CHANGE\s*,\s*this\.onConfigChange\s*\))')
    if pat.search(src):
        src = pat.sub(lambda m: m.group(1) + ', __xc_dial()', src, count=1)
        print("[js] main watch dial now changes with the colorway")
    else:
        show_context("CONFIG_CHANGE", "colorway-change")

# ---- 5) page theme table (background/text colors per colorway) ---------------
p_ot = re.compile(r'(fourth\s*:\s*\[\s*"#D7CFC8"[^\]]*\])(?:\s*,\s*fifth\s*:\s*\[[^\]]*\]\s*,\s*sixth\s*:\s*\[[^\]]*\])?')
if not p_ot.search(src):
    sys.exit("ERROR: theme color table not found")
src = p_ot.sub(lambda m: m.group(1) + ', fifth: ' + json.dumps(THEME["fifth"]) + ', sixth: ' + json.dumps(THEME["sixth"]), src, count=1)
print("[js] theme colors added")
JS.write_text(src, encoding="utf-8")

# ---- 6) CSS for the two new wheel pieces ---------------------------------------
css = CSS.read_text(encoding="utf-8")
css = re.sub(r'/\*xc-css-start\*/.*?/\*xc-css-end\*/', '', css, flags=re.S)
_bg = SITE_BG["first"].lstrip("#")
_bg = ",".join(str(int(_bg[i:i+2], 16)) for i in (0, 2, 4))
extra = """/*xc-css-start*/
:root{--site-bg-rgb:%s}
#the-watch{background:rgb(var(--site-bg-rgb))}
[data-section=VerticalText]:before{background-image:linear-gradient(180deg,rgb(var(--site-bg-rgb)),rgba(var(--site-bg-rgb),.3) 50%%,rgba(var(--site-bg-rgb),.149) 65%%,rgba(var(--site-bg-rgb),.075) 75.5%%,rgba(var(--site-bg-rgb),.035) 82.85%%,rgba(var(--site-bg-rgb),.02) 88%%,rgba(var(--site-bg-rgb),0))}
[data-section=Colors]{background:linear-gradient(to bottom,rgb(var(--site-bg-rgb)) 0%%,transparent 22%%,transparent 75%%,rgb(var(--site-bg-rgb)) 100%%),linear-gradient(70deg,var(--first-color) 0%%,var(--second-color) 100%%)}
.circle-svg [data-config=fifth] .border,.circle-svg [data-config=sixth] .border{stroke-dasharray:545 545;stroke-dashoffset:545}
.circle-svg [data-config=fifth] .stroke,.circle-svg [data-config=sixth] .stroke{stroke-dasharray:1240 1240;stroke-dashoffset:1240}
.circle-svg [data-config=fifth].selected .border,.circle-svg [data-config=sixth].selected .border{stroke-dashoffset:0}
@media (hover: hover) and (pointer: fine){.circle-svg [data-config=fifth]:hover .border,.circle-svg [data-config=sixth]:hover .border{stroke-dashoffset:0!important}}
.circle-svg [data-config=fifth] .border{stroke:%s}
.circle-svg [data-config=sixth] .border{stroke:%s}
/*xc-css-end*/""" % (_bg, RING["fifth"], RING["sixth"])
if REMOVE_TYPEKIT:
    css = re.sub(r'@import\s*"https://use\.typekit\.net/[^"]*";?', '', css)
    print("[css] removed online font import (offline mode)")
CSS.write_text(css.rstrip() + "\n" + extra + "\n", encoding="utf-8")
print("[css] added styles for the left/right wheel pieces")

# ---- 6b) swap the 3D model file ----------------------------------------------------
GLB = ASSETS / "watch-DXFPNOEl.glb"
if MODEL == "monaco":
    mine = Path(__file__).resolve().parent / "watch-monaco.glb"
    if not mine.exists():
        mine = ROOT / "watch-monaco.glb"
    if not mine.exists():
        sys.exit("ERROR: MODEL is 'monaco' but watch-monaco.glb was not found next to the script.")
    orig = GLB.with_suffix(".glb.orig")
    if not orig.exists():
        shutil.copy(GLB, orig)
    shutil.copy(mine, GLB)
    print("[model] using the Monaco model")
else:
    orig = GLB.with_suffix(".glb.orig")
    if orig.exists():
        shutil.copy(orig, GLB)
        print("[model] restored the original FS 60P model")

# ---- 6c) text of the Straps section ---------------------------------------------------
for lang in sorted(ASSETS.glob("en_GB.*.js")) + sorted(ASSETS.glob("fr_FR.*.js")):
    txt = lang.read_text(encoding="utf-8")
    bak = lang.with_suffix(".js.orig")
    if not bak.exists():
        shutil.copy(lang, bak)
    txt = bak.read_text(encoding="utf-8")
    if MODEL == "monaco":
        txt = txt.replace("polished links, the bracelet combines durability with comfort, perfectly complementing the watch\u2019s design",
                          "perforated suede leather, the strap combines comfort with durability, perfectly complementing the watch\u2019s design")
        txt = txt.replace("polished links, the bracelet combines durability with comfort, perfectly complementing the watch’s design",
                          "perforated suede leather, the strap combines comfort with durability, perfectly complementing the watch’s design")
        txt = txt.replace('"Bracelet"', '"Strap"')
    lang.write_text(txt, encoding="utf-8")

# ---- 7) images (placeholders until you add real renders) ---------------------
IMG.mkdir(parents=True, exist_ok=True)
for name in ("fifth", "sixth"):
    for i in range(1, 6):
        dst = IMG / f"{name}_{i}.webp"
        if dst.exists():
            continue
        s_img = PUB / f"{name}_{i}.webp"
        if not s_img.exists():
            s_img = IMG / f"fourth_{i}.webp"
        shutil.copy(s_img, dst)
        print(f"[img] created {dst.name} (placeholder - replace with a real render)")

print("\nDone. Restart server.py and hard-refresh (Ctrl+Shift+R).")
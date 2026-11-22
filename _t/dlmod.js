/* ==================== 选集操作：播放 / 收藏 / 下载 ==================== */
var DLM={busy:false,ctrl:null,rec:null,recChunks:[],recT0:0,recTimer:0,mime:""};
var DLS={bytes:0,total:0,t0:0,lastT:0,lastB:0,speed:0};

function dlBytes(n){n=n||0;if(n<1024)return n+" B";if(n<1048576)return (n/1024).toFixed(0)+" KB";if(n<1073741824)return (n/1048576).toFixed(1)+" MB";return (n/1073741824).toFixed(2)+" GB";}
function dlSpeed(b){return b>0?dlBytes(b)+"/s":"—";}
function dlDur(s){s=Math.max(0,Math.round(s));var m=Math.floor(s/60);return m+":"+(s%60<10?"0":"")+(s%60);}
function dlName(ext){
  var t=(playerItem&&playerItem.vod_name)||"video";
  t=t.replace(/[\\/:*?"<>|\s]+/g,"_").slice(0,60);
  return t+"_第"+(playerEp+1)+"集."+ext;
}

function dlsReset(){DLS={bytes:0,total:0,t0:performance.now(),lastT:0,lastB:0,speed:0};}
function dlsAdd(n,total){
  if(total)DLS.total=total;
  DLS.bytes+=n;
  var now=performance.now();
  if(now-DLS.lastT>350){DLS.speed=(DLS.bytes-DLS.lastB)/((now-DLS.lastT)/1000);DLS.lastT=now;DLS.lastB=DLS.bytes;}
}

/* ---------- 网络 ---------- */
async function dlFetchBytes(url,signal,onChunk){
  var res=await fetch(url,{signal:signal,credentials:"omit",cache:"no-store",referrerPolicy:"no-referrer"});
  if(!res.ok)throw new Error("HTTP "+res.status);
  var total=+res.headers.get("content-length")||0;
  if(!res.body){var ab=await res.arrayBuffer();var u0=new Uint8Array(ab);onChunk&&onChunk(u0.length,total);return u0;}
  var reader=res.body.getReader(),parts=[],got=0;
  for(;;){
    var r=await reader.read();
    if(r.done)break;
    parts.push(r.value);got+=r.value.length;
    onChunk&&onChunk(r.value.length,total||0);
  }
  var out=new Uint8Array(got),off=0;
  parts.forEach(function(p){out.set(p,off);off+=p.length;});
  return out;
}
async function dlText(url,signal){
  var res=await fetch(url,{signal:signal,credentials:"omit",cache:"no-store",referrerPolicy:"no-referrer"});
  if(!res.ok)throw new Error("HTTP "+res.status);
  return res.text();
}
function dlConcat(list){
  var n=0;list.forEach(function(u){if(u)n+=u.length});
  var out=new Uint8Array(n),off=0;
  list.forEach(function(u){if(u){out.set(u,off);off+=u.length;}});
  return out;
}
function dlSave(u8,ext,type){
  var blob=new Blob([u8],{type:type||"application/octet-stream"});
  dlSaveBlob(blob,ext);
}
function dlSaveBlob(blob,ext){
  var a=document.createElement("a"),u=URL.createObjectURL(blob);
  a.href=u;a.download=dlName(ext);document.body.appendChild(a);a.click();
  setTimeout(function(){URL.revokeObjectURL(u);a.remove();},4000);
}

/* ---------- M3U8 ---------- */
function m3u8Parse(text,base){
  var lines=text.split(/\r?\n/),segs=[],variants=[],mapUrl="",dur=0,bw=0,res="";
  for(var i=0;i<lines.length;i++){
    var l=lines[i].trim();
    if(!l)continue;
    if(l.indexOf("#EXT-X-STREAM-INF")===0){
      var mb=/BANDWIDTH=(\d+)/.exec(l);bw=mb?+mb[1]:0;
      var mr=/RESOLUTION=(\d+)x(\d+)/.exec(l);res=mr?mr[2]:"";continue;
    }
    if(l.indexOf("#EXT-X-MAP")===0){
      var mm=/URI="([^"]+)"/.exec(l);if(mm)mapUrl=new URL(mm[1],base).href;continue;
    }
    if(l.indexOf("#EXTINF:")===0){var md=/,([\d.]+)/.exec(l.slice(8));if(md)dur+=parseFloat(md[1]);continue;}
    if(l.charAt(0)==="#")continue;
    var abs=new URL(l,base).href;
    if(bw){variants.push({url:abs,bandwidth:bw,height:res});bw=0;res="";}
    else segs.push(abs);
  }
  return {isMaster:variants.length>0,variants:variants,segs:segs,map:mapUrl,duration:dur,live:text.indexOf("#EXT-X-ENDLIST")<0};
}

async function dlSegments(urls,signal,onEach){
  var out=new Array(urls.length),idx=0,done=0,err=null;
  async function worker(){
    while(true){
      if(err)return;
      var k=idx++;if(k>=urls.length)return;
      try{
        out[k]=await dlFetchBytes(urls[k],signal,function(n){onEach&&onEach(done,urls.length,n);});
        done++;onEach&&onEach(done,urls.length,0);
      }catch(e){err=e;return;}
    }
  }
  var pool=[];for(var i=0;i<Math.min(4,urls.length);i++)pool.push(worker());
  await Promise.all(pool);
  if(err)throw err;
  return out;
}

/* ts → fMP4 转封装（mux.js 按需加载） */
function dlLoadMux(){
  return new Promise(function(res){
    if(window.muxjs)return res(true);
    var s=document.createElement("script");
    s.src="https://cdn.jsdelivr.net/npm/mux.js@7.1.0/dist/mux.min.js";
    s.onload=function(){res(!!window.muxjs);};
    s.onerror=function(){res(false);};
    document.head.appendChild(s);
    setTimeout(function(){res(!!window.muxjs);},12000);
  });
}
async function dlRemux(segs,onProg){
  var ok=await dlLoadMux();
  if(!ok)return null;
  return new Promise(function(res){
    var t=new muxjs.mp4.Transmuxer({keepOriginalTimestamps:true}),init=null,parts=[];
    t.on("data",function(seg){
      if(seg.initSegment&&!init)init=seg.initSegment;
      if(seg.data)parts.push(seg.data);
    });
    t.on("done",function(){res(dlConcat([init].concat(parts)));});
    (async function(){
      for(var i=0;i<segs.length;i++){
        t.push(segs[i]);
        onProg(i+1,segs.length);
        if(i%6===5)await new Promise(function(r){setTimeout(r,0);});
      }
      t.flush();
    })();
  });
}

/* ---------- 下载面板 ---------- */
function dlEl(id){return document.getElementById(id);}
function dlSetStage(kind,title,note){
  dlEl("dlStageTitle").textContent=title;
  dlEl("dlStageNote").textContent=note||"";
  dlEl("dlStageIcon").setAttribute("icon",kind||"lucide:download-cloud");
}
function dlSetBar(pct){
  dlEl("dlBarFill").style.width=Math.max(0,Math.min(100,pct||0))+"%";
}
function dlSetMeta(a,b,c){
  dlEl("dlMetaA").textContent=a||"";dlEl("dlMetaB").textContent=b||"";dlEl("dlMetaC").textContent=c||"";
}
function dlSetBusy(on){
  DLM.busy=on;
  dlEl("dlCancel").textContent=on?"取消":"关闭";
  dlEl("dlOpts").style.display=on?"none":"";
  dlEl("dlProg").style.display=on?"":"none";
}
function dlOpen(){
  var src=(playerSources[playerSrc]||[])[playerEp]||{};
  var url=src.url||"";
  var isHls=/\.m3u8(\?|$)/i.test(url)||playerCurM3u8;
  var isMp4=/\.mp4(\?|$)/i.test(url);
  dlEl("dlSub").textContent=((playerItem&&playerItem.vod_name)||"")+" · 第"+(playerEp+1)+"集";
  dlEl("optM3u8").classList.toggle("disabled",!isHls);
  dlEl("optM3u8").querySelector(".dl-opt-note").textContent=isHls?"抓取全部分片，转封装为 MP4":"当前源不是 HLS 流，无可抓取分片";
  dlEl("optMp4").classList.toggle("disabled",!isMp4);
  dlEl("optMp4").querySelector(".dl-opt-note").textContent=isMp4?"直接下载源文件，速度取决于服务器":"当前源是 HLS 流，没有 MP4 直链";
  var recOk=!!(videoEl&&videoEl.captureStream&&window.MediaRecorder);
  dlEl("optWebm").classList.toggle("disabled",!recOk);
  dlEl("optWebm").querySelector(".dl-opt-note").textContent=recOk?"实时录制当前画面与声音，边看边存":"当前浏览器不支持录制";
  dlSetBusy(false);
  dlEl("dlModal").classList.add("show");
}
function dlClose(){
  if(DLM.busy){dlCancel();return;}
  dlEl("dlModal").classList.remove("show");
}
function dlCancel(){
  if(DLM.ctrl){try{DLM.ctrl.abort();}catch(e){}}
  if(DLM.rec&&DLM.rec.state!=="inactive"){try{DLM.rec.stop();}catch(e){}}
  DLM.busy=false;
  dlEl("dlModal").classList.remove("show");
}

async function dlRunM3U8(){
  var src=(playerSources[playerSrc]||[])[playerEp]||{};
  var base=src.url||playerCurUrl;
  DLM.ctrl=new AbortController();
  dlSetBusy(true);dlsReset();
  try{
    dlSetStage("lucide:list-tree","解析播放清单","");
    dlSetBar(2);dlSetMeta("","","");
    var txt=await dlText(base,DLM.ctrl.signal);
    var man=m3u8Parse(txt,base);
    if(man.isMaster){
      man.variants.sort(function(a,b){return b.bandwidth-a.bandwidth;});
      var best=man.variants[0];
      dlSetStage("lucide:list-tree","选择清晰度",man.variants.length+" 个档位，取最高"+(best.height?" "+best.height+"p":""));
      txt=await dlText(best.url,DLM.ctrl.signal);
      man=m3u8Parse(txt,best.url);
    }
    if(!man.segs.length)throw new Error("清单中没有媒体分片");
    if(man.live)throw new Error("这是直播流（清单无结束标记），没有终点。请改用「WebM 边看边录」");
    var n=man.segs.length;
    dlEl("dlStageIcon").setAttribute("icon","lucide:hard-drive-download");
    dlEl("dlStageTitle").textContent="下载分片 0/"+n;
    dlEl("dlStageNote").textContent="共 "+n+" 段"+(man.duration?" · 时长 "+dlDur(man.duration):"");
    var lastPaint=0;
    var segs=await dlSegments(man.segs,DLM.ctrl.signal,function(done,total,chunk){
      dlsAdd(chunk,0);
      var now=performance.now();
      if(now-lastPaint<120&&done<total)return;
      lastPaint=now;
      dlSetBar(done/total*90);
      dlEl("dlStageTitle").textContent="下载分片 "+done+"/"+total;
      dlSetMeta(dlBytes(DLS.bytes),"已下",dlSpeed(DLS.speed)+"  ·  剩 #"+(total-done));
    });
    var size=0;segs.forEach(function(s){size+=s.length});
    dlSetStage("lucide:cog","转封装中","TS 分片 → MP4");
    dlSetBar(92);
    var out=null,ext="mp4";
    if(man.map&&/\.(m4s|mp4)(\?|$)/i.test(man.segs[0])){
      var init=await dlFetchBytes(man.map,DLM.ctrl.signal);
      dlEl("dlStageNote").textContent="fMP4 直拼，无需转码";
      out=dlConcat([init].concat(segs));
    }else{
      out=await dlRemux(segs,function(i,t){
        dlSetBar(90+i/t*9);
        dlEl("dlStageTitle").textContent="转封装 "+i+"/"+t;
      });
      if(!out){ext="ts";out=dlConcat(segs);dlEl("dlStageNote").textContent="转封装组件未就绪，已输出 TS";}
    }
    dlSetBar(100);
    dlSetStage("lucide:check-circle-2","完成",dlBytes(out.length)+" · "+ext.toUpperCase());
    dlSetMeta(dlBytes(out.length),"最终大小","耗时 "+dlDur((performance.now()-DLS.t0)/1000));
    dlSave(out,ext,ext==="mp4"?"video/mp4":"video/mp2t");
    toast("已保存 "+dlName(ext));
  }catch(e){
    if(e.name==="AbortError"){dlSetStage("lucide:x-circle","已取消","");}
    else{
      dlSetStage("lucide:triangle-alert","下载失败",dlErrText(e));
      console.error("dl m3u8",e);
    }
    dlSetBar(0);
  }finally{
    DLM.ctrl=null;
    dlEl("dlCancel").textContent="关闭";
  }
}

function dlErrText(e){
  var m=(e&&e.message)||"未知错误";
  if(/Failed to fetch|NetworkError|Load failed/i.test(m))return "跨域被拒绝：该源不允许浏览器直取分片，改用「WebM 边看边录」";
  if(/HTTP 40[34]/.test(m))return "服务器拒绝访问（"+m+"），可能是防盗链";
  return m;
}

async function dlRunDirect(){
  var src=(playerSources[playerSrc]||[])[playerEp]||{};
  var url=src.url||playerCurUrl;
  DLM.ctrl=new AbortController();
  dlSetBusy(true);dlsReset();
  try{
    dlSetStage("lucide:download","下载中","0%");
    dlSetBar(0);
    var lastPaint=0;
    var u8=await dlFetchBytes(url,DLM.ctrl.signal,function(n,total){
      dlsAdd(n,total);
      var now=performance.now();
      if(now-lastPaint<120)return;
      lastPaint=now;
      var pct=DLS.total?DLS.bytes/DLS.total*100:0;
      dlSetBar(pct);
      dlEl("dlStageTitle").textContent="下载中 "+(DLS.total?pct.toFixed(0)+"%":"");
      dlSetMeta(dlBytes(DLS.bytes)+(DLS.total?" / "+dlBytes(DLS.total):""),"已下载",
        dlSpeed(DLS.speed)+(DLS.total&&DLS.speed>0?"  ·  剩 "+dlDur((DLS.total-DLS.bytes)/DLS.speed):""));
    });
    dlSetBar(100);
    dlSetStage("lucide:check-circle-2","完成",dlBytes(u8.length));
    var ext=(/\.mp4(\?|$)/i.test(url)?"mp4":"bin");
    dlSave(u8,ext,ext==="mp4"?"video/mp4":"application/octet-stream");
    toast("已保存 "+dlName(ext));
  }catch(e){
    if(e.name==="AbortError")dlSetStage("lucide:x-circle","已取消","");
    else{dlSetStage("lucide:triangle-alert","下载失败",dlErrText(e));console.error("dl direct",e);}
    dlSetBar(0);
  }finally{DLM.ctrl=null;dlEl("dlCancel").textContent="关闭";}
}

/* ---------- WebM 边看边录 ---------- */
function dlStartRec(){
  if(!videoEl.captureStream){toast("当前浏览器不支持录制");return;}
  var stream;
  try{stream=videoEl.captureStream();}catch(e){toast("无法捕获画面："+(e.message||""));return;}
  var cands=["video/webm;codecs=vp9,opus","video/webm;codecs=vp8,opus","video/webm"];
  var mime="";
  for(var i=0;i<cands.length;i++){if(window.MediaRecorder.isTypeSupported(cands[i])){mime=cands[i];break;}}
  if(!mime){toast("当前浏览器不支持 WebM 录制");return;}
  DLM.mime=mime;DLM.recChunks=[];DLM.recT0=Date.now();
  try{
    DLM.rec=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:2500000,audioBitsPerSecond:128000});
  }catch(e){toast("录制启动失败："+(e.message||""));return;}
  DLM.rec.ondataavailable=function(e){if(e.data&&e.data.size)DLM.recChunks.push(e.data);};
  DLM.rec.onstop=function(){
    clearInterval(DLM.recTimer);DLM.recTimer=0;
    var blob=new Blob(DLM.recChunks,{type:"video/webm"});
    DLM.recChunks=[];
    dlEl("dlModal").classList.remove("show");
    dlRecBar(false);
    dlSaveBlob(blob,"webm");
    toast("录制结束，已保存 "+dlBytes(blob.size));
  };
  DLM.rec.start(1000);
  if(videoEl.paused)videoEl.play().catch(function(){});
  dlRecBar(true);
  DLM.recTimer=setInterval(function(){
    var sec=(Date.now()-DLM.recT0)/1000;
    var b=0;DLM.recChunks.forEach(function(c){b+=c.size});
    dlEl("recTime").textContent=dlDur(sec);
    dlEl("recSize").textContent=dlBytes(b);
  },500);
  dlEl("dlModal").classList.remove("show");
  toast("开始录制，播放到哪录到哪");
}
function dlStopRec(){
  if(DLM.rec&&DLM.rec.state!=="inactive"){try{DLM.rec.stop();}catch(e){}}
}
function dlRecBar(on){
  var bar=dlEl("recBar");
  if(bar)bar.classList.toggle("show",!!on);
}

/* ---------- 选集三按钮 ---------- */
function epActsHTML(){
  var fav=playerItem?isFav(playerItem):false;
  return '<div class="ep-acts">'
    +'<button class="ep-act" data-act="play"><iconify-icon icon="lucide:play"></iconify-icon><span>播放</span></button>'
    +'<button class="ep-act'+(fav?" on":"")+'" data-act="fav"><iconify-icon icon="'+(fav?"lucide:heart":"lucide:heart")+'"></iconify-icon><span>'+(fav?"已收藏":"收藏")+'</span></button>'
    +'<button class="ep-act" data-act="dl"><iconify-icon icon="lucide:download"></iconify-icon><span>下载</span></button>'
    +'</div>';
}
function epActsRefresh(){
  document.querySelectorAll("#epActs,#fsEpActs").forEach(function(c){if(c)c.innerHTML=epActsHTML();});
}
document.addEventListener("click",function(e){
  var b=e.target.closest&&e.target.closest(".ep-act");
  if(!b)return;
  var act=b.getAttribute("data-act");
  if(act==="play"){
    var m=dlEl("fsEpModal");if(m)m.classList.remove("show");
    playEp(playerEp);
  }else if(act==="fav"){
    if(!playerItem)return;
    toggleFav(playerItem,{stopPropagation:function(){},preventDefault:function(){}});
    epActsRefresh();
  }else if(act==="dl"){
    dlOpen();
  }
});

/* ---------- 绑定 ---------- */
function dlInit(){
  dlEl("dlClose").addEventListener("click",dlClose);
  dlEl("dlCancel").addEventListener("click",dlCancel);
  dlEl("optM3u8").addEventListener("click",dlRunM3U8);
  dlEl("optMp4").addEventListener("click",dlRunDirect);
  dlEl("optWebm").addEventListener("click",dlStartRec);
  dlEl("recStop").addEventListener("click",dlStopRec);
  dlEl("dlModal").addEventListener("click",function(e){if(e.target===dlEl("dlModal"))dlClose();});
}

"use strict";
const $ = id => document.getElementById(id);
let tool = "audio", filter = "all", media = [], sequence = [], selected = -1, ready = false, search = "", brandColors = [];
let audioView="audition", audioBucketFilter="effect", auditionSearch="";
const BUCKETS={bed:"Sound beds",effect:"Sound Effects",wildcard:"Wildcards"};
const audioBucket=m=>m.audio_bucket||({Bed:"bed",Gesture:"effect",Music:"wildcard"}[m.ingredient_role])||"wildcard";
const DRAFT_KEY = "mit2009Studio2026Draft";
const copy = {
  video: ["PHOTO & VIDEO GENERATOR", "Make the work move.", "Arrange photographs and edited clips into a silent video. Add sound when you’re ready.", "Create silent video"],
  audio: ["AUDIO GENERATOR", "Find your sound.", "Sound beds, Sound Effects, and Wildcards. Listen first. Keep what feels like 2.009.", "Generate soundtrack"],
  text: ["TEXT ANIMATOR", "Make your words move.", "Animate a title, add words over an image, or create a transparent layer for your final edit.", "Export animation"],
  assemble: ["AV ASSEMBLER", "Bring it all together.", "Combine your chosen video, soundtrack, and optional animated text into a downloadable MP4.", "Export final post"]
};
const item = id => media.find(m => m.id === id);
const val = id => $(id).value;
const num = id => Number(val(id));
const checked = id => $(id).checked;
function element(tag, className, text) {const e=document.createElement(tag);if(className)e.className=className;if(text!==undefined)e.textContent=text;return e;}
async function api(path, body) {
  const r=await fetch(path, body===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json","X-Studio-Request":"1"},body:JSON.stringify(body)});
  const result=await r.json();if(!r.ok)throw Error(result.error||"Something went wrong.");return result;
}
function saveDraft(){
  if(!ready)return;
  try{const inputs={};document.querySelectorAll(".settings input[id],.settings select[id],.settings textarea[id]").forEach(e=>{if(e.type!=="file")inputs[e.id]=e.type==="checkbox"?e.checked:e.value;});localStorage.setItem(DRAFT_KEY,JSON.stringify({tool,sequence,selected,inputs,audioView,audioBucketFilter}));}catch{}
}
function restoreDraft(){
  try{const draft=JSON.parse(localStorage.getItem(DRAFT_KEY)||localStorage.getItem("mit2009StudioDraft")||"null");if(!draft)return;
    sequence=(draft.sequence||[]).filter(e=>item(e.id));selected=Math.min(draft.selected??0,sequence.length-1);
    Object.entries(draft.inputs||{}).forEach(([id,value])=>{const e=$(id);if(!e||e.type==="file")return;if(e.type==="checkbox")e.checked=Boolean(value);else e.value=value;});
    if(copy[draft.tool])tool=draft.tool;
    if(["audition","mix"].includes(draft.audioView))audioView=draft.audioView;
    if(BUCKETS[draft.audioBucketFilter])audioBucketFilter=draft.audioBucketFilter;
    auditionSearch=val("audition-search").trim().toLowerCase();
  }catch{}
}
function selectTool(next) {
  tool=next;document.body.dataset.tool=tool;$("file-input").accept=tool==="audio"?"audio/*":"image/*,video/*,audio/*";document.querySelectorAll("button[data-tool]").forEach(b=>{b.classList.toggle("active",b.dataset.tool===tool);b.setAttribute("aria-pressed",String(b.dataset.tool===tool));});
  document.querySelectorAll(".tool-panel").forEach(p=>p.hidden=p.id!==`panel-${tool}`);
  const [eyebrow,title,description,button]=copy[tool];$("eyebrow").textContent=eyebrow;$("page-title").textContent=title;$("page-description").textContent=description;
  $("render-button").replaceChildren(document.createTextNode(button),element("span","","↗"));$("form-status").textContent="";
  renderLibrary();setAudioView(audioView);updatePreview();saveDraft();
}
function updateSelects() {
  document.querySelectorAll("select[data-library]").forEach(select=>{
    const previous=select.value, kind=select.dataset.library, first=select.options[0].textContent;
    select.replaceChildren(new Option(first,""));
    media.filter(m=>{const bucket={"audio-main":"bed","audio-accent":"effect","audio-music":"wildcard"}[select.id];return !bucket||(m.role==="source"&&audioBucket(m)===bucket&&m.assessment!=="pass");}).filter(m=>kind==="audio"?m.kind==="audio":kind==="overlay"?m.role==="text-overlay":kind==="visual"?["image","video"].includes(m.kind)&&m.role!=="text-overlay":m.kind==="video"&&m.role!=="text-overlay").forEach(m=>select.add(new Option(m.name,m.id)));
    if([...select.options].some(o=>o.value===previous))select.value=previous;
  });
}
async function refreshLibrary(){media=(await api("/api/library")).items;$("media-count").textContent=`${media.length} files`;updateSelects();renderLibrary();renderAudition();}
function renderLibrary(){
  const list=$("media-list");list.replaceChildren();
  const rows=media.filter(m=>(filter==="all"||m.kind===filter)&&m.name.toLowerCase().includes(search));
  if(!rows.length){list.append(element("p","muted small",search?"No matching files. Try another name.":"No media here yet."));return;}
  rows.slice().reverse().forEach(m=>{
    const card=element("div","media-card");
    if(m.thumbnail_url){const img=element("img");img.src=m.thumbnail_url;img.alt="";img.loading="lazy";card.append(img);}else card.append(element("div","media-icon",m.kind==="audio"?"♫":"▻"));
    const text=element("div");text.append(element("strong","",m.name),element("small","",m.kind==="image"?`${m.width} × ${m.height}`:`${m.duration.toFixed(1)} sec · ${m.role==="source"?m.kind:"export"}`));card.append(text);
    const add=element("button","","+");add.title=tool==="video"?"Add to sequence":"Use this file";add.setAttribute("aria-label",`${add.title}: ${m.name}`);
    add.onclick=()=>useMedia(m);card.append(add);list.append(card);
  });
}
function useMedia(m){
  if(tool==="video"&&["image","video"].includes(m.kind)&&m.role!=="text-overlay"){
    sequence.push({id:m.id,duration:m.kind==="video"?Math.min(m.duration,num("default-duration")):num("default-duration"),start:0,focus_x:.5,focus_y:.5});selected=sequence.length-1;renderSequence();
  }else if(tool==="text"&&["image","video"].includes(m.kind)){$("text-base").value=m.id;$("text-transparent").checked=false;}
  else if(tool==="audio"&&m.kind==="audio"){audioBucketFilter=audioBucket(m);$("audition-shortlist").checked=false;auditionSearch=m.name.toLowerCase();$("audition-search").value=m.name;setAudioView("audition");}
  else if(tool==="assemble"){
    if(m.role==="text-overlay")$("assemble-overlay").value=m.id;
    else $(m.kind==="audio"?"assemble-audio":"assemble-video").value=m.id;
  }else{$("form-status").textContent="Choose a media file that matches the current tool.";return;}
  updatePreview();
}
function inputLabel(name,value,type="number",onchange){
  const label=element("label","",name),input=element("input");input.type=type;input.value=value;
  if(type==="number"){input.min="0";input.step="0.1";}else{input.min="0";input.max="1";input.step="0.01";}
  input.addEventListener("input",()=>onchange(Number(input.value)));label.append(input);return label;
}
function renderSequence(){
  saveDraft();
  const list=$("sequence");list.replaceChildren();$("sequence-count").textContent=sequence.length?`${sequence.length} · ${sequence.reduce((s,e)=>s+e.duration,0).toFixed(1)}s`:"0";
  if(!sequence.length){list.append(element("div","empty-sequence","Add photographs or edited clips from your library."));updatePreview();return;}
  sequence.forEach((entry,index)=>{
    const m=item(entry.id);if(!m)return;
    const card=element("div","seq-card"+(index===selected?" selected":""));card.draggable=true;card.dataset.index=index;
    card.ondragstart=e=>e.dataTransfer.setData("text/plain",String(index));card.ondragover=e=>e.preventDefault();card.ondrop=e=>{e.preventDefault();const from=Number(e.dataTransfer.getData("text/plain"));if(Number.isInteger(from)&&from>=0&&from<sequence.length){const [moved]=sequence.splice(from,1);sequence.splice(index,0,moved);selected=index;renderSequence();}};
    const row=element("div","seq-top");row.append(element("span","seq-index",String(index+1).padStart(2,"0")));
    const img=element("img");img.src=m.thumbnail_url;img.alt="";img.onclick=()=>{selected=index;renderSequence();};row.append(img);
    const name=element("div","seq-name",m.name);name.onclick=()=>{selected=index;renderSequence();};row.append(name);
    const actions=element("div","seq-actions");
    [["↑","Move earlier",-1],["↓","Move later",1],["×","Remove",0]].forEach(([symbol,label,delta])=>{const b=element("button","",symbol);b.type="button";b.setAttribute("aria-label",`${label}: ${m.name}`);b.onclick=()=>{if(!delta){sequence.splice(index,1);selected=Math.min(selected,sequence.length-1);}else if(index+delta>=0&&index+delta<sequence.length){[sequence[index],sequence[index+delta]]=[sequence[index+delta],sequence[index]];selected=index+delta;}renderSequence();};actions.append(b);});row.append(actions);card.append(row);
    const settings=element("div","seq-options");settings.append(inputLabel("Duration · sec",entry.duration,"number",v=>{entry.duration=v;$("sequence-count").textContent=`${sequence.length} · ${sequence.reduce((s,e)=>s+e.duration,0).toFixed(1)}s`;}));
    if(m.kind==="video")settings.append(inputLabel("Start in clip · sec",entry.start,"number",v=>entry.start=v));
    if(m.kind==="image"){
      const details=element("details");details.append(element("summary","","Adjust crop focus"));
      details.append(inputLabel("Left ↔ right",entry.focus_x,"range",v=>{entry.focus_x=v;selected=index;updatePreview();}),inputLabel("Top ↔ bottom",entry.focus_y,"range",v=>{entry.focus_y=v;selected=index;updatePreview();}));settings.append(details);
    }
    card.append(settings);list.append(card);
  });updatePreview();
}
function updatePreview(){
  $("video-motion").disabled=val("video-fit")==="contain";
  updateSwatches();
  updateMixPlayers();
  const stage=$("preview-stage");stage.replaceChildren();let m,format="vertical";
  $("preview-heading").textContent=tool==="audio"?"Sound ingredient":tool==="text"?"Style preview":tool==="assemble"?"Selected video":"Framing preview";
  $("preview-note").textContent=tool==="text"?"A guide to the style and placement. Your exported animation appears below for review.":tool==="audio"?"Listen to your sound bed here. Each layer also has its own player. Your finished mix appears below.":"Review your rendered video below before sharing.";
  if(tool==="video"){m=item(sequence[selected]?.id);format=val("video-format");}
  if(tool==="text"){m=checked("text-transparent")?null:item(val("text-base"));format=val("text-format");}
  if(tool==="audio")m=item(val("audio-main"));
  if(tool==="assemble"){m=item(val("assemble-video"));if(m)format=m.width===m.height?"square":m.width>m.height?"landscape":"vertical";}
  stage.className="preview-stage"+(format==="square"?" square":format==="landscape"?" wide":"");$("format-label").textContent={vertical:"9:16",square:"1:1",landscape:"16:9"}[format];
  stage.style.background=tool==="text"?val("text-background"):"#171717";
  if(m){
    const e=element(m.kind==="image"?"img":m.kind==="audio"?"audio":"video");e.src=m.url;
    if(m.kind!=="image"){e.controls=true;e.preload="metadata";}else e.alt="Selected photograph";
    if(tool==="video"){e.style.objectFit=val("video-fit")==="contain"?"contain":"cover";e.style.objectPosition=`${(sequence[selected]?.focus_x??.5)*100}% ${(sequence[selected]?.focus_y??.5)*100}%`;}
    stage.append(e);
  }else if(tool!=="text"){
    const empty=element("div","empty-preview");const mark=element("span","connect-logo"),logo=element("img");logo.src="/brand-2026/logo-02.png";logo.alt="2.009 Connect";mark.append(logo);empty.append(mark,element("p","",tool==="audio"?"Choose a sound ingredient.":tool==="assemble"?"Choose your video and soundtrack.":"Choose a photograph to start your edit."));stage.append(empty);
  }
  if(tool==="text"){
    const overlay=element("div",`preview-text ${val("text-position")} ${val("text-style")}`);overlay.style.color=val("text-color");
    const words=element("span",checked("text-plate")?"backing":"",val("text-content"));words.id="preview-words";overlay.append(words);stage.append(overlay);
  }
}
let animationStart=performance.now();
setInterval(()=>{if(tool!=="text")return;const span=$("preview-words");if(!span)return;const elapsed=((performance.now()-animationStart)/1000)%5,content=val("text-content");
  if(val("text-style")==="words")span.textContent=content.split(/\s+/).slice(0,Math.ceil(content.split(/\s+/).length*Math.min(1,elapsed/2))).join(" ");
  else if(val("text-style")==="type")span.textContent=content.slice(0,Math.ceil(content.length*Math.min(1,elapsed/2)));
},80);
function importFeedback(message){$("import-status").textContent=message;$("audition-status").textContent=message;}
async function importFiles(files){
  const importTool=tool, importBucket=audioBucketFilter;
  const supported=[...files].filter(f=>(importTool==="audio"?/\.(wav|mp3|m4a|aac|aiff?|flac|ogg)$/i:/\.(jpe?g|png|webp|tiff?|mp4|mov|m4v|webm|wav|mp3|m4a|aac|aiff?|flac|ogg)$/i).test(f.name));
  if(!supported.length){importFeedback("Choose photographs, video, or audio files. Unzip folders before importing.");return;}
  let failed=0;const imported=[];
  for(let i=0;i<supported.length;i++){
    const file=supported[i];importFeedback(`Importing ${i+1} of ${supported.length}: ${file.name}`);
    try{const r=await fetch(`/api/import?name=${encodeURIComponent(file.name)}&audio_bucket=${importTool==="audio"?importBucket:"wildcard"}`,{method:"POST",headers:{"X-Studio-Request":"1"},body:file});const data=await r.json();if(!r.ok)throw Error(data.error);imported.push(data);}catch(e){failed++;$("form-status").textContent=`${file.name}: ${e.message}`;}
  }
  await refreshLibrary();importFeedback(`${imported.length} imported${failed?`; ${failed} could not be imported`:""}.`);
  if(tool==="audio"){$("audition-shortlist").checked=false;renderAudition();}
  if(tool==="video"){
    imported.filter(m=>["image","video"].includes(m.kind)).sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true})).forEach(m=>useMedia(m));
  }
}
function configuration(){
  if(tool==="video")return{format:val("video-format"),fit:val("video-fit"),motion:val("video-motion"),dissolve:num("video-dissolve"),sequence};
  if(tool==="audio")return{main:val("audio-main"),music:val("audio-music"),accent:val("audio-accent"),main_gain:num("audio-main-gain"),music_gain:num("audio-music-gain"),accent_gain:num("audio-accent-gain"),duration:num("audio-duration"),seed:num("audio-seed"),target_lufs:num("audio-level")};
  if(tool==="text")return{text:val("text-content"),format:val("text-format"),style:val("text-style"),position:val("text-position"),color:val("text-color"),background:val("text-background"),base:val("text-base"),plate:checked("text-plate"),transparent:checked("text-transparent"),duration:num("text-duration"),start:num("text-start"),hold:num("text-hold")};
  return{video:val("assemble-video"),audio:val("assemble-audio"),overlay:val("assemble-overlay"),gain:num("assemble-gain"),fade:num("assemble-fade"),loop_audio:checked("assemble-loop")};
}
async function renderJob(){
  const button=$("render-button");button.disabled=true;$("form-status").textContent="";
  try{await api("/api/render",{tool,name:val("export-name"),config:configuration()});$("form-status").textContent="Your export is in the queue below. You can keep working.";await pollJobs();}
  catch(e){$("form-status").textContent=e.message;}finally{button.disabled=false;}
}
let knownDone=new Set(),polling=false;
async function pollJobs(){
  if(polling)return;polling=true;
  try{
    const {jobs}=await api("/api/jobs"),container=$("jobs");$("job-count").textContent=jobs.length?`${jobs.length} exports`:"";
    if(!jobs.length)return;
    if(!container.querySelector(".job"))container.replaceChildren();
    let refresh=false;
    jobs.forEach(job=>{
      if(job.status==="done"&&!knownDone.has(job.id)){knownDone.add(job.id);refresh=true;}
      const signature=`${job.status}:${job.message}`;let card=document.getElementById(`job-${job.id}`);
      if(card?.dataset.signature===signature)return;
      const next=element("article","job"+(job.status==="error"?" error":["queued","rendering"].includes(job.status)?" working":""));next.id=`job-${job.id}`;next.dataset.signature=signature;
      next.append(element("span","tag",job.tool),element("h3","",job.name),element("p","",job.message));
      if(job.status==="done"){
        const result=job.result,player=element(result.kind==="audio"?"audio":"video");player.controls=true;player.preload="metadata";player.src=result.preview_url;next.append(player);
        const details=element("p","",`${result.duration.toFixed(1)} seconds${result.kind==="video"?` · ${result.width} × ${result.height}`:""}`);next.append(details);
        const download=element("a","download",`Download ${result.name.split(".").pop().toUpperCase()} ↓`);download.href=result.url+"?download=1";download.download=result.name;next.append(download);
        const review=element("select");review.setAttribute("aria-label",`Review status: ${job.name}`);[["draft","Draft — needs review"],["keep","Keep for comparison"],["approved","Approved by me"]].forEach(([v,n])=>review.add(new Option(n,v)));review.value=item(result.id)?.review||"draft";review.onchange=async()=>{try{await api("/api/review",{id:result.id,review:review.value});await refreshLibrary();}catch(e){$("form-status").textContent=e.message;}};next.append(review);
      }else if(job.status!=="error")next.append(element("div","progress"));
      if(card)card.replaceWith(next);else container.prepend(next);
    });
    if(refresh)await refreshLibrary();
  }catch(e){$("form-status").textContent="The local studio is not responding. Keep its launcher open and refresh this page.";}
  finally{polling=false;}
}
document.addEventListener("input",()=>setTimeout(saveDraft,0));
document.addEventListener("change",()=>setTimeout(saveDraft,0));
document.querySelectorAll("button[data-tool]").forEach(b=>b.onclick=()=>selectTool(b.dataset.tool));
document.querySelectorAll("[data-filter]").forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll("[data-filter]").forEach(x=>x.classList.toggle("active",x===b));renderLibrary();});
$("media-search").oninput=e=>{search=e.target.value.trim().toLowerCase();renderLibrary();};
$("drop-zone").onclick=()=>$("file-input").click();
$("import-folder").onclick=()=>$("folder-input").click();
$("file-input").onchange=e=>importFiles(e.target.files);$("folder-input").onchange=e=>importFiles(e.target.files);
const drop=$("drop-zone");drop.ondragover=e=>{e.preventDefault();drop.classList.add("dragging");};drop.ondragleave=()=>drop.classList.remove("dragging");drop.ondrop=e=>{e.preventDefault();drop.classList.remove("dragging");importFiles(e.dataTransfer.files);};
$("apply-duration").onclick=()=>{sequence.forEach(e=>{const m=item(e.id);e.duration=m.kind==="video"?Math.min(num("default-duration"),m.duration-e.start):num("default-duration");});renderSequence();};
document.querySelectorAll(".tool-panel input,.tool-panel select,.tool-panel textarea").forEach(input=>input.addEventListener("input",()=>{const label=document.querySelector(`[data-for="${input.id}"]`);if(label)label.textContent=`${input.value} dB`;animationStart=performance.now();updatePreview();}));
$("text-duration").addEventListener("change",()=>{$("text-hold").value=Math.max(.2,num("text-duration")-num("text-start"));});
$("text-base").addEventListener("change",()=>{const m=item(val("text-base"));if(m?.kind==="video"){$("text-duration").value=Math.min(180,m.duration).toFixed(1);$("text-hold").value=Math.max(.2,num("text-duration")-num("text-start"));}});
$("render-button").onclick=renderJob;
$("text-content").value=$("text-content").value.replace(/\\n/g,"\n");
(async()=>{try{await loadBrand();await refreshLibrary();restoreDraft();ready=true;selectTool(tool);renderSequence();await pollJobs();}catch(e){$("form-status").textContent=e.message;}})();
setInterval(pollJobs,1500);

// This edition stays 2026. A future course year belongs in its own copy.
async function loadBrand(){
  const brand=await api("/brand-2026/brand.json");
  brandColors=[...brand.colors,{name:"Ink",hex:"#231f20"},{name:"White",hex:"#ffffff"}];
  for(const [container,target] of [["text-swatches","text-color"],["background-swatches","text-background"]]){
    brandColors.forEach(color=>{
      const button=element("button","swatch");button.type="button";button.style.setProperty("--swatch",color.hex);button.dataset.color=color.hex;button.dataset.target=target;
      button.title=`${color.name} · ${color.hex.toUpperCase()}`;button.setAttribute("aria-label",`${target==="text-color"?"Text":"Background"}: ${color.name}`);
      button.onclick=()=>{$(target).value=color.hex;updatePreview();saveDraft();};$(container).append(button);
    });
  }
  brand.colors.forEach(color=>{
    const b=element("button","palette-card");b.type="button";b.style.setProperty("--swatch",color.hex);b.setAttribute("aria-label",`Copy ${color.name} ${color.hex}`);
    b.append(element("span","palette-chip"),element("strong","",color.name),element("small","",color.hex.toUpperCase()));
    b.onclick=async()=>{try{await navigator.clipboard.writeText(color.hex.toUpperCase());$("brand-status").textContent=`${color.name} copied: ${color.hex.toUpperCase()}`;}catch{$("brand-status").textContent=`${color.name}: ${color.hex.toUpperCase()}`;}};$("brand-palette").append(b);
  });
}
function updateSwatches(){
  document.querySelectorAll(".swatch").forEach(b=>{const chosen=val(b.dataset.target).toLowerCase()===b.dataset.color;b.classList.toggle("selected",chosen);b.setAttribute("aria-pressed",String(chosen));});
}
$("open-brand").onclick=()=>$("brand-dialog").showModal();
$("close-brand").onclick=()=>$("brand-dialog").close();
$("brand-dialog").addEventListener("click",e=>{if(e.target===$("brand-dialog")){const rect=e.target.getBoundingClientRect();if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)e.target.close();}});

function setAudioView(view){
  audioView=view;document.body.dataset.audioView=view;
  $("audio-audition").hidden=view!=="audition";$("audio-mix").hidden=view!=="mix";
  document.querySelectorAll("button[data-audio-view]").forEach(b=>{b.classList.toggle("active",b.dataset.audioView===view);b.setAttribute("aria-pressed",String(b.dataset.audioView===view));});
  if(tool==="audio"&&view==="audition")renderAudition();
  saveDraft();
}
function updateMixPlayers(){
  for(const part of ["main","accent","music"]){
    const player=$("listen-"+part),m=item(val("audio-"+part));player.hidden=!m;
    if(m&&player.getAttribute("src")!==m.url)player.src=m.url;
    if(!m)player.removeAttribute("src");
  }
}
async function assessAudio(m,changes,status){
  try{await api("/api/audio-item",{id:m.id,...changes});Object.assign(m,changes);status.textContent="Saved";updateSelects();saveDraft();}
  catch(e){status.textContent=e.message;}
}
function renderAudition(){
  const sources=media.filter(m=>m.kind==="audio"&&m.role==="source");
  document.querySelectorAll("[data-audio-bucket]").forEach(b=>{const bucket=b.dataset.audioBucket;b.classList.toggle("active",bucket===audioBucketFilter);b.setAttribute("aria-pressed",String(bucket===audioBucketFilter));$("bucket-count-"+bucket).textContent=sources.filter(m=>audioBucket(m)===bucket).length;});
  const matches=sources.filter(m=>audioBucket(m)===audioBucketFilter&&(!checked("audition-shortlist")||m.collection==="Adobe playful shortlist")&&m.name.toLowerCase().includes(auditionSearch));
  const list=$("audition-list");list.replaceChildren();
  $("audition-intro").textContent=checked("audition-shortlist")?"A playful first pass from your Adobe library. Selected by the sound descriptions; your ears make the final call.":`${BUCKETS[audioBucketFilter]}. Listen, make a note, and decide what belongs.`;
  if(!matches.length){list.append(element("p","empty-sequence",checked("audition-shortlist")?"No shortlist clips in this bucket. Turn off New Adobe shortlist to see your other sounds.":"No matching sounds. Import audio or try a different search."));return;}
  matches.sort((a,b)=>(a.shortlist_order??999)-(b.shortlist_order??999)||a.name.localeCompare(b.name,undefined,{numeric:true})).forEach(m=>{
    const card=element("article","audition-card"),head=element("div","audition-card-heading"),status=element("span","assessment-status");
    head.append(element("span","tag",m.collection==="Adobe playful shortlist"?"ADOBE · SHORTLIST":"YOUR LIBRARY"),element("span","duration",`${m.duration.toFixed(2)} sec`));card.append(head,element("h3","",m.name.replace(/\.wav$/i,"")));
    if(m.suggestion)card.append(element("p","sound-suggestion",m.suggestion));
    const player=element("audio");player.controls=true;player.preload="none";player.src=m.url;player.setAttribute("aria-label",`Listen to ${m.name}`);card.append(player);
    const controls=element("div","audition-card-controls"),label=element("label","","Your take"),review=element("select");review.setAttribute("aria-label",`Your take: ${m.name}`);
    [["unreviewed","Not assessed"],["keep","Keep"],["maybe","Maybe"],["pass","Pass"]].forEach(([v,n])=>review.add(new Option(n,v)));review.value=m.assessment||"unreviewed";
    review.onchange=()=>assessAudio(m,{assessment:review.value},status);label.append(review);controls.append(label);
    const bucketLabel=element("label","","Bucket"),bucketSelect=element("select");bucketSelect.setAttribute("aria-label",`Bucket: ${m.name}`);Object.entries(BUCKETS).forEach(([v,n])=>bucketSelect.add(new Option(n,v)));bucketSelect.value=audioBucket(m);bucketSelect.onchange=async()=>{await assessAudio(m,{audio_bucket:bucketSelect.value},status);renderAudition();};bucketLabel.append(bucketSelect);controls.append(bucketLabel);card.append(controls);
    const noteLabel=element("label","audition-note","Your note"),notes=element("input");notes.type="text";notes.maxLength=500;notes.value=m.notes||"";notes.placeholder="e.g. Good for a reveal";notes.setAttribute("aria-label",`Note: ${m.name}`);notes.onchange=()=>assessAudio(m,{notes:notes.value},status);noteLabel.append(notes);card.append(noteLabel);
    const bottom=element("div","audition-card-bottom"),use=element("button","use-sound","Use in a mix ↗");use.onclick=()=>{if(m.assessment==="pass"){status.textContent="Change Pass to Keep or Maybe to use this sound.";return;}updateSelects();$({bed:"audio-main",effect:"audio-accent",wildcard:"audio-music"}[audioBucket(m)]).value=m.id;document.querySelectorAll("audio").forEach(p=>p.pause());setAudioView("mix");updatePreview();saveDraft();};bottom.append(status,use);card.append(bottom);list.append(card);
  });
}
document.querySelectorAll("button[data-audio-view]").forEach(b=>b.onclick=()=>setAudioView(b.dataset.audioView));
document.querySelectorAll("button[data-audio-bucket]").forEach(b=>b.onclick=()=>{audioBucketFilter=b.dataset.audioBucket;$("audition-shortlist").checked=false;renderAudition();saveDraft();});
$("audition-shortlist").onchange=()=>{if(checked("audition-shortlist"))audioBucketFilter="effect";renderAudition();saveDraft();};
$("audition-search").oninput=e=>{auditionSearch=e.target.value.trim().toLowerCase();renderAudition();};
document.addEventListener("play",e=>{if(e.target.tagName==="AUDIO")document.querySelectorAll("audio").forEach(player=>{if(player!==e.target)player.pause();});},true);

$("add-bucket-audio").onclick=()=>$("file-input").click();
$("add-bucket-folder").onclick=()=>$("folder-input").click();

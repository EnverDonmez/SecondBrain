const $ = selector => document.querySelector(selector);
const node = (tag, attrs={}, children=[]) => {
  const element=document.createElement(tag);
  for (const [key,value] of Object.entries(attrs)) {
    if (key==='text') element.textContent=value;
    else if (key.startsWith('on')) element.addEventListener(key.slice(2),value);
    else if (value!==null && value!==undefined) element.setAttribute(key,value);
  }
  for (const child of Array.isArray(children)?children:[children]) if(child!==null && child!==undefined) element.append(child instanceof Node?child:document.createTextNode(String(child)));
  return element;
};
const date = value => value?new Date(value).toLocaleString('tr-TR',{dateStyle:'medium',timeStyle:'short'}):'Henüz yok';
const names={overview:'Özet',activity:'Yapılanlar',memories:'Hafıza'};
const states={active:'Kullanımda',candidate:'Henüz kabul edilmedi',disputed:'Çelişki var',rejected:'Kabul edilmedi'};
const types={USER_ASSERTED_FACT:'Senin beyanın',USER_PREFERENCE:'Tercihin',MODEL_INFERENCE:'AI çıkarımı',PROJECT_STATE:'Proje bilgisi',DECISION:'Karar',POLICY:'Kural',PROCEDURE:'Çalışma yöntemi',SKILL:'Beceri',LESSON:'Deneyimden çıkarım',EXTERNAL_KNOWLEDGE:'Belgeden bilgi',CORRECTION:'Düzeltme',OBSERVED_EVENT:'Gözlem'};
const button=(text,handler,cls='')=>node('button',{type:'button',class:cls,text,onclick:async event=>{const b=event.currentTarget;b.disabled=true;try{await handler();}catch(error){showError(error);}finally{b.disabled=false;}}});
const panel=(title,body,extra)=>node('section',{class:'panel'},[node('div',{class:'panel-header'},[node('h2',{text:title}),extra]),body]);
const heading=(title,subtitle)=>node('div',{class:'observer-heading'},[node('h1',{text:title}),node('p',{text:subtitle})]);
let renderId=0, activityOffset=0, memoryOffset=0, searchQuery='', refreshing=false;
function login(message='') { renderId++;$('#dialog').close();$('#shell').hidden=true;$('#login').hidden=false;$('#login-error').textContent=message; }
async function api(path,body) {
  let response;
  try { response=await fetch('/api/'+path,{method:body===undefined?'GET':'POST',headers:{'X-Brain-Request':'1',...(body===undefined?{}:{'Content-Type':'application/json'})},...(body===undefined?{}:{body:JSON.stringify(body)})}); }
  catch { throw new Error('Beynine ulaşılamıyor. Yerel sunucuyu Start.cmd ile açıp yeniden dene.'); }
  let result; try{result=await response.json();}catch{throw new Error('Sunucudan geçerli yanıt alınamadı.');}
  if(!response.ok){if(response.status===403 && result.error==='Authentication required')login($('#shell').hidden?'':'Oturumun sona erdi. Tekrar giriş yapabilirsin.');const error=new Error(result.error||'İstek tamamlanamadı.');error.status=response.status;throw error;}
  return result;
}
function showError(error){$('#footer-health').textContent='Bağlantı denetlenmeli'; if(!$('#shell').hidden)$('#main').replaceChildren(heading('Şu an gösterilemiyor',error.message),button('Yeniden dene',()=>render()));else $('#login-error').textContent=error.message;}
const empty=text=>node('div',{class:'observer-empty',text});
function showDialog(title,content){$('#dialog-content').replaceChildren(node('h2',{text:title}),content);if(!$('#dialog').open)$('#dialog').showModal();}
async function memoryDetail(id){
  const data=await api('observer/memories/'+encodeURIComponent(id)), row=data.memory;
  const body=node('div',{},[node('p',{class:'observer-detail-meta',text:[types[row.memory_type]||row.memory_type,row.known_to?'Tarihsel kayıt':(states[row.status]||row.status),row.scope].join(' · ')}),node('div',{class:'source-excerpt',text:row.value}),node('p',{class:'note',text:'Değiştirmek istediğinde konuştuğun AI’ya bu bilgiyi tarif et. Kaydı senin talimatına göre, geçmişini koruyarak güncelleyebilir.'})]);
  if(row.topics.length)body.append(node('p',{class:'observer-note',text:'Konular: '+row.topics.join(', ')}));
  body.append(node('h3',{text:'Hangi kaynağa dayanıyor?'}));
  for(const source of data.sources)body.append(node('div',{class:'observer-history'},[node('small',{text:date(source.occurred_at)+' · '+(source.actor==='user'?'Kullanıcı mesajı':source.actor==='assistant'?'AI açıklaması':'Kaynak metni')}),node('p',{text:source.text}),source.more?node('small',{text:'Uzun kaynağın ilk 6.000 karakteri gösteriliyor. Devamını AI’dan isteyebilirsin.'}):null]));
  if(data.history.length>1){body.append(node('h3',{text:'Değişiklik geçmişi'}));for(const version of data.history)body.append(node('div',{class:'observer-history'},[node('small',{text:date(version.known_from)+' · '+(version.known_to?'Önceki sürüm':version.valid_to?'Önceki geçerlilik dönemi':'Geçerli sürüm')}),node('p',{text:version.value})]));}
  if(data.history_more||data.sources_more)body.append(node('p',{class:'observer-note',text:'Son 20 sürüm ve ilk 10 kaynak gösteriliyor. Daha eski ayrıntıları konuştuğun AI’dan isteyebilirsin.'}));
  if(data.changes.length){body.append(node('h3',{text:'AI’nın yaptığı düzenlemeler'}));for(const change of data.changes)body.append(node('div',{class:'observer-history'},[node('small',{text:date(change.created_at)+' · '+change.actor}),node('p',{text:change.details.operation==='organize'?'Konular ve bağlantılar düzenlendi.':change.details.operation==='hide'?'Kullanımdan kaldırıldı; geçmişi korundu.':change.details.operation==='approve'?'Konuşmadaki açık talimatınla kabul edildi.':'Konuşmadaki talimatınla reddedildi.'})]));}
  body.append(node('details',{class:'observer-details'},[node('summary',{text:'Kayıt referansı'}),node('p',{class:'observer-note',text:row.id+' · '+row.predicate})]));
  showDialog((row.subject==='user'?'Seninle ilgili':row.subject)+' · '+(types[row.memory_type]||'Bilgi'),body);
}
function memoryCard(row){return node('article',{class:'activity-entry'},[node('span',{class:'activity-mark',text:'◫'}),node('div',{class:'activity-copy'},[node('h3',{text:row.subject==='user'?'Seninle ilgili':row.subject}),node('p',{text:row.value||row.preview}),node('div',{class:'activity-meta'},[node('span',{class:'observer-tag',text:states[row.status]||row.status}),types[row.memory_type]||row.memory_type,row.scope,button('Kaynak ve geçmiş',()=>memoryDetail(row.id),'link-button')])])]);}
function activityLabel(row){
  if(row.action==='memory.conversation_change')return {organize:'Konular ve bağlantılar düzenlendi',approve:'Konuşmadaki talimatınla kabul edildi',reject:'Konuşmadaki talimatınla reddedildi',hide:'Kullanımdan kaldırıldı; geçmişi korundu'}[row.operation]||'Kayıt düzenlendi';
  return {'event.ingested':'Bir kaynak kaydedildi','memory.proposed':'Bir bilgi adayı çıkarıldı','memory.user_statement_accepted':row.correction?'Verdiğin bilgi güncellendi':'Söylediğin bilgi kaydedildi','memory.statement_reused':'Tekrarlanan bilgi mevcut kayda bağlandı','memory.approved':'Bir bilgi kabul edildi','memory.conflict':'Çelişen bilgi saptandı','memory.hidden':'Bir kayıt kullanımdan kaldırıldı','memory.rejected':'Bir aday reddedildi','memory.forgotten':'Kalıcı silme tamamlandı','backup.created':'Şifreli yedek oluşturuldu','backup.restored':'Yedek geri yüklendi','projection.rebuilt':'Arama bağlantıları yenilendi','token.created':'AI bağlantısı tanımlandı','token.revoked':'AI bağlantısı kaldırıldı'}[row.action]||'Sistem işlemi kaydedildi';
}
function activityCard(row){return node('article',{class:'activity-entry'},[node('span',{class:'activity-mark',text:row.action==='event.ingested'?'◷':'✧'}),node('div',{class:'activity-copy'},[node('h3',{text:activityLabel(row)}),row.subject?node('p',{text:row.subject==='user'?'Seninle ilgili':row.subject}):null,row.preview?node('p',{text:row.preview}):null,node('div',{class:'activity-meta'},[date(row.created_at),row.actor==='local-owner'?'Yerel uygulama':row.actor,row.subject?button('Kaynak ve geçmiş',()=>memoryDetail(row.target),'link-button'):null])])]);}
function intro(){return node('div',{class:'observer-intro'},[node('strong',{text:'Sen anlat. AI düzenlesin. Buradan olanları izle.'}),node('p',{text:'Bilgileri elle girmen veya sınıflandırman gerekmiyor. Bir değişiklik istediğinde konuştuğun yapay zekâya söyle; kaynak ve değişiklik geçmişi korunur.'})]);}
async function overview(main){
  const data=await api('observer');main.append(heading('Beyninde neler oluyor?','Konuşmalarından kalan bilgiler ve yapay zekânın yaptığı son işlemler.'),intro());
  main.append(node('div',{class:'stats-grid observer-stats'},[['Kullanımdaki bilgi',data.counts.current,'Kaynaklarıyla birlikte hatırlanabilir.'],['Korunan kaynak',data.counts.sources,'Yalnız kaydedilen konuşmalar ve belgeler.'],['Netleştirilmesi gereken',data.counts.pending,'AI bunları konuşmada seninle netleştirebilir.']].map(([title,value,note])=>node('div',{class:'stat-card'},[node('div',{class:'stat-top',text:title}),node('div',{class:'stat-value',text:value}),node('small',{text:note})]))));
  const feed=data.activity.items.length?node('div',{},data.activity.items.map(activityCard)):empty('Henüz bir işlem kaydedilmedi. Bağlı AI konuşmalarından bilgi kaydettikçe burada görünecek.');
  const attention=data.attention.length?node('div',{},data.attention.map(memoryCard)):empty('Şu anda netleştirilmesi gereken bir kayıt görünmüyor.');
  const connections=node('div',{},data.connections.length?data.connections.map(connection=>node('div',{class:'observer-status'},[node('strong',{text:connection.name}),node('p',{text:connection.enabled?(connection.last_seen?'Son erişim: '+date(connection.last_seen):'Yetki tanımlı; henüz erişim kaydı yok.'):'Bağlantı yetkisi kaldırılmış.'})])):[empty('Henüz bir AI bağlantısı tanımlanmamış. Kurulumu birlikte konuşarak yapabiliriz.')]);
  const ongoing=data.queue.filter(row=>['pending','running'].includes(row.state)).reduce((sum,row)=>sum+row.count,0);
  const system=node('div',{},[node('div',{class:'observer-status'},[node('strong',{text:ongoing?ongoing+' iş işleniyor veya sırada':'Bekleyen arka plan işi yok'}),node('p',{text:'Bilgiler bu bilgisayarda saklanıyor. Bu ekran 20 saniyede bir yenilenir.'})]),...data.issues.map(issue=>node('div',{class:'observer-status'},[node('strong',{text:'Bir işlem tamamlanamadı'}),node('p',{text:issue.error||'Ayrıntıyı konuştuğun AI ile inceleyebilirsin.'})]))]);
  main.append(node('div',{class:'observer-grid'},[node('div',{},[panel('Son yapılanlar',feed,node('a',{href:'#activity',class:'link-button',text:'Tüm işlemler →'})),panel('Konuşmada netleştirilecekler',attention)]),node('div',{},[panel('AI bağlantılarının son erişimi',connections),panel('Sistem durumu',system)])]));
}
async function activities(main){const data=await api('observer/activity?offset='+activityOffset);main.append(heading('Yapılanlar','Hangi kaynak eklendi, hangi bilgi güncellendi, kim düzenledi?'),panel('İşlem geçmişi',data.items.length?node('div',{},data.items.map(activityCard)):empty('Bu aralıkta işlem yok.')),pagination(activityOffset,data.more,()=>{activityOffset=Math.max(0,activityOffset-30);return render();},()=>{activityOffset+=30;return render();}));}
function pagination(offset,more,previous,next){const back=button('← Öncekiler',previous),forward=button('Sonrakiler →',next);back.disabled=offset===0;forward.disabled=!more;return node('div',{class:'observer-pagination'},[back,forward]);}
async function memories(main){
  main.append(heading('Hafızada neler var?','Bilgileri, dayandıkları kaynakları ve önceki hallerini incele.'));
  const query=node('input',{id:'memory-query',type:'search',maxlength:'2000',value:searchQuery,placeholder:'Bir bilgi, kişi veya proje ara…'});
  const form=node('form',{class:'observer-search',onsubmit:async event=>{event.preventDefault();searchQuery=query.value;memoryOffset=0;await render();}},[node('label',{for:'memory-query',text:'Hafızada ara'}),query,node('button',{type:'submit',class:'primary',text:'Ara'})]);main.append(form);
  const data=await api('observer/memories?query='+encodeURIComponent(searchQuery)+'&offset='+memoryOffset);
  main.append(panel('Bilgiler',data.items.length?node('div',{},data.items.map(memoryCard)):empty('Bu aramada kayıt bulunamadı. Bilgi henüz kaydedilmemiş olabilir.')),pagination(memoryOffset,data.more,()=>{memoryOffset=Math.max(0,memoryOffset-20);return render();},()=>{memoryOffset+=20;return render();}));
}
async function render({quiet=false}={}){
  const version=++renderId,raw=location.hash.slice(1),route=names[raw]?raw:'overview';
  $('#nav').replaceChildren(...Object.entries(names).map(([key,label],index)=>node('a',{href:'#'+key,class:key===route?'active':'','aria-current':key===route?'page':null},[node('span',{class:'nav-icon',text:['◎','◷','◫'][index]}),label])));
  $('#crumb').textContent=names[route];
  if(!quiet)$('#main').replaceChildren(node('div',{class:'loader',text:'Beynin okunuyor…'}));
  const staged=node('div');
  try{await ({overview,activity:activities,memories}[route])(staged);if(version!==renderId||$('#shell').hidden)return;$('#main').replaceChildren(...staged.childNodes);$('#footer-health').textContent='Son kontrol: '+new Date().toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'});}
  catch(error){if(version===renderId)showError(error);}
}
function syncMenu(){const hidden=window.matchMedia('(max-width:760px)').matches&&!$('.sidebar').classList.contains('open');$('.sidebar').inert=hidden;$('.sidebar').setAttribute('aria-hidden',String(hidden));$('#menu-button').setAttribute('aria-expanded',String(!hidden));}
async function start(){document.body.classList.toggle('dark',localStorage.getItem('brain-theme')==='dark');syncMenu();try{await api('observer');$('#login').hidden=true;$('#shell').hidden=false;await render();}catch(error){login(error.status===403?'':error.message);}}
$('#login-form').addEventListener('submit',async event=>{event.preventDefault();const submit=event.submitter;if(submit)submit.disabled=true;try{await api('login',{token:$('#login-key').value,remember:$('#remember-me').checked});$('#login-key').value='';$('#login-error').textContent='';await start();}catch(error){$('#login-error').textContent=error.message;}finally{if(submit)submit.disabled=false;}});
$('#logout-button').addEventListener('click',async()=>{try{await api('logout',{});login();}catch(error){showError(error);}});
$('#refresh-button').addEventListener('click',()=>render());
$('#theme-button').addEventListener('click',()=>{document.body.classList.toggle('dark');localStorage.setItem('brain-theme',document.body.classList.contains('dark')?'dark':'light');});
$('#menu-button').addEventListener('click',()=>{$('.sidebar').classList.toggle('open');syncMenu();});
window.addEventListener('resize',syncMenu);
window.addEventListener('hashchange',()=>{$('.sidebar').classList.remove('open');syncMenu();render();});
setInterval(async()=>{if(document.hidden||$('#shell').hidden||$('#dialog').open||refreshing||document.activeElement?.matches('input'))return;refreshing=true;try{await render({quiet:true});}finally{refreshing=false;}},20000);
await start();

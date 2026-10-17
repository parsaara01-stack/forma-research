"use strict";
// A deterministic scenario, deliberately separate from an estimated trading rule
function timingOutcome({price, eps, pe, dilution, years, hurdle}) {
 const values=[price,eps,pe,dilution,years,hurdle];
 if(values.some(x=>typeof x!=='number'||!Number.isFinite(x))||price<=0||eps<=0||pe<=0||dilution<0||years<=0||hurdle<0)return {valid:false};
 const dilutedEPS=eps/(1+dilution/100), futurePrice=dilutedEPS*pe;
 const annualReturn=(futurePrice/price)**(1/years)-1;
 const entryForHurdle=futurePrice/(1+hurdle/100)**years;
 return {valid:true,dilutedEPS,futurePrice,annualReturn,entryForHurdle};
}
if(typeof module!=='undefined')module.exports={timingOutcome};
if(typeof document!=='undefined'){
 let timingRows=[], selectionRequest=0, searchMatches=[], activeMatch=-1;
 const t=id=>document.getElementById(id);
 const n=id=>t(id).value.trim()===''?NaN:Number(t(id).value);
 const dollars=x=>'$'+x.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
 const percent=x=>(x<0?'−':'+')+Math.abs(x*100).toFixed(1)+'%';
 const h=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function timingValues(){return {price:n('entry-price'),eps:n('future-eps'),pe:n('exit-pe'),dilution:n('extra-shares'),years:n('holding-years'),hurdle:n('return-hurdle')};}
 function updateTiming(){
  t('exit-pe-value').textContent=t('exit-pe').value+'×';t('extra-shares-value').textContent=t('extra-shares').value+'%';
  const values=timingValues(),out=timingOutcome(values);
  t('timing-return').textContent=out.valid?percent(out.annualReturn):'—';
  t('future-price').textContent=out.valid?dollars(out.futurePrice):'—';
  t('hurdle-price').textContent=out.valid?dollars(out.entryForHurdle):'—';
  t('timing-reading').textContent=out.valid?`At ${dollars(values.price)}, this scenario ${out.annualReturn>=values.hurdle/100?'meets':'falls short of'} your ${values.hurdle}% yearly return requirement`:'Enter a price and a positive future EPS estimate to explore the scenario';
  if(!out.valid){t('payoff-matrix').innerHTML='<p class="matrix-empty">Price / earnings is not a useful valuation rule while projected earnings are zero or negative</p>';return;}
  const factors=[.75,1,1.25];
  t('payoff-matrix').innerHTML='<table class="matrix"><caption class="sr-only">Annual price return across earnings and valuation assumptions</caption><thead><tr><th scope="col">EPS / P:E</th>'+factors.map(f=>`<th scope="col">${(values.pe*f).toFixed(1)}×</th>`).join('')+'</tr></thead><tbody>'+factors.map((f,i)=>'<tr><th scope="row">'+dollars(values.eps*f)+'</th>'+factors.map((p,j)=>{const x=timingOutcome({...values,eps:values.eps*f,pe:values.pe*p});return `<td class="${x.annualReturn>=0?'positive':'negative'} ${i===1&&j===1?'base-case':''}">${percent(x.annualReturn)}${i===1&&j===1?'<span class="sr-only"> your base scenario</span>':''}</td>`;}).join('')+'</tr>').join('')+'</tbody></table>';
 }
 function resetTiming(){selectionRequest++;t('timing-company').value='';Object.entries({'entry-price':50,'reported-eps':2,'future-eps':3,'exit-pe':20,'extra-shares':0,'holding-years':2,'return-hurdle':10}).forEach(([id,v])=>t(id).value=v);t('timing-source').textContent='Illustrative business · $50 entry price · $2 annual EPS';t('assumption-note').textContent='Example assumptions · Edit any field · No analyst forecast';t('company-search').value='IWM · Market view';window.renderMarketCompany?.(null);t('earnings-trend').textContent='Reported earnings history appears when you choose a company';updateTiming();}
 window.loadTimingCompanies=rows=>{timingRows=rows;t('timing-company').innerHTML='<option value="">Market view · IWM</option>'+rows.map(r=>`<option value="${h(r.ticker)}">${h(r.ticker)} — ${h(r.name)}</option>`).join('');};
 t('timing-company').addEventListener('change',async()=>{
  const token=++selectionRequest, ticker=t('timing-company').value;
  if(!ticker){resetTiming();return;}
  const r=timingRows.find(r=>r.ticker===ticker);if(!r)return;
  t('entry-price').value=Number.isFinite(r.holding_price)&&r.holding_price>0?r.holding_price:'';
  t('reported-eps').value=Number.isFinite(r.reported_eps)?r.reported_eps:'';
  const years=n('holding-years');
  const profitable=Number.isFinite(r.reported_eps)&&r.reported_eps>0;
  t('future-eps').value=profitable?(r.reported_eps*1.1**years).toFixed(2):'1.00';t('extra-shares').value='0';t('exit-pe').value='20';
  t('assumption-note').textContent=profitable?'Example: EPS grows 10% a year · 20× future earnings · Edit these assumptions':'Recovery example: EPS reaches $1 · 20× future earnings · Edit these assumptions';
  t('company-search').value=r.ticker+' · '+r.name;window.renderMarketCompany?.(r);
  t('timing-source').textContent=`Holdings price: ${r.price_date||'unavailable'} · Annual EPS period: ${r.eps_end||'not available'} · ${r.observation_status==='stale-previous-snapshot'?'Older saved report':'Unreviewed report'}`;
  t('earnings-trend').textContent='Loading reported earnings history';updateTiming();
  try{
   const detail=await fetchCompany(ticker);if(token!==selectionRequest)return;
   const history=[...(detail.earnings?.annual_history||[])].reverse();
   t('earnings-trend').innerHTML='<h4>Reported annual EPS</h4>'+(history.length?'<div class="eps-history">'+history.map(r=>`<div><span>${h(r.end)}</span><strong>${r.eps?dollars(r.eps.value):'—'}</strong><small>Filed ${h(r.filed)}</small></div>`).join('')+'</div>':'<p>Comparable annual EPS is not available for this company</p>')+'<p class="input-note">Original annual reports · Not current-quarter or analyst estimates</p>';
  }catch{if(token===selectionRequest)t('earnings-trend').textContent='Earnings history could not load — the fields above retain their source dates';}
 });

 function closeSearch(){t('company-options').hidden=true;t('company-search').setAttribute('aria-expanded','false');t('company-search').removeAttribute('aria-activedescendant');activeMatch=-1;}
 function chooseMatch(ticker){t('timing-company').value=ticker;closeSearch();t('timing-company').dispatchEvent(new Event('change',{bubbles:true}));}
 function showSearch(){
  const query=t('company-search').value.trim().toLowerCase();
  const filtered=timingRows.filter(r=>(r.ticker+' '+r.name).toLowerCase().includes(query));
  searchMatches=[{ticker:'',name:'IWM · Market view'},...filtered.slice(0,25)];activeMatch=-1;
  t('company-options').innerHTML=searchMatches.map((r,i)=>`<div id="company-option-${i}" role="option" aria-selected="false" data-ticker="${h(r.ticker)}"><strong>${h(r.ticker||'IWM')}</strong><span>${h(r.name)}</span></div>`).join('')+(filtered.length?'':'<div class="no-company-match">No matching company</div>');
  t('company-options').hidden=false;t('company-search').setAttribute('aria-expanded','true');t('company-search').removeAttribute('aria-activedescendant');t('picker-status').textContent=filtered.length+' matching stocks'+(filtered.length>25?' · refine your search':'');
 }
 t('company-search').addEventListener('focus',()=>{t('company-search').select();showSearch();});
 t('company-search').addEventListener('input',showSearch);
 t('company-options').addEventListener('mousedown',event=>event.preventDefault());
 t('company-options').addEventListener('click',event=>{const option=event.target.closest('[role=option]');if(option)chooseMatch(option.dataset.ticker);});
 t('company-search').addEventListener('blur',closeSearch);
 t('company-search').addEventListener('keydown',event=>{
  if(event.key==='Escape'){event.preventDefault();closeSearch();return;}
  if(event.key==='Enter'){event.preventDefault();if(!t('company-options').hidden&&activeMatch>=0)chooseMatch(searchMatches[activeMatch].ticker);return;}
  if(!['ArrowDown','ArrowUp'].includes(event.key))return;
  event.preventDefault();if(t('company-options').hidden)showSearch();activeMatch=(activeMatch+(event.key==='ArrowDown'?1:-1)+searchMatches.length)%searchMatches.length;
  t('company-options').querySelectorAll('[role=option]').forEach((option,i)=>option.setAttribute('aria-selected',String(i===activeMatch)));
  const option=t('company-option-'+activeMatch);t('company-search').setAttribute('aria-activedescendant',option.id);option.scrollIntoView({block:'nearest'});
 });

 t('timing-form').addEventListener('submit',e=>e.preventDefault());
 t('timing-form').addEventListener('input',()=>{t('assumption-note').textContent='Your assumptions · No analyst forecast';updateTiming();});t('timing-form').addEventListener('change',updateTiming);t('reset-timing').addEventListener('click',resetTiming);
 const tabs=[t('tab-timing'),t('tab-companies')];
 function activateTab(index){tabs.forEach((tab,i)=>{tab.setAttribute('aria-selected',String(i===index));tab.tabIndex=i===index?0:-1;t(tab.getAttribute('aria-controls')).hidden=i!==index;});}
 tabs.forEach((tab,i)=>{tab.addEventListener('click',()=>activateTab(i));tab.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?1:1-i;activateTab(next);tabs[next].focus();}});});
 window.loadMacro=async()=>{
  try{
   const response=await fetch('./data/macro.json',{cache:'no-store'});if(!response.ok)throw Error('Unavailable');const data=await response.json();if(!Array.isArray(data.series))throw Error('Invalid data');
   t('macro-cards').innerHTML=data.series.map(s=>{
    const points=(s.history||[]).filter(p=>Number.isFinite(p.value));let spark='';
    if(points.length>1){const values=points.map(p=>p.value),lo=Math.min(...values),hi=Math.max(...values); const line=points.map((p,i)=>`${(i/(points.length-1)*160).toFixed(1)},${(35-(p.value-lo)/(hi-lo||1)*30).toFixed(1)}`).join(' ');spark=`<svg viewBox="0 0 160 40" aria-hidden="true"><polyline points="${line}" fill="none" stroke="currentColor" stroke-width="2"/></svg>`;}
    return `<article class="macro-card"><a href="${/^https:\/\/fred.stlouisfed.org\/series\/[A-Z0-9]+$/.test(s.source_url)?h(s.source_url):'#research'}" target="_blank" rel="noopener noreferrer">${h(s.label)} ↗</a><strong>${Number.isFinite(s.value)?s.value.toFixed(2)+(s.unit==='%'?'%':' pp'):'—'}</strong>${spark}<span>${h(s.date)}${s.status==='stale'?' · Older reading':''}</span><small>${Number.isFinite(s.change_90d)?(s.change_90d>=0?'+':'')+s.change_90d.toFixed(2)+' pp over 90 days':'Monthly reading · Year-over-year inflation'}</small></article>`;
   }).join('');
   t('macro-status').textContent=`${data.refresh_status==='saved-after-source-failure'?'Saved readings · refresh unavailable':'FRED'} · Checked ${data.asof_cutoff} · About one year shown`;
  }catch{t('macro-cards').textContent='Economic data could not load — the scenario tool still works';t('macro-status').textContent='No economic readings have been filled in';}
 };
 updateTiming();
}

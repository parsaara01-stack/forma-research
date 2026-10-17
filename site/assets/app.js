"use strict";
const hypotheses = [
 ["H01", "When is early too early?", "Does waiting for earnings to improve avoid losses, or miss too much of the rebound?"],
 ["H02", "When has the price caught up?", "Do forecast upgrades still help once a higher stock price already reflects them?"],
 ["H03", "What does the economy change?", "Do rates, inflation, jobs and access to credit change when a small-cap recovery is worth buying?"],
 ["H04", "Which profits can we trust?", "Do cash flow, margins and EPS together tell us more than reported EPS growth alone?"],
 ["H05", "Can the company fund the wait?", "Do debt due dates, interest costs and available cash change the value of an earnings recovery?"],
 ["H06", "What do new shares cost?", "Does growth still improve the outcome for each original share after new stock is issued?"],
 ["H07", "Is the outlook getting better?", "Do changes in analyst EPS estimates and the spread of forecasts help identify a better entry window?"],
 ["H08", "Is the whole index improving?", "How much improvement comes from the same companies, and how much from stocks joining or leaving?"],
 ["H09", "Does a timing rule earn its keep?", "After costs, risk and time spent waiting, can it improve on holding IWM or investing each month?"],
];
const $ = id => document.getElementById(id);
const fmt = (x,d=1) => Number.isFinite(x) ? x.toFixed(d) : '—';
const fmtM = x => Number.isFinite(x) ? (x<0?'−':'')+'$'+Math.abs(x).toFixed(1)+'M' : '—';
const pct = (x, d=1) => Number.isFinite(x) ? (x*100).toFixed(d)+'%' : '—';
function renderStatic(){
  $('hypotheses').innerHTML = hypotheses.map(([id,title,question]) => `<article class="hypothesis"><span class="hyp-id">${id}</span><h3>${title}</h3><p>${question}</p><span class="status-tag">To be tested</span></article>`).join('');
}
function simulate(growth, margin, cost, capex, dilution){
  const revenue = 150*(1+growth/100);
  const opIncome = revenue*margin/100;
  const interest = 90*cost/100;
  const pretax = opIncome-interest;
  const incomeTaxes = Math.max(0,pretax)*.25;
  const da = revenue*.03;
  const wc = (revenue-150)*.10; // negative growth implies working-capital release
  const investment = revenue*capex/100 + wc;
  const cashBeforeReinvestment = opIncome-interest-incomeTaxes+da;
  const equityCash = cashBeforeReinvestment-investment;
  return {revenue, opIncome, interest, incomeTaxes, da, wc, investment, cashBeforeReinvestment, equityCash, perShare: equityCash/(1+dilution/100)};
}
function updateSimulator(){
  const v = ['growth','margin','cost','capex','dilution'].map(id=>Number($(id).value));
  ['growth','margin','cost','capex','dilution'].forEach((id,i)=>$(id+'-value').textContent=v[i]+'%');
  const x=simulate(...v);
  $('owner-cash').textContent=fmtM(x.equityCash);
  $('op-income').textContent=fmtM(x.opIncome);
  $('interest').textContent=fmtM(x.interest);
  $('owner-share').textContent=fmtM(x.perShare);
  $('cash-bar').innerHTML = [
    ['Cash before new investment', x.cashBeforeReinvestment],
    ['Equipment + extra working cash', -x.investment],
    ['Cash left for shareholders', x.equityCash]
  ].map(([label,value])=>`<div class="bridge-row"><span>${label}</span><strong>${fmtM(value)}</strong></div>`).join('');
}

function asNumber(x){return typeof x==='number' && Number.isFinite(x)?x:null;}
function escapeHTML(s){return String(s??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
let records=[], currentPage=0; const PAGE_SIZE=40; const companyDetails=new Map(); let detailRequest=0;
function secURL(value){
 try { const u=new URL(value);return u.protocol==='https:'&&u.hostname==='www.sec.gov'&&u.pathname.startsWith('/Archives/edgar/data/')?u.href:null; } catch { return null; }
}
const statusLabel=r=>r.observation_status==='stale-previous-snapshot'?'Older saved report':(r.has_facts??Object.keys(r.facts||{}).length)?'Annual SEC report · review pending':'Waiting for data';
function row(r){
 const f=r.facts||{}; const revenue=asNumber(r.revenue??f.revenue?.value); const margin=asNumber(r.metrics?.operating_margin);const fcf=asNumber(r.metrics?.free_cash_flow);const ratio=asNumber(r.metrics?.debt_to_assets);
 const money=x=>x===null?'—':('$'+(x/1e6).toLocaleString('en-US',{maximumFractionDigits:1})+'M');
 const url=secURL(r.primary_filing_url);
 const link=url?`<a class="filing-link" href="${escapeHTML(url)}" rel="noopener noreferrer" target="_blank" aria-label="${escapeHTML(r.ticker)} SEC filing">SEC ↗</a>`:'<span class="pending">Pending</span>';
 return `<tr><td><button class="company-button" type="button" data-company="${escapeHTML(r.ticker)}">${escapeHTML(r.name||r.ticker)} <span aria-hidden="true">↗</span></button><span class="ticker">${escapeHTML(r.ticker)} · ${escapeHTML(r.group||'Other')}</span><span class="observation-label ${r.observation_status==='stale-previous-snapshot'?'stale':''}">${statusLabel(r)}</span></td><td>${escapeHTML(r.fiscal_end||'—')}</td><td>${money(revenue)}</td><td>${margin===null?'—':pct(margin)}</td><td>${money(fcf)}</td><td>${ratio===null?'—':pct(ratio)}</td><td>${link}</td></tr>`;
}
function updateTable(){
 const q=$('search-company').value.toLowerCase().trim();const filter=$('filter-status').value; const sector=$('filter-sector').value;
 const filtered=records.filter(r=>{
  const match=((r.name||'')+' '+r.ticker).toLowerCase().includes(q);
  const available=r.has_facts??Object.keys(r.facts||{}).length>0;
  const stale=r.observation_status==='stale-previous-snapshot';
  return match&&(sector==='all'||r.group===sector)&&(filter==='all'||(filter==='available'&&available&&!stale)||(filter==='stale'&&stale)||(filter==='pending'&&!available));
 });
 currentPage=Math.min(currentPage,Math.max(0,Math.ceil(filtered.length/PAGE_SIZE)-1));
 const page=filtered.slice(currentPage*PAGE_SIZE,(currentPage+1)*PAGE_SIZE);
 $('company-rows').innerHTML=page.length?page.map(row).join(''):'<tr><td colspan="7">No matches — try another name or filter</td></tr>';
 $('result-count').textContent=`${filtered.length.toLocaleString()} of ${records.length.toLocaleString()} listed stocks · ${page.length} shown`;
 $('page-label').textContent=`Page ${currentPage+1} of ${Math.max(1,Math.ceil(filtered.length/PAGE_SIZE))}`;
 $('page-prev').disabled=currentPage===0; $('page-next').disabled=(currentPage+1)*PAGE_SIZE>=filtered.length;
}
const fieldLabels={revenue:'Revenue',operating_income:'Profit before interest and tax',net_income:'Net income',operating_cash_flow:'Cash from running the business',capex:'Equipment and property spending',total_assets:'Total assets',total_liabilities:'Total liabilities',equity:'Shareholders’ stake on the books',cash:'Cash available to use',long_term_debt:'Long-term debt due after this year',current_debt:'Long-term debt due within a year',short_term_borrowings:'Short-term borrowings',interest_expense:'Reported interest cost',depreciation:'Asset costs spread across years',share_based_compensation:'Pay awarded in shares',current_assets:'Assets available within a year',current_liabilities:'Bills due within a year',diluted_shares:'Average share count including potential new shares',equity_issuance:'Cash raised by selling shares',share_repurchases:'Cash spent buying back shares'};
for(let n=1;n<=5;n++)fieldLabels['maturity_year_'+n]='Debt due in year '+n;
fieldLabels.maturity_thereafter='Debt due after year five';
function factValue(f){
 if(!f||!Number.isFinite(f.value))return 'Unavailable';
 if(f.unit==='shares')return (f.value/1e6).toLocaleString('en-US',{maximumFractionDigits:2})+'M shares';
 return '$'+(f.value/1e6).toLocaleString('en-US',{maximumFractionDigits:2})+'M';
}
async function fetchCompany(ticker){
 if(!/^[A-Z0-9.\-]+$/.test(ticker))throw Error('Invalid ticker');
 if(companyDetails.has(ticker))return companyDetails.get(ticker);
 const response=await fetch('./data/companies/'+encodeURIComponent(ticker)+'.json');
 if(!response.ok)throw Error('Report unavailable');
 const detail=await response.json();if(detail.ticker!==ticker)throw Error('Report identity mismatch');
 companyDetails.set(ticker,detail);return detail;
}
async function showCompany(ticker){
 const brief=records.find(x=>x.ticker===ticker);if(!brief)return; const request=++detailRequest;
 $('detail-title').textContent=brief.name||ticker;
 $('detail-body').textContent='Loading the source report';
 $('company-detail').showModal();$('close-detail').focus();
 let r;
 try{r=await fetchCompany(ticker);}catch{ $('detail-body').textContent='This report could not load — close and try again';return; }
 if(!$('company-detail').open||request!==detailRequest)return;
 $('detail-title').textContent=r.name||r.ticker;
 const facts=r.facts||{};const m=r.metrics||{};
 const maturity=[1,2,3,4,5].map(n=>`<div><span>Year ${n}</span><strong>${factValue(facts['maturity_year_'+n])}</strong></div>`).join('');
 const factRows=Object.entries(facts).map(([k,f])=>`<tr><th scope="row">${escapeHTML(fieldLabels[k]||k.replaceAll('_',' '))}<small>${escapeHTML(f.tag)}</small></th><td>${factValue(f)}</td><td>${escapeHTML(f.start?f.start+' → '+f.end:f.end)}<small>Filed ${escapeHTML(f.filed)}</small></td></tr>`).join('');
 const url=secURL(r.primary_filing_url);const source=r.source_document;
 $('detail-body').innerHTML=`<p class="detail-meta">${escapeHTML(r.ticker)} · ${escapeHTML(r.group)} · ${statusLabel(r)}</p>
 <p>${r.fiscal_end?'Annual period ending '+escapeHTML(r.fiscal_end)+'<br>Figures come from one original annual report':'We have not loaded this company’s reports yet'} <br>The figures still need review before use in research</p>
 ${r.refresh_error?`<p class="data-alert">Latest refresh failed: ${escapeHTML(r.refresh_error)}<br>Saved figures keep their original report date</p>`:''}
 <h3>Borrowing & ability to pay</h3><div class="capital-metrics"><div><span>Profit compared with interest cost</span><strong>${Number.isFinite(m.interest_coverage)?fmt(m.interest_coverage)+'×':'Unavailable'}</strong></div><div><span>Short-term assets / bills due</span><strong>${Number.isFinite(m.current_ratio)?fmt(m.current_ratio)+'×':'Unavailable'}</strong></div><div><span>Cash / yearly cash used by operations</span><strong>${Number.isFinite(m.cash_runway_years)?fmt(m.cash_runway_years)+' years':'Unavailable'}</strong></div></div>
 <p class="detail-note">The first figure compares profit before interest and tax with reported interest cost<br>The cash figure assumes the same yearly cash loss from operations — it leaves out investments, future spending and new funding<br>Banks and insurers need a different approach</p>
 <h3>When debt is due</h3><div class="maturity-grid">${maturity}</div><p class="detail-note">Debt due in each year after the reporting date<br>After year five: ${factValue(facts.maturity_thereafter)}<br>Missing figures are not zero<br>These totals may cover only part of the debt — check the borrowing notes before adding them up</p>
 <p class="review-note">The cost of raising new money: <strong>not yet estimated</strong><br>We still need to review changing interest rates, loan conditions, pledged assets, leases and debt that can turn into shares</p>
 <h3>Figures from the report</h3>${url?`<a class="inline-link" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">Open the original SEC report ↗</a>`:''}
 ${factRows?`<div class="table-wrap facts-table" tabindex="0" role="region" aria-label="Reported figures; scroll to see more"><table><caption class="sr-only">${escapeHTML(r.ticker)} source facts</caption><thead><tr><th>Figure / source label</th><th>Reported figure</th><th>Period / report date</th></tr></thead><tbody>${factRows}</tbody></table></div>`:'<p>Missing figures have been left blank</p>'}
 ${source?`<details class="source-fingerprint"><summary>Where the data came from</summary><dl><dt>Downloaded (UTC)</dt><dd>${escapeHTML(source.retrieved_at)}</dd><dt>File fingerprint (SHA-256)</dt><dd>${escapeHTML(source.sha256)}</dd><dt>Source</dt><dd>${escapeHTML(source.url)}</dd><dt>Saved source file</dt><dd>${escapeHTML(source.raw_path||'Source file not saved in this update')}</dd></dl></details>`:''}
 <p class="detail-note">The SEC database can change over time<br>Filtering by report date cannot fully recreate what someone knew in the past<br>These figures do not establish a stock forecast</p>`;

}
async function loadData(){
 try {
 const resp=await fetch('./data/catalog.json',{cache:'no-store'});if(!resp.ok)throw Error('HTTP '+resp.status);
 const data=await resp.json();if(!Array.isArray(data.companies))throw Error('Invalid dataset');
 records=data.companies.filter(r=>r&&typeof r.ticker==='string');
 $('tracked-count').textContent=records.length;
 const n=records.filter(r=>r.has_facts).length;
 const stale=records.filter(r=>r.observation_status==='stale-previous-snapshot').length;
 $('facts-count').textContent=n;
 $('refresh-date').textContent=data.last_successful_refresh?data.last_successful_refresh.slice(0,10)+' UTC':'Not yet run';
 $('table-status').textContent=n?`${n} of ${records.length} companies with annual reports · ${stale} using older saved data · review pending`:'Waiting for the first company reports';
 $('data-cutoff').textContent=data.asof_cutoff?`Reports filed by ${data.asof_cutoff} · Annual figures only · Holdings prices have separate dates`:'Figures appear when reports load';
 const warnings=data.refresh_warnings||[];$('data-warning').hidden=!warnings.length;
 $('data-warning').textContent=warnings.length?`${warnings.length} stocks need further source work — older or missing figures stay labeled · Open a company for details`:'';
 const u=data.universe||{}; const count=records.length.toLocaleString();
 $('hero-coverage').textContent=`${count} listed stocks · IWM holdings ${u.effective||'date unavailable'}`;
 $('tab-count').textContent=count;
 $('universe-note').textContent='All usable listed stocks in IWM’s published holdings — a Russell 2000 proxy, not certified index membership';
 $('coverage-detail').textContent=`Holdings dated ${u.effective||'unknown'} · ${count} listed stocks · ${(u.excluded_holdings||[]).length} other positions kept outside the company panel · ${u.changes?.basis==='initial complete holdings import'?'First full import':`${u.changes?.added?.length||0} additions and ${u.changes?.removed?.length||0} removals since the last saved list`} · Holdings and macro checked each weekday, company reports twice a week`;
 $('filter-sector').innerHTML='<option value="all">Every sector</option>'+[...new Set(records.map(r=>r.group).filter(Boolean))].sort().map(x=>`<option value="${escapeHTML(x)}">${escapeHTML(x)}</option>`).join('');
 loadTimingCompanies(records);
 updateTable();
 } catch(err){
 $('table-status').textContent='Dataset unavailable';
 $('company-rows').innerHTML='<tr><td colspan="7">The company figures could not load — please reload the page</td></tr>';
 $('data-warning').hidden=false;$('data-warning').textContent='Company figures are unavailable — no figures have been filled in';
 }
}
renderStatic();['growth','margin','cost','capex','dilution'].forEach(id=>$(id).addEventListener('input',updateSimulator));
$('reset-sim').addEventListener('click',()=>{Object.entries({growth:10,margin:16,cost:8,capex:9,dilution:3}).forEach(([id,v])=>$(id).value=v);updateSimulator();});
$('search-company').addEventListener('input',()=>{currentPage=0;updateTable();}); ['filter-status','filter-sector'].forEach(id=>$(id).addEventListener('change',()=>{currentPage=0;updateTable();}));
$('page-prev').addEventListener('click',()=>{currentPage--;updateTable();});$('page-next').addEventListener('click',()=>{currentPage++;updateTable();});
$('company-rows').addEventListener('click',event=>{const button=event.target.closest('[data-company]');if(button)showCompany(button.dataset.company);});
$('close-detail').addEventListener('click',()=>$('company-detail').close());
$('company-detail').addEventListener('click',event=>{if(event.target===$('company-detail')){const rect=$('company-detail').getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)$('company-detail').close();}});
function toggleMenu(open){$('mobile-menu').setAttribute('aria-expanded',String(open));$('mobile-menu').setAttribute('aria-label',open?'Close navigation':'Open navigation');document.querySelector('.nav').classList.toggle('open',open);}
$('mobile-menu').addEventListener('click',()=>toggleMenu($('mobile-menu').getAttribute('aria-expanded')!=='true'));
document.querySelectorAll('.nav a').forEach(a=>a.addEventListener('click',()=>toggleMenu(false)));
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&$('mobile-menu').getAttribute('aria-expanded')==='true'){toggleMenu(false);$('mobile-menu').focus();}});
updateSimulator();loadData();loadMacro();

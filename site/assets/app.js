"use strict";
const framework = [
  ["01", "Operations", "Revenue durability, margins, unit economics and operating quality.", "GROWTH"],
  ["02", "Capital deployment", "Maintenance capex, expansion investment, working capital and incremental returns.", "INVESTMENT"],
  ["03", "Financing structure", "Debt maturities, secured obligations, leases, covenants and marginal capital cost.", "FINANCING"],
  ["04", "Resilience", "Liquidity runway, dilution, financing access and downside survival.", "RISK"],
  ["05", "Expectations", "Consensus revisions, forward narratives and what prices already imply.", "BELIEFS"],
  ["06", "Price discovery", "Risk-adjusted returns, liquidity, factor exposures and possible mispricing.", "MARKETS"]
];
const hypotheses = [
  ["H01", "The capital conversion gap", "Does growth funded by external capital generate lower per-share economic value than internally funded growth?"],
  ["H02", "The refinancing cliff", "Does exposure to debt repricing predict operating cuts and subsequent equity underperformance?"],
  ["H03", "Incremental return on capital", "Is incremental ROIC more informative than trailing ROIC about growth durability?"],
  ["H04", "The recovery illusion", "Can cash-flow quality explain which forecast earnings rebounds persist?"],
  ["H05", "Dilution versus survival", "When does equity issuance preserve valuable real options, and when does it destroy per-share value?"],
  ["H06", "The index composition effect", "How much index earnings growth arises from entry/exit, restatements, and denominator effects?"],
];
const $ = id => document.getElementById(id);
const fmt = (x,d=1) => Number.isFinite(x) ? x.toFixed(d) : '—';
const fmtM = x => Number.isFinite(x) ? (x<0?'−':'')+'$'+Math.abs(x).toFixed(1)+'M' : '—';
const pct = (x, d=1) => Number.isFinite(x) ? (x*100).toFixed(d)+'%' : '—';
function renderStatic(){
  $('dimensions').innerHTML = framework.map(([id,title,description,category]) => `<article class="dimension-card"><span class="dimension-no">${id}</span><h3>${title}</h3><p>${description}</p><div class="dimension-foot"><span>${category}</span><span aria-hidden="true">↗</span></div></article>`).join('');
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
    ['Before reinvestment', x.cashBeforeReinvestment],
    ['Capex + working capital', -x.investment],
    ['Available to equity', x.equityCash]
  ].map(([label,value])=>`<div class="bridge-row"><span>${label}</span><strong>${fmtM(value)}</strong></div>`).join('');
}

function asNumber(x){return typeof x==='number' && Number.isFinite(x)?x:null;}
function escapeHTML(s){return String(s??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
let records=[];
function secURL(value){
 try { const u=new URL(value);return u.protocol==='https:'&&u.hostname==='www.sec.gov'&&u.pathname.startsWith('/Archives/edgar/data/')?u.href:null; } catch { return null; }
}
const statusLabel=r=>r.observation_status==='stale-previous-snapshot'?'Stale snapshot':Object.keys(r.facts||{}).length?'SEC tagged · unreviewed':'Awaiting data';
function row(r){
 const f=r.facts||{}; const revenue=asNumber(f.revenue?.value); const margin=asNumber(r.metrics?.operating_margin);const fcf=asNumber(r.metrics?.free_cash_flow);const ratio=asNumber(r.metrics?.debt_to_assets);
 const money=x=>x===null?'—':('$'+(x/1e6).toLocaleString('en-US',{maximumFractionDigits:1})+'M');
 const url=secURL(r.primary_filing_url);
 const link=url?`<a class="filing-link" href="${escapeHTML(url)}" rel="noopener noreferrer" target="_blank" aria-label="${escapeHTML(r.ticker)} SEC filing">SEC ↗</a>`:'<span class="pending">Pending</span>';
 return `<tr><td><button class="company-button" type="button" data-company="${escapeHTML(r.ticker)}">${escapeHTML(r.name||r.ticker)} <span aria-hidden="true">↗</span></button><span class="ticker">${escapeHTML(r.ticker)} · ${escapeHTML(r.group||'Other')}</span><span class="observation-label ${r.observation_status==='stale-previous-snapshot'?'stale':''}">${statusLabel(r)}</span></td><td>${escapeHTML(r.fiscal_end||'—')}</td><td>${money(revenue)}</td><td>${margin===null?'—':pct(margin)}</td><td>${money(fcf)}</td><td>${ratio===null?'—':pct(ratio)}</td><td>${link}</td></tr>`;
}
function updateTable(){
 const q=$('search-company').value.toLowerCase().trim();const filter=$('filter-status').value;
 const filtered=records.filter(r=>{
  const match=((r.name||'')+' '+r.ticker).toLowerCase().includes(q);
  const available=Object.keys(r.facts||{}).length>0;
  const stale=r.observation_status==='stale-previous-snapshot';
  return match&&(filter==='all'||(filter==='available'&&available&&!stale)||(filter==='stale'&&stale)||(filter==='pending'&&!available));
 });
 $('company-rows').innerHTML=filtered.length?filtered.map(row).join(''):'<tr><td colspan="7">No matching observations. Try another company or status.</td></tr>';
 $('result-count').textContent=`${filtered.length} of ${records.length} companies`;
}
const fieldLabels={revenue:'Revenue',operating_income:'Operating income',net_income:'Net income',operating_cash_flow:'Operating cash flow',capex:'Capital expenditure',total_assets:'Total assets',total_liabilities:'Total liabilities',equity:'Stockholders’ equity',cash:'Unrestricted cash & equivalents',long_term_debt:'Long-term debt, noncurrent',current_debt:'Current portion of long-term debt',short_term_borrowings:'Short-term borrowings',interest_expense:'Reported interest expense',depreciation:'Depreciation & amortization',share_based_compensation:'Stock-based compensation',current_assets:'Current assets',current_liabilities:'Current liabilities',diluted_shares:'Weighted-average diluted shares',equity_issuance:'Common stock cash proceeds',share_repurchases:'Cash share repurchases'};
function factValue(f){
 if(!f||!Number.isFinite(f.value))return 'Unavailable';
 if(f.unit==='shares')return (f.value/1e6).toLocaleString('en-US',{maximumFractionDigits:2})+'M shares';
 return '$'+(f.value/1e6).toLocaleString('en-US',{maximumFractionDigits:2})+'M';
}
function showCompany(ticker){
 const r=records.find(x=>x.ticker===ticker);if(!r)return;
 $('detail-title').textContent=r.name||r.ticker;
 const facts=r.facts||{};const profile=r.capital_profile||{};const m=r.metrics||{};
 const maturity=[1,2,3,4,5].map(n=>`<div><span>Year ${n}</span><strong>${factValue(facts['maturity_year_'+n])}</strong></div>`).join('');
 const factRows=Object.entries(facts).map(([k,f])=>`<tr><th scope="row">${escapeHTML(fieldLabels[k]||k.replaceAll('_',' '))}<small>${escapeHTML(f.tag)}</small></th><td>${factValue(f)}</td><td>${escapeHTML(f.start?f.start+' → '+f.end:f.end)}<small>Filed ${escapeHTML(f.filed)}</small></td></tr>`).join('');
 const url=secURL(r.primary_filing_url);const source=r.source_document;
 $('detail-body').innerHTML=`<p class="detail-meta">${escapeHTML(r.ticker)} · ${escapeHTML(r.group)} · ${statusLabel(r)}</p>
 <p>${r.fiscal_end?'Annual period ending '+escapeHTML(r.fiscal_end)+'. Original 10-K, one filing and statement duration.':'This company has no loaded observations yet. A successful SEC refresh is required.'} Tagged facts require accounting review before research use.</p>
 ${r.refresh_error?`<p class="data-alert">Latest refresh failed: ${escapeHTML(r.refresh_error)}. Any values shown retain their original filing date.</p>`:''}
 <h3>Capital & resilience</h3><div class="capital-metrics"><div><span>Interest coverage</span><strong>${Number.isFinite(m.interest_coverage)?fmt(m.interest_coverage)+'×':'Unavailable'}</strong></div><div><span>Current ratio</span><strong>${Number.isFinite(m.current_ratio)?fmt(m.current_ratio)+'×':'Unavailable'}</strong></div><div><span>Cash / operating burn</span><strong>${Number.isFinite(m.cash_runway_years)?fmt(m.cash_runway_years)+' years':'Unavailable'}</strong></div></div>
 <p class="detail-note">Operating income / reported interest is an accounting proxy. Cash coverage holds annual operating burn constant, excludes securities and other investments, and excludes future investing and financing flows. It is not total liquidity runway. Bank and insurer ratios require a separate protocol.</p>
 <h3>Debt maturities</h3><div class="maturity-grid">${maturity}</div><p class="detail-note">Principal buckets relative to fiscal end. Thereafter: ${factValue(facts.maturity_thereafter)}. Missing means unavailable, never zero. Standard tags may omit custom or instrument-level disclosures; reconcile to the debt note before aggregating.</p>
 <p class="review-note">Marginal financing cost and WACC: <strong>not estimated.</strong> Floating rates, covenants, collateral, leases, convertible terms and maintenance capex require source review.</p>
 <h3>Filing evidence</h3>${url?`<a class="inline-link" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">Open original SEC filing index ↗</a>`:''}
 ${factRows?`<div class="table-wrap facts-table" tabindex="0" role="region" aria-label="Source facts; scroll for additional observations"><table><caption class="sr-only">${escapeHTML(r.ticker)} source facts</caption><thead><tr><th>Fact / SEC tag</th><th>Reported value</th><th>Measurement / filing dates</th></tr></thead><tbody>${factRows}</tbody></table></div>`:'<p>No financial values have been substituted for missing observations.</p>'}
 ${source?`<details class="source-fingerprint"><summary>Input provenance</summary><dl><dt>Retrieved (UTC)</dt><dd>${escapeHTML(source.retrieved_at)}</dd><dt>SHA-256 of SEC response</dt><dd>${escapeHTML(source.sha256)}</dd><dt>Source</dt><dd>${escapeHTML(source.url)}</dd><dt>Archived input</dt><dd>${escapeHTML(source.raw_path||'Not archived in this refresh')}</dd></dl></details>`:''}
 <p class="detail-note">CompanyFacts is a current database. A filing-date cutoff does not recreate a historical database vintage. No predictive or market-pricing conclusion is implied.</p>`;
 $('company-detail').showModal();$('close-detail').focus();
}
async function loadData(){
 try {
 const resp=await fetch('./data/research.json',{cache:'no-store'});if(!resp.ok)throw Error('HTTP '+resp.status);
 const data=await resp.json();if(!Array.isArray(data.companies))throw Error('Invalid dataset');
 records=data.companies.filter(r=>r&&typeof r.ticker==='string');
 $('tracked-count').textContent=records.length;
 const n=records.filter(r=>Object.keys(r.facts||{}).length).length;
 const stale=records.filter(r=>r.observation_status==='stale-previous-snapshot').length;
 $('facts-count').textContent=n;
 $('refresh-date').textContent=data.last_successful_refresh?data.last_successful_refresh.slice(0,10)+' UTC':'Not yet run';
 $('table-status').textContent=n?`${n} of ${records.length} companies with annual SEC tags · ${stale} stale · unreviewed`:'Awaiting initial SEC data refresh';
 $('data-cutoff').textContent=data.asof_cutoff?`Filing-date cutoff: ${data.asof_cutoff}. Annual statements only; this is a current coverage pilot, not a Russell 2000 sample.`:'Eight-company coverage pilot. Financial observations will appear after the first successful SEC refresh.';
 const warnings=data.refresh_warnings||[];$('data-warning').hidden=!warnings.length;
 $('data-warning').textContent=warnings.length?`${warnings.length} company refresh issue(s). Stale or missing rows are labeled; open a company for details.`:'';
 updateTable();
 } catch(err){
 $('table-status').textContent='Dataset unavailable';
 $('company-rows').innerHTML='<tr><td colspan="7">The observation panel could not be loaded. Please reload the page.</td></tr>';
 $('data-warning').hidden=false;$('data-warning').textContent='Financial data is unavailable. No results have been substituted.';
 }
}
renderStatic();['growth','margin','cost','capex','dilution'].forEach(id=>$(id).addEventListener('input',updateSimulator));
$('reset-sim').addEventListener('click',()=>{Object.entries({growth:10,margin:16,cost:8,capex:9,dilution:3}).forEach(([id,v])=>$(id).value=v);updateSimulator();});
$('search-company').addEventListener('input',updateTable);$('filter-status').addEventListener('change',updateTable);
$('company-rows').addEventListener('click',event=>{const button=event.target.closest('[data-company]');if(button)showCompany(button.dataset.company);});
$('close-detail').addEventListener('click',()=>$('company-detail').close());
$('company-detail').addEventListener('click',event=>{if(event.target===$('company-detail')){const rect=$('company-detail').getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)$('company-detail').close();}});
function toggleMenu(open){$('mobile-menu').setAttribute('aria-expanded',String(open));$('mobile-menu').setAttribute('aria-label',open?'Close navigation':'Open navigation');document.querySelector('.nav').classList.toggle('open',open);}
$('mobile-menu').addEventListener('click',()=>toggleMenu($('mobile-menu').getAttribute('aria-expanded')!=='true'));
document.querySelectorAll('.nav a').forEach(a=>a.addEventListener('click',()=>toggleMenu(false)));
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&$('mobile-menu').getAttribute('aria-expanded')==='true'){toggleMenu(false);$('mobile-menu').focus();}});
updateSimulator();loadData();

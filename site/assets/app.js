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
  const base=Math.max(Math.abs(x.cashBeforeReinvestment),Math.abs(x.investment),1);
  const left=50*x.cashBeforeReinvestment/base; const right=50*x.investment/base;
  const displayBase=Math.max(0,Math.min(100,50+left));
  const displayCost=Math.max(0,Math.min(100,Math.abs(right)));
  $('cash-bar').innerHTML=`<span class="base" style="width:${displayBase}%" title="Cash before reinvestment: ${fmtM(x.cashBeforeReinvestment)}"></span><span class="cost" style="width:${displayCost}%" title="Reinvestment: ${fmtM(x.investment)}"></span>`;
}
function asNumber(x){return typeof x==='number' && Number.isFinite(x)?x:null;}
function escapeHTML(s){return String(s??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
let records=[];
function row(r){
 const f=r.facts||{}; const revenue=asNumber(f.revenue?.value); const margin=asNumber(r.metrics?.operating_margin);const fcf=asNumber(r.metrics?.free_cash_flow);const ratio=asNumber(r.metrics?.debt_to_assets);
 const money=x=> x===null?'—':('$'+(x/1e6).toLocaleString('en-US',{maximumFractionDigits:1})+'M');
 const link=r.primary_filing_url?`<a class="filing-link" href="${escapeHTML(r.primary_filing_url)}" rel="noopener noreferrer" target="_blank">SEC ↗</a>`:'<span class="pending">Pending</span>';
 return `<tr><td><span class="company-name">${escapeHTML(r.name||r.ticker)}</span><span class="ticker">${escapeHTML(r.ticker)} · ${escapeHTML(r.group||'Other')}</span></td><td>${escapeHTML(r.fiscal_year||'—')}</td><td>${money(revenue)}</td><td>${margin===null?'—':pct(margin)}</td><td>${money(fcf)}</td><td>${ratio===null?'—':pct(ratio)}</td><td>${link}</td></tr>`;
}
function updateTable(){
 const q=$('search-company').value.toLowerCase().trim();const filter=$('filter-status').value;
 const filtered=records.filter(r=>{
  const match=(r.name+' '+r.ticker).toLowerCase().includes(q);
  const available=Boolean(r.primary_filing_url);
  return match&&(filter==='all'||(filter==='available'&&available)||(filter==='pending'&&!available));
 });
 $('company-rows').innerHTML=filtered.length?filtered.map(row).join(''):'<tr><td colspan="7">No matching observations.</td></tr>';
}
async function loadData(){
 try {
 const resp=await fetch('./data/research.json',{cache:'no-store'});if(!resp.ok)throw Error('HTTP '+resp.status);
 const data=await resp.json();records=(data.companies||[]).filter(r=>typeof r.ticker==='string');
 $('tracked-count').textContent=records.length;
 const n=records.filter(r=>r.primary_filing_url).length;
 $('facts-count').textContent=n;
 $('refresh-date').textContent=data.last_successful_refresh?data.last_successful_refresh.slice(0,10):'Not yet run';
 $('table-status').textContent=n?`Regulatory filings loaded for ${n} / ${records.length} monitored companies`:'Awaiting initial SEC data refresh';
 updateTable();
 } catch(err){
 $('table-status').textContent='Dataset unavailable — use a local HTTP server or view published site';
 $('company-rows').innerHTML='<tr><td colspan="7">Unable to fetch local dataset. See README for local preview instructions.</td></tr>';
 }
}
renderStatic();['growth','margin','cost','capex','dilution'].forEach(id=>$(id).addEventListener('input',updateSimulator));
$('reset-sim').addEventListener('click',()=>{Object.entries({growth:10,margin:16,cost:8,capex:9,dilution:3}).forEach(([id,v])=>$(id).value=v);updateSimulator();});
$('search-company').addEventListener('input',updateTable);$('filter-status').addEventListener('change',updateTable);
$('mobile-menu').addEventListener('click',()=>{const open=$('mobile-menu').getAttribute('aria-expanded')!=='true';$('mobile-menu').setAttribute('aria-expanded',String(open));document.querySelector('.nav').classList.toggle('open',open);});
document.querySelectorAll('.nav a').forEach(a=>a.addEventListener('click',()=>{document.querySelector('.nav').classList.remove('open');$('mobile-menu').setAttribute('aria-expanded','false');}));
updateSimulator();loadData();

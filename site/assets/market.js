"use strict";
// Licensed display embeds stay separate from the archived research dataset
function marketSymbol(row){
 if(!row)return 'AMEX:IWM';
 const ticker=String(row.ticker||'').toUpperCase();
 if(!/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(ticker))return null;
 const exchange=String(row.exchange||'').toUpperCase();
 const venue=exchange.includes('NASDAQ')?'NASDAQ':exchange.includes('ARCA')||exchange.includes('NYSE MKT')||exchange.includes('NYSE AMERICAN')?'AMEX':exchange.includes('NEW YORK')||exchange==='NYSE'?'NYSE':null;
 return venue?venue+':'+ticker.replace(/-/g,'.'):null;
}
if(typeof module!=='undefined')module.exports={marketSymbol};
if(typeof document!=='undefined'){
 const marketEl=id=>document.getElementById(id);let pendingRow=null,marketReady=false;
 function embed(id,file,config,title){
  const host=marketEl(id);host.replaceChildren();host.classList.add('tradingview-widget-container');
  const box=document.createElement('div');box.className='tradingview-widget-container__widget';host.append(box);
  const credit=document.createElement('div');credit.className='tradingview-widget-copyright';
  const link=document.createElement('a');link.href='https://www.tradingview.com/symbols/'+config.symbol.replace(':','-')+'/';link.target='_blank';link.rel='noopener noreferrer';link.textContent=title+' by TradingView';credit.append(link);host.append(credit);
  const script=document.createElement('script');script.async=true;script.src='https://s3.tradingview.com/external-embedding/'+file+'.js';script.textContent=JSON.stringify(config);
  script.onerror=()=>{box.textContent='Chart unavailable — use Open full chart above';};
  const labelFrames=()=>host.querySelectorAll('iframe').forEach(frame=>frame.title=title);
  const observer=new MutationObserver(labelFrames);observer.observe(host,{childList:true,subtree:true});
  script.onload=()=>{labelFrames();observer.disconnect();};host.append(script);
 }
 function draw(row){
  const symbol=marketSymbol(row),name=row?row.ticker+' · '+row.name:'IWM · Russell 2000 ETF';marketEl('market-company').textContent=name;
  if(!symbol){['market-quote','market-four-hour','market-daily'].forEach(id=>marketEl(id).textContent='This listing could not be matched to a chart');marketEl('market-link').hidden=true;return;}
  marketEl('market-link').hidden=false;marketEl('market-link').href='https://www.tradingview.com/symbols/'+symbol.replace(':','-')+'/';
  embed('market-quote','embed-widget-symbol-info',{symbol,width:'100%',locale:'en',colorTheme:'light',isTransparent:true},'Latest available quote and company logo');
  const common={autosize:true,symbol,timezone:'America/New_York',theme:'light',style:'1',locale:'en',allow_symbol_change:false,calendar:false,details:false,hide_side_toolbar:true,hide_top_toolbar:true,hide_legend:false,hide_volume:false,save_image:false,withdateranges:true,backgroundColor:'#ffffff',gridColor:'rgba(46,46,46,0.04)',support_host:'https://www.tradingview.com'};
  embed('market-four-hour','embed-widget-advanced-chart',{...common,interval:'240'},'4-hour stock price');
  // Daily bars are deliberate: 200 four-hour bars are not 200 trading days
  embed('market-daily','embed-widget-advanced-chart',{...common,interval:'D',range:'12M',studies:[{id:'STD;SMA',inputs:{in_0:200},overlay:true}]},'Daily stock price and 200-day moving average');
 }
 window.renderMarketCompany=row=>{pendingRow=row;if(marketReady)draw(row);};
 const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){marketReady=true;draw(pendingRow);observer.disconnect();}},{rootMargin:'250px'});
 observer.observe(marketEl('market-quote'));
}

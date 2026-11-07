import {chromium} from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
const out=resolve(process.env.QA_OUTPUT||'evidence/browser');await mkdir(out,{recursive:true});
const root=resolve('docs');
const server=createServer(async(req,res)=>{try{let p=new URL(req.url,'http://localhost').pathname;if(p.endsWith('/'))p+='index.html';const file=resolve(root,'.'+decodeURIComponent(p));if(!file.startsWith(root))throw Error();res.setHeader('Content-Type',({'.html':'text/html','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml'})[extname(file)]||'application/octet-stream');res.end(await readFile(file));}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));const url=process.env.PRODUCT_URL||`http://127.0.0.1:${server.address().port}/`;
const browser=await chromium.launch(),results=[];
const header='id,first_name,course,consent,opt_out\n';
try{for(const [width,height] of [[320,700],[375,812],[390,844],[768,1024],[1024,768],[1440,1000],[1920,1080]]){
 const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce',acceptDownloads:true});const page=await context.newPage(),errors=[],external=[],bad=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('request',r=>{if(new URL(r.url()).origin!==new URL(url).origin)external.push(r.url());});page.on('response',r=>{if(r.status()>=400)bad.push(r.url());});
 await page.goto(url,{waitUntil:'networkidle'});
 assert.equal(await page.locator('h1').textContent(),'Prepare carefully.Send deliberately.');
 assert((await page.locator('h1').evaluate(e=>parseFloat(getComputedStyle(e).fontSize)))<61);
 assert.equal(await page.locator('.hero .cta').getAttribute('href'),'#install');
 const order=await page.evaluate(()=>['android','install','simulator'].map(id=>document.getElementById(id).offsetTop));assert(order[0]<order[1]&&order[1]<order[2]);
 for(const a of await page.locator('a[href^="#"]').all()){const h=await a.getAttribute('href');assert(await page.locator(h).count(),h);}
 await page.keyboard.press('Tab');assert.match(await page.locator(':focus').textContent(),/Skip to main/);await page.keyboard.press('Enter');assert.equal(await page.locator(':focus').getAttribute('id'),'top');
 await page.locator('.hero .cta').focus();assert(await page.locator(':focus').evaluate(e=>getComputedStyle(e).outlineStyle!=='none'));await page.keyboard.press('Enter');await page.waitForTimeout(100);
 assert(await page.locator('#install').evaluate(e=>e.getBoundingClientRect().top<100));
 for(const name of ['macOS · Terminal','Linux · shell']){const summary=page.getByText(name,{exact:true});await summary.focus();await page.keyboard.press('Enter');assert(await summary.evaluate(e=>e.parentElement.open));await page.keyboard.press('Enter');}
 assert(await page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior==='auto'));
 const a=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();await writeFile(`${out}/axe-${width}.json`,JSON.stringify(a,null,2));assert.deepEqual(a.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)})),[]);
 await page.locator('h1').click();await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:`${out}/arrival-${width}.png`,fullPage:true});
 await page.locator('#android').screenshot({path:`${out}/android-${width}.png`});
 await page.locator('#install').screenshot({path:`${out}/install-${width}.png`});
 await page.locator('#run').click();assert.equal(await page.locator('#metric-queued').textContent(),'2');assert.equal(await page.locator('#metric-duplicates').textContent(),'1');assert.equal(await page.locator('#results tr').count(),5);
 await page.locator('#message').fill('{{bad}}');await page.locator('#run').click();assert.match(await page.locator('#errors').textContent(),/Unsupported/);assert.equal(await page.locator('#results tr').count(),0);
 const upload=async text=>{await page.locator('#contacts-file').setInputFiles({name:'fictional.csv',mimeType:'text/csv',buffer:Buffer.from(text)});};
 await page.locator('#message').fill('Hello {{first_name}}');
 for(const rows of [['a,Ari,Web,true,false','a,Other,Web,false,false'],['a,Other,Web,false,false','a,Ari,Web,true,false'],['a,Ari,Web,true,false','a,Other,Web,true,true']]){await upload(header+rows.join('\n'));await page.locator('#process-file').click();assert.equal(await page.locator('#metric-queued').textContent(),'0');assert.equal(await page.locator('#results .preview').allTextContents().then(xs=>xs.every(x=>x==='Not prepared')),true);}
 await upload(header+'formula,=1+1,Web,true,false\nxss,<img src=x onerror=alert(1)>,Web,true,false');await page.locator('#process-file').click();assert.equal(await page.locator('#results img').count(),0);assert((await page.locator('#results').textContent()).includes('<img'));
 const downloadEvent=page.waitForEvent('download');await page.locator('#export-plan').click();const download=await downloadEvent;const csv=await readFile(await download.path(),'utf8');assert(csv.includes("'=1+1"));assert(csv.includes('Hello =1+1'));
 await upload(header.replace(',opt_out',',phone,opt_out')+'a,Ari,Web,true,not-a-number,false');await page.waitForFunction(()=>!document.querySelector('#errors').hidden);assert.match(await page.locator('#errors').textContent(),/phone-number/);assert(await page.locator('#process-file').isDisabled());
 await upload('x'.repeat(1048577));await page.waitForFunction(()=>!document.querySelector('#errors').hidden);assert.match(await page.locator('#errors').textContent(),/1 MiB/);
 await upload(header+Array.from({length:1001},(_,i)=>`id${i},Ari,Web,true,false`).join('\n'));await page.waitForFunction(()=>!document.querySelector('#errors').hidden);assert.match(await page.locator('#errors').textContent(),/1,000/);
 // Finish a deferred file read after Reset: stale data must never repopulate the workspace.
 await page.evaluate(()=>{window.originalFileText=File.prototype.text;File.prototype.text=function(){return new Promise(r=>window.finishImport=()=>r('id,first_name,course,consent,opt_out\na,Ari,Web,true,false'));};});
 await upload(header+'a,Ari,Web,true,false');await page.waitForFunction(()=>!!window.finishImport);await page.locator('#reset').click();await page.evaluate(()=>{window.finishImport();File.prototype.text=window.originalFileText;});await page.waitForTimeout(100);assert(await page.locator('#process-file').isDisabled());assert.equal(await page.locator('#metric-total').textContent(),'—');assert.match(await page.locator('#status').textContent(),/^Ready/);
 await page.locator('#run').click();await page.locator('#simulator').screenshot({path:`${out}/demo-${width}.png`});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert.deepEqual(errors,[]);assert.deepEqual(external,[]);assert.deepEqual(bad,[]);
 results.push({width,height,url,axe:0,productHierarchy:'passed',installationKeyboard:'passed',consentConflicts:'passed',limits:'passed',exportAndLiteralRendering:'passed',resetRace:'passed',externalRequests:external,consoleErrors:errors});await context.close();
}}finally{await writeFile(`${out}/results.json`,JSON.stringify(results,null,2));await browser.close();await new Promise(r=>server.close(r));}
console.log(JSON.stringify(results,null,2));

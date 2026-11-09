// SPDX-License-Identifier: Apache-2.0
// Optional browser regression. Requires Playwright and Chromium; fixture service is owned by test_operator.py.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async()=>{
 const url=process.env.OVERLORD_TEST_URL;
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1200,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  const session=crypto.randomUUID();
  async function post(path,data){const r=await page.request.post(url+path,{data});assert(r.ok(),await r.text());return r.json()}
  await post('/v1/sessions',{session_id:session,mission_name:'Operation First Contact',map_name:'Altis'});
  await page.goto(url+'/operator');
  await page.getByText('Read-only: use the private launch link or enter its credential').waitFor();
  assert(await page.locator('#apply').isDisabled());
  await page.goto(url+'/operator#token=browser-test-operator');
  // The launch link must also authorise an already-open read-only tab, without a reload.
  await page.getByText('Authorised launch operator: approval and mode controls available').waitFor();
  assert(!page.url().includes('token='));
  await page.locator('#selection').selectOption('review');
  await page.locator('#apply').click();
  await page.getByText('Current mode: execution review',{exact:true}).waitFor();
  await new Promise(resolve=>setTimeout(resolve,1100));
  const event={protocol_version:'1.0',session_id:session,event_id:crypto.randomUUID(),timestamp:new Date().toISOString(),event_type:'checkpoint_attacked',payload:{checkpoint_id:'checkpoint_alpha',attacking_side:'BLUFOR',report_channel:'guard_radio',reserve_available:true}};
  await post('/v1/observations',event);
  await page.getByRole('button',{name:'Approve this fresh recommendation'}).click();
  await page.getByText('APPROVED · explicit operator approval of fresh guard report',{exact:true}).waitFor();
  const packet=await post('/v1/commands/poll',{session_id:session,include_report:true});
  assert.equal(packet.length,7);assert(packet[4].length);
  assert.deepEqual((await post('/v1/commands/poll',{session_id:session}))[4],packet[4]);
  await post('/v1/acknowledgements',{protocol_version:'1.0',session_id:session,command_id:packet[4][0],idempotency_key:packet[4][1],status:'executed',result:'movement_order_assigned'});
  for(const milestone of ['briefing_complete','recon_reported','extracted'])await post('/v1/observations',{...event,event_id:crypto.randomUUID(),event_type:'operation_progress',payload:{milestone}});
  await page.getByText('Operation: succeeded · Outcome: succeeded',{exact:true}).waitFor();
  await page.getByText('Arma result: executed / movement_order_assigned',{exact:true}).waitFor();
  await page.locator('#pause').click();await page.getByText('Current mode: execution review · PAUSED',{exact:true}).waitFor();
  await page.screenshot({path:process.env.OVERLORD_TEST_SCREENSHOT||'/tmp/overlord-operator.png',fullPage:true});
  await page.route('**/v1/**',route=>route.abort());
  await page.getByText('Director unavailable. Essential mission progression remains local; this panel may be stale.',{exact:true}).waitFor();
  assert.deepEqual(errors,[]);
  console.log('Browser: read-only/authenticated modes, review approval, repeated command, synthetic ack, debrief, pause and unavailable status passed.');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});

// Bộ điều khiển Chrome headless qua CDP, thao tác bằng chuột/phím thật.
import {spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import fs from 'node:fs';
export const sleep = ms => new Promise(r => setTimeout(r, ms));
export async function open(htmlPath, outDir, profile, {port = 9361, w = 1280, h = 800, mobile = false, dark = false} = {}) {
  const url = pathToFileURL(htmlPath).href;
  const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run', '--disable-extensions', '--hide-scrollbars', `--window-size=${w},${h}`, 'about:blank'], {stdio: 'ignore'});
  let target;
  for (let i = 0; i < 60; i++) { try { const l = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); target = l.find(t => t.type === 'page'); if (target) break; } catch (e) {} await sleep(250); }
  if (!target) { chrome.kill(); throw new Error('no chrome'); }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r));
  let id = 0; const pend = new Map(); const listeners = [];
  ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result || m); pend.delete(m.id); } else if (m.method) listeners.forEach(f => f(m)); });
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({id: i, method, params})); });
  const S = {};
  S.send = send;
  S.ev = async expr => { const r = await send('Runtime.evaluate', {expression: expr, returnByValue: true, awaitPromise: true}); if (r.exceptionDetails) return {__err: r.exceptionDetails.exception && r.exceptionDetails.exception.description}; return r.result ? r.result.value : r; };
  await send('Page.enable'); await send('Runtime.enable');
  const errs = []; listeners.push(m => { if (m.method === 'Runtime.exceptionThrown') errs.push(m.params.exceptionDetails.exception ? m.params.exceptionDetails.exception.description : m.params.exceptionDetails.text); });
  S.errs = errs;
  await send('Emulation.setDeviceMetricsOverride', {width: w, height: h, deviceScaleFactor: mobile ? 2 : 1, mobile});
  if (mobile) await send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 5});
  await send('Emulation.setEmulatedMedia', {features: [{name: 'prefers-color-scheme', value: dark ? 'dark' : 'light'}]});
  S.load = async (u = url) => { await send('Page.navigate', {url: u}); await sleep(1000); };
  S.shot = async (name, full = false) => { const p = {format: 'jpeg', quality: 76}; if (full) { const m = await send('Page.getLayoutMetrics'); p.clip = {x: 0, y: 0, width: w, height: Math.min(m.cssContentSize.height, 6000), scale: 1}; p.captureBeyondViewport = true; } const r = await send('Page.captureScreenshot', p); fs.writeFileSync(`${outDir}/${name}.jpg`, Buffer.from(r.data, 'base64')); return name; };
  S.box = async sel => S.ev(`(function(){var e=${sel.js ? sel.js : `document.querySelector(${JSON.stringify(sel)})`};if(!e)return null;e.scrollIntoView({block:'center',inline:'center'});var r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2,l:r.left,t:r.top,w:r.width,h:r.height}})()`);
  S.mouse = (type, x, y, extra = {}) => send('Input.dispatchMouseEvent', Object.assign({type, x, y, button: 'left', clickCount: 1}, extra));
  S.click = async (sel, dx = 0, dy = 0) => { const b = await S.box(sel); if (!b) throw new Error('no element ' + sel); await sleep(80); await S.mouse('mouseMoved', b.x + dx, b.y + dy, {button: 'none'}); await S.mouse('mousePressed', b.x + dx, b.y + dy); await S.mouse('mouseReleased', b.x + dx, b.y + dy); await sleep(350); return b; };
  const KEYS = {Enter: [13, 'Enter', '\r'], Escape: [27, 'Escape', ''], ArrowDown: [40, 'ArrowDown', ''], ArrowUp: [38, 'ArrowUp', ''], ArrowLeft: [37, 'ArrowLeft', ''], ArrowRight: [39, 'ArrowRight', ''], Tab: [9, 'Tab', ''], Backspace: [8, 'Backspace', '']};
  S.key = async (k, mods = 0) => {
    let code, key, text;
    if (KEYS[k]) [code, key, text] = KEYS[k];
    else { key = k; text = k; code = k === ' ' ? 32 : k === '/' ? 191 : k === '?' ? 191 : k === '`' ? 192 : k.toUpperCase().charCodeAt(0); }
    const shift = k === '?' ? 8 : 0;
    await send('Input.dispatchKeyEvent', {type: text && !mods ? 'keyDown' : 'rawKeyDown', key, windowsVirtualKeyCode: code, text: mods ? undefined : text, unmodifiedText: text, modifiers: mods | shift});
    await send('Input.dispatchKeyEvent', {type: 'keyUp', key, windowsVirtualKeyCode: code, modifiers: mods | shift});
    await sleep(300);
  };
  S.type = async t => { await send('Input.insertText', {text: t}); await sleep(200); };
  // kéo thả HTML5 thật: chặn drag của trình duyệt rồi phát dragEnter/dragOver/drop
  S.drag = async (from, to, {dx = 0, dy = 0} = {}) => {
    const a = await S.box(from); if (!a) throw new Error('no drag source ' + from);
    await send('Input.setInterceptDrags', {enabled: true});
    let data = null; const on = m => { if (m.method === 'Input.dragIntercepted') data = m.params.data; }; listeners.push(on);
    await S.mouse('mouseMoved', a.x, a.y, {button: 'none'}); await S.mouse('mousePressed', a.x, a.y);
    for (let i = 1; i <= 6 && !data; i++) { await S.mouse('mouseMoved', a.x + i * 4, a.y + i * 4, {buttons: 1}); await sleep(60); }
    listeners.splice(listeners.indexOf(on), 1);
    if (!data) { await S.mouse('mouseReleased', a.x, a.y); await send('Input.setInterceptDrags', {enabled: false}); throw new Error('drag not started'); }
    await sleep(100);
    const b = typeof to === 'object' ? to : await S.ev(`(function(){var e=document.querySelector(${JSON.stringify(to)});if(!e)return null;var r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2,t:r.top,h:r.height}})()`);
    if (!b) throw new Error('no drop target ' + to);
    const x = b.x + dx, y = b.y + dy;
    await send('Input.dispatchDragEvent', {type: 'dragEnter', x, y, data});
    for (let i = 0; i < 3; i++) { await send('Input.dispatchDragEvent', {type: 'dragOver', x, y: y + i, data}); await sleep(80); }
    await send('Input.dispatchDragEvent', {type: 'drop', x, y: y + 2, data});
    await S.mouse('mouseReleased', x, y + 2);
    await send('Input.setInterceptDrags', {enabled: false});
    await sleep(500);
  };
  S.close = () => { try { ws.close(); } catch (e) {} chrome.kill(); };
  return S;
}

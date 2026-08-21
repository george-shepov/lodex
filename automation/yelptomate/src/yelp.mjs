import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { artifactDir } from './engines.mjs';

export const YELP_BUSINESS_URL = 'https://biz.yelp.com/';

const DISCOVER_SCRIPT = `(() => {
  const visible = (el) => {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  };
  const compact = (el) => ({
    tag: el.tagName,
    text: (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 500),
    href: el.getAttribute('href'),
    role: el.getAttribute('role'),
    ariaLabel: el.getAttribute('aria-label'),
    placeholder: el.getAttribute('placeholder'),
    type: el.getAttribute('type'),
    name: el.getAttribute('name'),
    testId: el.getAttribute('data-testid')
  });
  const selector = 'a,button,textarea,input,[contenteditable="true"],[role="button"],[role="link"],[data-testid]';
  return [...document.querySelectorAll(selector)].filter(visible).slice(0, 1000).map(compact);
})()`;

const CANDIDATE_THREADS_SCRIPT = `(() => {
  const visible = (el) => {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  };
  const anchors = [...document.querySelectorAll('a[href]')].filter(visible);
  const candidates = anchors
    .filter(a => /message|inbox|lead|quote|conversation/i.test(a.getAttribute('href') || ''))
    .map(a => ({
      href: a.href,
      text: (a.innerText || a.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 1000)
    }))
    .filter(x => x.text);
  const unique = [];
  const seen = new Set();
  for (const item of candidates) {
    const key = item.href + '|' + item.text;
    if (!seen.has(key)) { seen.add(key); unique.push(item); }
  }
  return unique.slice(0, 300);
})()`;

const BODY_TEXT_SCRIPT = `(() => (document.body?.innerText || '').slice(0, 30000))()`;

function stamp() {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

async function pressEnter(message) {
  if (!process.stdin.isTTY) return;
  const rl = readline.createInterface({ input, output });
  await rl.question(`${message}\nPress Enter to continue... `);
  rl.close();
}

async function looksLoggedIn(engine) {
  const url = (await engine.url()).toLowerCase();
  const body = String(await engine.evaluate(BODY_TEXT_SCRIPT)).toLowerCase();
  if (/login|sign.?in/.test(url) && /password/.test(body)) return false;
  return /inbox|messages|leads|business information|yelp ads/i.test(body) || !/login|sign.?in/.test(url);
}

export async function ensureBusinessSession(engine) {
  await engine.goto(YELP_BUSINESS_URL);
  await engine.wait(1500);
  if (await looksLoggedIn(engine)) return;

  console.log(`\n[${engine.name}] Yelp login is required in the browser window.`);
  console.log('Log into the LODEX Yelp for Business account manually. The browser profile is persisted locally, so this should normally be one-time per engine.');
  await pressEnter('Finish the Yelp login in the browser.');
  await engine.wait(1000);

  if (!(await looksLoggedIn(engine))) {
    throw new Error('Yelp still appears to be on a login screen. Complete login and run again.');
  }
}

export async function openInbox(engine) {
  await ensureBusinessSession(engine);

  const clicked = await engine.clickText('Inbox');
  if (clicked?.ok) {
    await engine.wait(1500);
    return;
  }

  const url = await engine.url();
  if (!/inbox|message/i.test(url)) {
    console.warn('[yelptomate] Could not find a visible Inbox control automatically. Staying on the current Yelp for Business page for discovery.');
  }
}

export async function discover(engine) {
  await openInbox(engine);
  const dir = artifactDir();
  const id = stamp();
  const screenshot = path.join(dir, `${id}-${engine.name}-discover.png`);
  const jsonFile = path.join(dir, `${id}-${engine.name}-discover.json`);

  const payload = {
    capturedAt: new Date().toISOString(),
    engine: engine.name,
    url: await engine.url(),
    title: await engine.title(),
    elements: await engine.evaluate(DISCOVER_SCRIPT),
    candidateThreads: await engine.evaluate(CANDIDATE_THREADS_SCRIPT),
    bodyText: await engine.evaluate(BODY_TEXT_SCRIPT)
  };

  await engine.screenshot(screenshot);
  fs.writeFileSync(jsonFile, JSON.stringify(payload, null, 2));
  return { screenshot, jsonFile, payload };
}

export async function listInbox(engine) {
  await openInbox(engine);
  return {
    url: await engine.url(),
    title: await engine.title(),
    candidates: await engine.evaluate(CANDIDATE_THREADS_SCRIPT),
    bodyText: await engine.evaluate(BODY_TEXT_SCRIPT)
  };
}

export async function openLead(engine, leadName) {
  await openInbox(engine);
  const click = await engine.clickText(leadName);
  if (!click?.ok) {
    throw new Error(`Could not locate a visible Yelp thread containing: ${leadName}`);
  }
  await engine.wait(1000);
  return { url: await engine.url(), title: await engine.title() };
}

export async function replyToLead(engine, { leadName, text, send = false }) {
  await openLead(engine, leadName);

  const composer = await engine.setComposerText(text);
  if (!composer?.ok) {
    throw new Error('Found the lead thread, but could not locate the reply composer. Run discover so we can inspect the current Yelp DOM.');
  }

  const dir = artifactDir();
  const id = stamp();
  const preview = path.join(dir, `${id}-${engine.name}-reply-preview.png`);
  await engine.screenshot(preview);

  if (!send) {
    return {
      sent: false,
      dryRun: true,
      preview,
      message: 'Composer was filled, but Send was not clicked. Re-run with --send after validating the thread and text.'
    };
  }

  const clicked = await engine.clickSend();
  if (!clicked?.ok) {
    throw new Error('Reply text was filled, but no Send control was found. Nothing was sent.');
  }

  await engine.wait(1000);
  const receipt = path.join(dir, `${id}-${engine.name}-reply-sent.png`);
  await engine.screenshot(receipt);
  return { sent: true, dryRun: false, receipt };
}

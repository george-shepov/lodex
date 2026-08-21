import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function profileDir(engineName) {
  return ensureDir(path.join(ROOT, 'profiles', engineName));
}

export function artifactDir() {
  return ensureDir(path.join(ROOT, 'artifacts'));
}

const DOM_CLICK_TEXT = (text) => `(() => {
  const needle = ${JSON.stringify(text)}.trim().toLowerCase();
  const visible = (el) => {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  };
  const nodes = [...document.querySelectorAll('a,button,[role="button"],[tabindex]')];
  const match = nodes.find(el => visible(el) && (el.innerText || el.textContent || '').trim().toLowerCase().includes(needle));
  if (!match) return { ok: false, reason: 'not-found', text: ${JSON.stringify(text)} };
  match.scrollIntoView({ block: 'center' });
  match.click();
  return { ok: true, tag: match.tagName, text: (match.innerText || match.textContent || '').trim().slice(0, 200) };
})()`;

const DOM_SET_COMPOSER = (text) => `(() => {
  const visible = (el) => {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  };
  const candidates = [...document.querySelectorAll('textarea,[contenteditable="true"],input[type="text"]')].filter(visible);
  const el = candidates.find(x => /response|reply|message|write/i.test(x.getAttribute('placeholder') || x.getAttribute('aria-label') || '')) || candidates[candidates.length - 1];
  if (!el) return { ok: false, reason: 'composer-not-found' };
  el.focus();
  const value = ${JSON.stringify(text)};
  if (el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
    if (setter) setter.call(el, value); else el.value = value;
  } else {
    el.textContent = value;
  }
  el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  return { ok: true, tag: el.tagName, placeholder: el.getAttribute('placeholder') || '', ariaLabel: el.getAttribute('aria-label') || '' };
})()`;

const DOM_CLICK_SEND = `(() => {
  const visible = (el) => {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  };
  const buttons = [...document.querySelectorAll('button,[role="button"],input[type="submit"]')].filter(visible);
  const exact = buttons.find(el => /^send$/i.test((el.innerText || el.value || el.getAttribute('aria-label') || '').trim()));
  const fuzzy = buttons.find(el => /send/i.test((el.innerText || el.value || el.getAttribute('aria-label') || '').trim()));
  const btn = exact || fuzzy;
  if (!btn) return { ok: false, reason: 'send-not-found' };
  btn.scrollIntoView({ block: 'center' });
  btn.click();
  return { ok: true, text: (btn.innerText || btn.value || btn.getAttribute('aria-label') || '').trim() };
})()`;

class CommonEngine {
  constructor(name) {
    this.name = name;
  }

  async clickText(text) {
    return this.evaluate(DOM_CLICK_TEXT(text));
  }

  async setComposerText(text) {
    return this.evaluate(DOM_SET_COMPOSER(text));
  }

  async clickSend() {
    return this.evaluate(DOM_CLICK_SEND);
  }
}

class PlaywrightEngine extends CommonEngine {
  constructor(context, page) {
    super('playwright');
    this.context = context;
    this.page = page;
  }

  static async launch({ headless = false } = {}) {
    const { chromium } = await import('playwright');
    const context = await chromium.launchPersistentContext(profileDir('playwright'), {
      headless,
      viewport: { width: 1440, height: 1000 },
      args: ['--disable-notifications']
    });
    const pages = context.pages();
    const page = pages[0] || await context.newPage();
    return new PlaywrightEngine(context, page);
  }

  async goto(url) { await this.page.goto(url, { waitUntil: 'domcontentloaded' }); }
  async url() { return this.page.url(); }
  async title() { return this.page.title(); }
  async wait(ms) { await this.page.waitForTimeout(ms); }
  async evaluate(source) { return this.page.evaluate((s) => globalThis.eval(s), source); }
  async screenshot(file) { await this.page.screenshot({ path: file, fullPage: true }); }
  async close() { await this.context.close(); }
}

class PuppeteerEngine extends CommonEngine {
  constructor(browser, page) {
    super('puppeteer');
    this.browser = browser;
    this.page = page;
  }

  static async launch({ headless = false } = {}) {
    const puppeteer = (await import('puppeteer')).default;
    const browser = await puppeteer.launch({
      headless,
      userDataDir: profileDir('puppeteer'),
      defaultViewport: { width: 1440, height: 1000 },
      args: ['--disable-notifications']
    });
    const pages = await browser.pages();
    const page = pages[0] || await browser.newPage();
    return new PuppeteerEngine(browser, page);
  }

  async goto(url) { await this.page.goto(url, { waitUntil: 'domcontentloaded' }); }
  async url() { return this.page.url(); }
  async title() { return this.page.title(); }
  async wait(ms) { await new Promise(resolve => setTimeout(resolve, ms)); }
  async evaluate(source) { return this.page.evaluate((s) => globalThis.eval(s), source); }
  async screenshot(file) { await this.page.screenshot({ path: file, fullPage: true }); }
  async close() { await this.browser.close(); }
}

class SeleniumEngine extends CommonEngine {
  constructor(driver) {
    super('selenium');
    this.driver = driver;
  }

  static async launch({ headless = false } = {}) {
    const { Builder } = await import('selenium-webdriver');
    const chrome = await import('selenium-webdriver/chrome.js');
    const options = new chrome.Options();
    options.addArguments(`--user-data-dir=${profileDir('selenium')}`);
    options.addArguments('--disable-notifications');
    options.addArguments('--window-size=1440,1000');
    if (headless) options.addArguments('--headless=new');
    const driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
    return new SeleniumEngine(driver);
  }

  async goto(url) { await this.driver.get(url); }
  async url() { return this.driver.getCurrentUrl(); }
  async title() { return this.driver.getTitle(); }
  async wait(ms) { await this.driver.sleep(ms); }
  async evaluate(source) { return this.driver.executeScript(`return ${source};`); }
  async screenshot(file) {
    const png = await this.driver.takeScreenshot();
    fs.writeFileSync(file, png, 'base64');
  }
  async close() { await this.driver.quit(); }
}

export async function launchEngine(name = 'playwright', options = {}) {
  const normalized = String(name).toLowerCase();
  if (normalized === 'playwright' || normalized === 'pw') return PlaywrightEngine.launch(options);
  if (normalized === 'puppeteer' || normalized === 'pptr') return PuppeteerEngine.launch(options);
  if (normalized === 'selenium' || normalized === 'sel') return SeleniumEngine.launch(options);
  throw new Error(`Unknown browser engine: ${name}. Use playwright, puppeteer, or selenium.`);
}

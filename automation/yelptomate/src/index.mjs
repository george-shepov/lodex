#!/usr/bin/env node
import { launchEngine } from './engines.mjs';
import { discover, listInbox, replyToLead } from './yelp.mjs';

function parseArgs(argv) {
  const positional = [];
  const flags = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) {
      positional.push(token);
      continue;
    }
    const [rawKey, inline] = token.slice(2).split('=', 2);
    if (inline !== undefined) {
      flags[rawKey] = inline;
      continue;
    }
    const next = argv[i + 1];
    if (next && !next.startsWith('--')) {
      flags[rawKey] = next;
      i += 1;
    } else {
      flags[rawKey] = true;
    }
  }
  return { positional, flags };
}

function required(flags, name) {
  const value = flags[name];
  if (!value || value === true) throw new Error(`Missing required --${name}`);
  return String(value);
}

function usage() {
  console.log(`Yelptomate - LODEX Yelp for Business browser automation\n\nUsage:\n  node src/index.mjs discover [--engine playwright|puppeteer|selenium]\n  node src/index.mjs inbox [--engine playwright|puppeteer|selenium]\n  node src/index.mjs reply --lead "Elizabeth Knight" --text "..." [--send] [--engine playwright]\n\nSafety:\n  reply is DRY-RUN by default. It fills the composer and saves a screenshot, but does not click Send unless --send is supplied.\n\nExamples:\n  npm run discover -- --engine playwright\n  npm run discover -- --engine selenium\n  npm run inbox -- --engine puppeteer\n  npm run reply -- --lead "Elizabeth Knight" --text "Hi Elizabeth..."\n  npm run reply -- --lead "Elizabeth Knight" --text "Hi Elizabeth..." --send\n`);
}

const { positional, flags } = parseArgs(process.argv.slice(2));
const command = positional[0] || 'discover';
const engineName = String(flags.engine || process.env.YELP_ENGINE || 'playwright');
const headless = flags.headless === true || String(process.env.YELP_HEADLESS || '').toLowerCase() === 'true';

if (flags.help || flags.h) {
  usage();
  process.exit(0);
}

let engine;
try {
  engine = await launchEngine(engineName, { headless });

  if (command === 'discover') {
    const result = await discover(engine);
    console.log(JSON.stringify({
      engine: engine.name,
      url: result.payload.url,
      title: result.payload.title,
      candidateThreadCount: result.payload.candidateThreads.length,
      screenshot: result.screenshot,
      jsonFile: result.jsonFile
    }, null, 2));
  } else if (command === 'inbox') {
    const result = await listInbox(engine);
    console.log(JSON.stringify(result, null, 2));
  } else if (command === 'reply') {
    const result = await replyToLead(engine, {
      leadName: required(flags, 'lead'),
      text: required(flags, 'text'),
      send: flags.send === true || String(flags.send).toLowerCase() === 'true'
    });
    console.log(JSON.stringify(result, null, 2));
  } else {
    usage();
    throw new Error(`Unknown command: ${command}`);
  }
} catch (error) {
  console.error(`\n[yelptomate] ${error?.stack || error}`);
  process.exitCode = 1;
} finally {
  if (engine) await engine.close().catch(() => {});
}

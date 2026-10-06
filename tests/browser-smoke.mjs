/** Browser integration test using isolated local services and temporary SQLite state. */
import { chromium } from '../frontend/crew_dashboard/node_modules/playwright/index.mjs';
import { spawn } from 'node:child_process';
import { mkdtemp, rm, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import assert from 'node:assert/strict';

const root = resolve(new URL('..', import.meta.url).pathname);
const temporary = await mkdtemp(join(tmpdir(), 'cabinops-browser-'));
const env = { ...process.env, ENV: 'development', CABINOPS_DB_PATH: join(temporary, 'test.db'), VITE_BACKEND_PORT: '8010', CREW_USERNAME: 'crew', CREW_PASSWORD: 'crew_password' };
const processes = [];
let browser;
function launch(command, args, cwd = root) {
  const child = spawn(command, args, { cwd, env, stdio: 'inherit' });
  processes.push(child);
  return child;
}
async function ready(url) {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (processes.some(child => child.exitCode !== null)) throw new Error('A test service exited early');
    try { if ((await fetch(url)).ok) return; } catch {}
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error(`Service unavailable: ${url}`);
}
try {
  launch(process.env.PYTHON || 'python', ['-m', 'uvicorn', 'backend.main:app', '--port', '8010']);
  for (const [portal, port] of [['passenger_screen', '5183'], ['crew_dashboard', '5184']]) {
    launch(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', port, '--strictPort'], join(root, 'frontend', portal));
  }
  await Promise.all(['http://127.0.0.1:8010/health', 'http://127.0.0.1:5183', 'http://127.0.0.1:5184'].map(ready));
  browser = await chromium.launch({ headless: true });
  const passenger = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const crew = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  for (const page of [passenger, crew]) page.on('pageerror', error => errors.push(error.message));
  await passenger.goto('http://127.0.0.1:5183');
  await passenger.locator('#seat-input').fill('22A');
  await passenger.locator('#booking-ref-input').fill('DEMO');
  await passenger.locator('button[type=submit]').click();
  await passenger.getByRole('textbox', { name: 'Your service request' }).waitFor();
  await crew.goto('http://127.0.0.1:5184');
  await crew.locator('#cc-username').fill('crew');
  await crew.locator('#cc-password').fill('crew_password');
  await crew.getByRole('button', { name: 'Sign In', exact: true }).click();
  await crew.getByRole('heading', { name: 'Passenger Duty Queue' }).waitFor();
  await passenger.getByRole('textbox', { name: 'Your service request' }).fill('I feel dizzy. Please help.');
  await passenger.getByRole('button', { name: 'Send request', exact: true }).click();
  await crew.getByRole('button', { name: 'Fulfill Request', exact: true }).click();
  await crew.getByRole('button', { name: 'Mark Complete', exact: true }).click();
  await passenger.locator('.status-badge--completed').waitFor();
  assert.equal(await passenger.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, 'Passenger mobile layout overflows');
  await crew.setViewportSize({ width: 390, height: 844 });
  assert.equal(await crew.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, 'Crew mobile layout overflows');
  await crew.setViewportSize({ width: 1440, height: 1000 });
  await crew.locator('.broadcast-textarea').fill('CabinOps browser test announcement');
  await crew.getByRole('button', { name: 'Broadcast to Cabin' }).click();
  await passenger.getByText('CabinOps browser test announcement', { exact: true }).waitFor();
  // Failed operations must remain visible and preserve the announcement draft.
  await crew.route('**/api/announcements', route => route.request().method() === 'POST' ? route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"Test write failed"}' }) : route.continue());
  await crew.locator('.broadcast-textarea').fill('Keep this draft');
  await crew.getByRole('button', { name: 'Broadcast to Cabin' }).click();
  await crew.getByRole('alert').waitFor();
  assert.equal(await crew.locator('.broadcast-textarea').inputValue(), 'Keep this draft');
  assert.deepEqual(errors, []);
  await mkdir(join(root, 'test-results'), { recursive: true });
  await passenger.screenshot({ path: join(root, 'test-results/passenger.png'), fullPage: true });
  await crew.screenshot({ path: join(root, 'test-results/crew.png'), fullPage: true });
  console.log('Browser smoke passed: login, request, crew completion, live announcements, failed writes, and mobile layouts.');
} finally {
  await browser?.close();
  for (const child of processes) child.kill('SIGTERM');
  await rm(temporary, { recursive: true, force: true });
}

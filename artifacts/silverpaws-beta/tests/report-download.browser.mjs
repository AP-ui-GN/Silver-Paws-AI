import { execFile, spawn } from 'node:child_process';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { promisify } from 'node:util';
import { createServer } from 'node:net';

const execFileAsync = promisify(execFile);
const appRoot = resolve(import.meta.dirname, '..');
const appOrigin = 'http://127.0.0.1:4173';
const chromiumPath = process.env.CHROMIUM_PATH ?? '/repl/tools/bin/chromium';

const pet = {
  id: 'pet-report-test',
  name: 'Mabel',
  species: 'Dog',
  breed: 'Spaniel',
  age: '7',
  weight: '9.4',
  notes: '',
  createdAt: '2026-09-01T12:00:00.000Z',
};

const completeAnalysis = {
  id: 'analysis-report-complete',
  petId: pet.id,
  fileName: 'mabel-garden-walk.mp4',
  durationSeconds: 18,
  createdAt: '2026-09-10T12:00:00.000Z',
  status: 'complete',
  strideSymmetryScore: 86,
  asymmetryPercent: 7,
  confidence: 78,
  observation: 'Mabel’s stride looked broadly even in this clip.',
  limitations: 'This is an educational observation from one camera angle. It is not a diagnosis.',
  source: 'Test video library',
  license: 'CC BY 4.0',
  sourceUrl: 'https://example.com/test-video',
};

const missingOptionalAnalysis = {
  id: 'analysis-report-fallbacks',
  petId: pet.id,
  fileName: 'mabel-living-room.mp4',
  durationSeconds: 9,
  createdAt: '2026-09-11T12:00:00.000Z',
  status: 'complete',
  observation: 'No clear difference was saved for this clip.',
};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function getFreePort() {
  const server = createServer();
  await new Promise((resolvePromise, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolvePromise);
  });
  const { port } = server.address();
  await new Promise((resolvePromise) => server.close(resolvePromise));
  return port;
}

async function waitForHttp(url, timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The dev server is still starting.
    }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 200));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function waitForDebugger(port, timeoutMs = 30_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/list`);
      const targets = await response.json();
      const page = targets.find((target) => target.type === 'page' && target.webSocketDebuggerUrl);
      if (page) return page.webSocketDebuggerUrl;
    } catch {
      // Chromium is still starting.
    }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 200));
  }
  throw new Error('Timed out waiting for Chromium remote debugging');
}

function connectToCdp(webSocketUrl) {
  const socket = new WebSocket(webSocketUrl);
  const pending = new Map();
  let nextId = 0;

  const connected = new Promise((resolvePromise, reject) => {
    socket.addEventListener('open', () => resolvePromise());
    socket.addEventListener('error', reject);
  });

  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (!message.id) return;
    const request = pending.get(message.id);
    if (!request) return;
    pending.delete(message.id);
    if (message.error) request.reject(new Error(message.error.message));
    else request.resolve(message.result);
  });

  return {
    async send(method, params = {}) {
      await connected;
      const id = ++nextId;
      return new Promise((resolvePromise, reject) => {
        pending.set(id, { resolve: resolvePromise, reject });
        socket.send(JSON.stringify({ id, method, params }));
      });
    },
    close() {
      socket.close();
    },
  };
}

async function evaluate(cdp, expression) {
  const result = await cdp.send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text ?? 'Browser evaluation failed');
  }
  return result.result?.value;
}

async function waitFor(cdp, expression, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await evaluate(cdp, expression)) return;
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 150));
  }
  throw new Error(`Timed out waiting for browser condition: ${expression}`);
}

async function waitForDownload(downloadDirectory, beforeFiles) {
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    const files = await readdir(downloadDirectory);
    const downloaded = files.find((file) =>
      file.endsWith('.pdf') && !beforeFiles.has(file),
    );
    if (downloaded) return join(downloadDirectory, downloaded);
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 150));
  }
  throw new Error('Timed out waiting for the report PDF download');
}

function stopProcess(child) {
  return new Promise((resolvePromise) => {
    if (child.exitCode !== null || child.signalCode !== null) {
      resolvePromise();
      return;
    }
    const finish = () => resolvePromise();
    child.once('exit', finish);
    child.kill('SIGTERM');
    setTimeout(() => {
      if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
      resolvePromise();
    }, 2_000);
  });
}

function assertReport(pdfBytes, expected) {
  const pdf = pdfBytes.toString('latin1');
  const searchablePdf = pdf.replace(/\\([()\\])/g, '$1');
  assert(pdf.startsWith('%PDF-1.4'), 'downloaded report is not a PDF');
  assert(pdf.endsWith('%%EOF'), 'downloaded report is missing the PDF trailer');
  assert(pdf.length > 1_000, 'downloaded report is unexpectedly small');

  const rawIndex = searchablePdf.indexOf('Raw measurements');
  const interpretationIndex = searchablePdf.indexOf('Interpretation');
  assert(rawIndex >= 0, 'report is missing the Raw measurements section');
  assert(interpretationIndex > rawIndex, 'Interpretation does not follow Raw measurements');
  assert(searchablePdf.indexOf('Sources and licensing') > interpretationIndex, 'report is missing sources after Interpretation');
  assert(searchablePdf.includes(expected.source), `report is missing source text: ${expected.source}`);
  assert(searchablePdf.includes(expected.license), `report is missing license text: ${expected.license}`);
  assert(searchablePdf.includes('SilverPaws AI is experimental educational software'), 'report is missing experimental language');
  assert(searchablePdf.includes('not a medical diagnosis'), 'report is missing no-diagnosis language');
  assert(searchablePdf.includes('cannot rule out'), 'report is missing cautious limitation language');
  assert(searchablePdf.includes('pain'), 'report is missing pain caution language');
  assert(searchablePdf.includes('injury'), 'report is missing injury caution language');
  for (const fallback of expected.fallbacks ?? []) {
    assert(searchablePdf.includes(fallback), `report is missing fallback text: ${fallback}`);
  }
}

async function run() {
  const downloadDirectory = await mkdtemp(join(tmpdir(), 'silverpaws-report-'));
  const serverPort = await getFreePort();
  const debugPort = await getFreePort();
  const server = spawn('pnpm', ['run', 'dev'], {
    cwd: appRoot,
    env: {
      ...process.env,
      BASE_PATH: '/',
      PORT: String(serverPort),
      NODE_ENV: 'test',
    },
    detached: true,
    stdio: ['ignore', 'ignore', 'ignore'],
  });
  const browser = spawn(chromiumPath, [
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${join(downloadDirectory, 'browser-profile')}`,
    'about:blank',
  ], { detached: true, stdio: ['ignore', 'ignore', 'ignore'] });

  let cdp;
  try {
    await waitForHttp(`${appOrigin.replace('4173', String(serverPort))}/`);
    const webSocketUrl = await waitForDebugger(debugPort);
    cdp = connectToCdp(webSocketUrl);
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('Page.setDownloadBehavior', {
      behavior: 'allow',
      downloadPath: downloadDirectory,
    });

    const origin = appOrigin.replace('4173', String(serverPort));
    const savedAnalyses = [completeAnalysis, missingOptionalAnalysis];
    await cdp.send('Page.navigate', { url: `${origin}/history/${completeAnalysis.id}` });
    await waitFor(cdp, `location.pathname.endsWith('/history/${completeAnalysis.id}')`);
    await evaluate(cdp, `localStorage.setItem('silverpaws:pets', ${JSON.stringify(JSON.stringify([pet]))}); localStorage.setItem('silverpaws:analyses', ${JSON.stringify(JSON.stringify(savedAnalyses))}); location.reload();`);
    await waitFor(cdp, `Boolean(document.querySelector('[data-testid="button-download-report-${completeAnalysis.id}"]'))`);

    let filesBefore = new Set(await readdir(downloadDirectory));
    await evaluate(cdp, `document.querySelector('[data-testid="button-download-report-${completeAnalysis.id}"]').click()`);
    let reportPath = await waitForDownload(downloadDirectory, filesBefore);
    assertReport(await readFile(reportPath), {
      source: completeAnalysis.source,
      license: completeAnalysis.license,
    });

    await cdp.send('Page.navigate', { url: `${origin}/history/${missingOptionalAnalysis.id}` });
    await waitFor(cdp, `location.pathname.endsWith('/history/${missingOptionalAnalysis.id}')`);
    await waitFor(cdp, `Boolean(document.querySelector('[data-testid="button-download-report-${missingOptionalAnalysis.id}"]'))`);
    filesBefore = new Set(await readdir(downloadDirectory));
    await evaluate(cdp, `document.querySelector('[data-testid="button-download-report-${missingOptionalAnalysis.id}"]').click()`);
    reportPath = await waitForDownload(downloadDirectory, filesBefore);
    assertReport(await readFile(reportPath), {
      source: 'User-provided local video (not uploaded by SilverPaws AI)',
      license: 'Not provided; confirm sharing rights before publishing this media',
      fallbacks: [
        'User-provided local video (not uploaded by SilverPaws AI)',
        'Not provided; confirm sharing rights before publishing this media',
      ],
    });

    console.log('Report download browser test passed for complete and fallback metadata.');
  } finally {
    cdp?.close();
    await Promise.all([stopProcess(browser), stopProcess(server)]);
    await rm(downloadDirectory, { recursive: true, force: true });
  }
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const WEB_ROOT = path.resolve(process.cwd());

function createDocumentStub() {
  const elements = new Map();
  return {
    body: { dataset: {} },
    getElementById(id) {
      return elements.get(id) || null;
    },
    querySelector() {
      return null;
    },
    __setElement(id, value) {
      elements.set(id, value);
    },
  };
}

function createLocalStorageStub() {
  const store = new Map();
  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    setItem(key, value) {
      store.set(key, String(value));
    },
    removeItem(key) {
      store.delete(key);
    },
  };
}

export function createBrowserHarness(overrides = {}) {
  const document = overrides.document || createDocumentStub();
  const localStorage = overrides.localStorage || createLocalStorageStub();
  const window = {
    MARATHON_API_BASE: "",
    setTimeout: overrides.setTimeout || setTimeout,
    clearTimeout: overrides.clearTimeout || clearTimeout,
    fetch: overrides.fetch,
    console,
    localStorage,
    ...overrides.window,
  };
  const context = {
    window,
    document,
    localStorage,
    console,
    state: overrides.state,
    fetch: overrides.fetch,
    AbortController: overrides.AbortController || AbortController,
    setTimeout: window.setTimeout,
    clearTimeout: window.clearTimeout,
  };
  context.globalThis = context;
  window.document = document;
  window.localStorage = localStorage;
  return { context, window, document, localStorage };
}

export function loadBrowserScript(relativePath, harness) {
  const absolutePath = path.join(WEB_ROOT, relativePath);
  const source = fs.readFileSync(absolutePath, "utf8");
  vm.runInNewContext(source, harness.context, { filename: absolutePath });
  return harness;
}

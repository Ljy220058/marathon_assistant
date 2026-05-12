import { chromium } from "playwright";

const url = process.env.WORKSPACE_URL || "http://127.0.0.1:4321/#workspace";
const executablePath = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const forbiddenVisibleText = ["API", "Token", "审计", "default_user", "FastAPI", "Generation Trace"];

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function inspectViewport(browser, viewport, label) {
  const page = await browser.newPage({ viewport });
  await page.goto(url, { waitUntil: "networkidle" });

  const base = await page.evaluate((forbidden) => {
    const bodyText = document.body.innerText;
    const toggle = document.querySelector(".side-drawer-toggle");
    const toggleRect = toggle?.getBoundingClientRect();
    return {
      workspaceFlow: Boolean(document.querySelector("#workspaceFlow")),
      primaryCard: Boolean(document.querySelector("[data-primary-workspace-card]")),
      drawerToggle: Boolean(toggle),
      drawerToggleOverflows: toggleRect ? toggleRect.left < 0 || toggleRect.right > window.innerWidth : true,
      hiddenPanelCount: Array.from(document.querySelectorAll("[data-drawer-section]")).filter((item) => item.hidden).length,
      visibleForbidden: forbidden.filter((item) => bodyText.includes(item)),
      hasDayEssentialsTemplate: document.documentElement.textContent.includes("day-card-essentials"),
    };
  }, forbiddenVisibleText);

  assert(base.workspaceFlow, `${label}: workspaceFlow missing`);
  assert(base.primaryCard, `${label}: primary workspace card missing`);
  assert(base.drawerToggle, `${label}: drawer toggle missing`);
  assert(!base.drawerToggleOverflows, `${label}: drawer toggle overflows viewport`);
  assert(base.hiddenPanelCount >= 3, `${label}: drawer panels should be hidden by default`);
  assert(base.visibleForbidden.length === 0, `${label}: forbidden normal-mode text visible: ${base.visibleForbidden.join(", ")}`);
  assert(base.hasDayEssentialsTemplate, `${label}: day-card-essentials template missing`);

  await page.click(".side-drawer-toggle");
  await page.fill("#drawerSearch", "依据");
  const basisActions = await page.evaluate(() =>
    Array.from(document.querySelectorAll("[data-drawer-action]"))
      .filter((item) => !item.hidden)
      .map((item) => item.dataset.drawerAction),
  );
  assert(basisActions.includes("basis"), `${label}: basis search did not reveal basis action`);

  await page.fill("#drawerSearch", "api");
  const apiActions = await page.evaluate(() =>
    Array.from(document.querySelectorAll("[data-drawer-action]"))
      .filter((item) => !item.hidden)
      .map((item) => item.dataset.drawerAction),
  );
  assert(!apiActions.includes("settings"), `${label}: expert settings visible from api search`);

  await page.close();
}

const browser = await chromium.launch({ headless: true, executablePath });
try {
  await inspectViewport(browser, { width: 1440, height: 960 }, "desktop");
  await inspectViewport(browser, { width: 375, height: 812 }, "mobile");
  console.log(`workspace smoke passed: ${url}`);
} finally {
  await browser.close();
}

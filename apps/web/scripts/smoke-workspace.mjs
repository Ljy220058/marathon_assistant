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
    const apiToken = document.querySelector("#apiToken");
    const openaiProviderButton = document.querySelector('[data-provider-choice="openai"]');
    const toggleRect = toggle?.getBoundingClientRect();
    const pageOverflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
    return {
      primaryCard: Boolean(document.querySelector("[data-primary-workspace-card]")),
      planGenerationEntryCount: document.querySelectorAll("[data-plan-generation-entry]").length,
      runQueryVisible: Boolean(document.querySelector("#runQuery")?.offsetParent),
      runnerIdentityCard: Boolean(document.querySelector("#runnerIdentityCard")),
      calendarSection: Boolean(document.querySelector("#calendar-section")),
      mobileQuickNav: Boolean(document.querySelector(".mobile-quick-nav")),
      drawerToggle: Boolean(toggle),
      apiTokenInput: Boolean(apiToken),
      openaiProviderButton: Boolean(openaiProviderButton),
      drawerToggleOverflows: toggleRect ? toggleRect.left < 0 || toggleRect.right > window.innerWidth : true,
      pageOverflow,
      hiddenPanelCount: Array.from(document.querySelectorAll("[data-drawer-section]")).filter((item) => item.hidden).length,
      visibleForbidden: forbidden.filter((item) => bodyText.includes(item)),
      hasDayEssentialsTemplate: document.documentElement.textContent.includes("day-card-essentials"),
    };
  }, forbiddenVisibleText);

  assert(base.primaryCard, `${label}: primary workspace card missing`);
  assert(base.planGenerationEntryCount >= 2, `${label}: plan generation entries missing`);
  assert(base.runQueryVisible, `${label}: generate plan button missing`);
  assert(base.runnerIdentityCard, `${label}: runner identity card missing`);
  assert(base.calendarSection, `${label}: calendar section missing`);
  assert(base.mobileQuickNav, `${label}: mobile quick nav missing`);
  assert(base.pageOverflow === 0, `${label}: page has horizontal overflow (${base.pageOverflow}px)`);
  assert(base.drawerToggle, `${label}: drawer toggle missing`);
  assert(base.apiTokenInput, `${label}: api token input missing`);
  assert(base.openaiProviderButton, `${label}: openai provider button missing`);
  assert(!base.drawerToggleOverflows, `${label}: drawer toggle overflows viewport`);
  assert(base.hiddenPanelCount >= 3, `${label}: drawer panels should be hidden by default`);
  assert(base.visibleForbidden.length === 0, `${label}: forbidden normal-mode text visible: ${base.visibleForbidden.join(", ")}`);
  assert(base.hasDayEssentialsTemplate, `${label}: day-card-essentials template missing`);

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

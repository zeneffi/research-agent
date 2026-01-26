import { chromium, Browser, BrowserContext, Page } from 'playwright';
import { v4 as uuidv4 } from 'uuid';
import * as fs from 'fs';
import * as path from 'path';

interface Tab {
  id: string;
  page: Page;
  url: string;
  title: string;
}

interface ClickOptions {
  selector?: string;
  text?: string;
  ref?: string;
}

interface TypeOptions {
  selector?: string;
  text: string;
  submit?: boolean;
  ref?: string;
}

interface WaitOptions {
  selector?: string;
  text?: string;
  timeout?: number;
}

interface ScreenshotOptions {
  fullPage?: boolean;
  path?: string;
}

interface SessionInfo {
  id: string;
  startTime: string;
  currentUrl: string;
  tabs: number;
  history: string[];
}

export class BrowserManager {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private tabs: Map<string, Tab> = new Map();
  private currentTabId: string | null = null;
  private sessionId: string;
  private startTime: Date;
  private history: string[] = [];
  private ready: boolean = false;

  constructor() {
    this.sessionId = uuidv4();
    this.startTime = new Date();
  }

  async initialize(): Promise<void> {
    if (this.browser) {
      return;
    }

    this.browser = await chromium.launch({
      headless: false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1920,1080'
      ]
    });

    // プロキシ設定を環境変数から取得
    const proxyServer = process.env.PROXY_SERVER;
    const proxyUsername = process.env.PROXY_USERNAME;
    const proxyPassword = process.env.PROXY_PASSWORD;

    const contextOptions: any = {
      viewport: { width: 1920, height: 1080 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    };

    // プロキシが設定されている場合は追加
    if (proxyServer) {
      contextOptions.proxy = {
        server: proxyServer,
        username: proxyUsername,
        password: proxyPassword
      };
      console.log(`Using proxy: ${proxyServer}`);
    }

    this.context = await this.browser.newContext(contextOptions);

    // 初期タブを作成
    const page = await this.context.newPage();
    const tabId = uuidv4();
    this.tabs.set(tabId, {
      id: tabId,
      page,
      url: 'about:blank',
      title: 'New Tab'
    });
    this.currentTabId = tabId;
    this.ready = true;

    console.log(`Browser initialized with session ID: ${this.sessionId}`);
  }

  isReady(): boolean {
    return this.ready;
  }

  private getCurrentPage(): Page {
    if (!this.currentTabId || !this.tabs.has(this.currentTabId)) {
      throw new Error('No active tab');
    }
    return this.tabs.get(this.currentTabId)!.page;
  }

  private async updateTabInfo(tabId: string): Promise<void> {
    const tab = this.tabs.get(tabId);
    if (tab) {
      tab.url = tab.page.url();
      tab.title = await tab.page.title();
    }
  }

  async navigate(url: string, waitUntil: 'load' | 'domcontentloaded' | 'networkidle' = 'domcontentloaded'): Promise<{ url: string; title: string }> {
    await this.ensureInitialized();
    const page = this.getCurrentPage();

    await page.goto(url, { waitUntil });

    const title = await page.title();
    const currentUrl = page.url();

    this.history.push(currentUrl);
    await this.updateTabInfo(this.currentTabId!);

    return { url: currentUrl, title };
  }

  async screenshot(options: ScreenshotOptions = {}): Promise<string> {
    await this.ensureInitialized();
    const page = this.getCurrentPage();

    const screenshotPath = options.path || `/tmp/screenshot-${Date.now()}.png`;
    await page.screenshot({
      path: screenshotPath,
      fullPage: options.fullPage || false
    });

    // Base64エンコードして返す
    const buffer = fs.readFileSync(screenshotPath);
    return buffer.toString('base64');
  }

  async getSnapshot(): Promise<object> {
    await this.ensureInitialized();
    const page = this.getCurrentPage();

    // ページの構造情報を取得
    const elements = await page.evaluate(() => {
      const getElements = (el: Element, depth = 0): object[] => {
        if (depth > 3) return [];
        const result: object[] = [];
        const children = el.children;
        for (let i = 0; i < children.length; i++) {
          const child = children[i];
          const tag = child.tagName.toLowerCase();
          if (['script', 'style', 'noscript'].includes(tag)) continue;
          result.push({
            tag,
            text: child.textContent?.slice(0, 100) || '',
            children: getElements(child, depth + 1)
          });
        }
        return result;
      };
      return getElements(document.body);
    });

    return {
      url: page.url(),
      title: await page.title(),
      elements
    };
  }

  async click(options: ClickOptions): Promise<void> {
    await this.ensureInitialized();
    const page = this.getCurrentPage();

    if (options.selector) {
      await page.click(options.selector);
    } else if (options.text) {
      await page.getByText(options.text).first().click();
    } else if (options.ref) {
      // refはセレクタとして使用
      await page.click(options.ref);
    } else {
      throw new Error('Either selector, text, or ref is required');
    }
  }

  async type(options: TypeOptions): Promise<void> {
    await this.ensureInitialized();
    const page = this.getCurrentPage();

    let element;
    if (options.selector) {
      element = page.locator(options.selector);
    } else if (options.ref) {
      element = page.locator(options.ref);
    } else {
      // フォーカスされた要素に入力
      element = page.locator(':focus');
    }

    await element.fill(options.text);

    if (options.submit) {
      await element.press('Enter');
    }
  }

  async getContent(): Promise<{ html: string; text: string; url: string; title: string }> {
    await this.ensureInitialized();
    const page = this.getCurrentPage();

    const html = await page.content();
    const text = await page.evaluate(() => document.body.innerText);

    return {
      html,
      text,
      url: page.url(),
      title: await page.title()
    };
  }

  async evaluate(script: string): Promise<unknown> {
    await this.ensureInitialized();
    const page = this.getCurrentPage();

    // スクリプトを関数として評価
    return await page.evaluate(script);
  }

  async wait(options: WaitOptions): Promise<void> {
    await this.ensureInitialized();
    const page = this.getCurrentPage();

    if (options.selector) {
      await page.waitForSelector(options.selector, { timeout: options.timeout });
    } else if (options.text) {
      await page.getByText(options.text).waitFor({ timeout: options.timeout });
    } else {
      await page.waitForTimeout(options.timeout || 1000);
    }
  }

  async getTabs(): Promise<{ id: string; url: string; title: string; active: boolean }[]> {
    await this.ensureInitialized();

    const tabList: { id: string; url: string; title: string; active: boolean }[] = [];
    for (const [id, tab] of this.tabs) {
      await this.updateTabInfo(id);
      tabList.push({
        id,
        url: tab.url,
        title: tab.title,
        active: id === this.currentTabId
      });
    }

    return tabList;
  }

  async newTab(url?: string): Promise<string> {
    await this.ensureInitialized();

    if (!this.context) {
      throw new Error('Browser context not initialized');
    }

    const page = await this.context.newPage();
    const tabId = uuidv4();

    this.tabs.set(tabId, {
      id: tabId,
      page,
      url: url || 'about:blank',
      title: 'New Tab'
    });

    if (url) {
      await page.goto(url);
      await this.updateTabInfo(tabId);
    }

    this.currentTabId = tabId;
    return tabId;
  }

  async closeTab(tabId?: string): Promise<void> {
    await this.ensureInitialized();

    const targetTabId = tabId || this.currentTabId;
    if (!targetTabId) {
      throw new Error('No tab to close');
    }

    const tab = this.tabs.get(targetTabId);
    if (tab) {
      await tab.page.close();
      this.tabs.delete(targetTabId);

      // 現在のタブが閉じられた場合、別のタブを選択
      if (targetTabId === this.currentTabId) {
        const remaining = Array.from(this.tabs.keys());
        this.currentTabId = remaining.length > 0 ? remaining[0] : null;
      }
    }
  }

  async selectTab(tabId: string): Promise<void> {
    await this.ensureInitialized();

    if (!this.tabs.has(tabId)) {
      throw new Error(`Tab ${tabId} not found`);
    }

    this.currentTabId = tabId;
    const tab = this.tabs.get(tabId)!;
    await tab.page.bringToFront();
  }

  async getSessionInfo(): Promise<SessionInfo> {
    await this.ensureInitialized();

    return {
      id: this.sessionId,
      startTime: this.startTime.toISOString(),
      currentUrl: this.currentTabId ? this.tabs.get(this.currentTabId)!.url : '',
      tabs: this.tabs.size,
      history: this.history
    };
  }

  async close(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
      this.context = null;
      this.tabs.clear();
      this.currentTabId = null;
      this.ready = false;
      console.log('Browser closed');
    }
  }

  private async ensureInitialized(): Promise<void> {
    if (!this.browser) {
      await this.initialize();
    }
  }
}

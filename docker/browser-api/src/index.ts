import express, { Request, Response, NextFunction } from 'express';
import { BrowserManager } from './browserManager';
import { v4 as uuidv4 } from 'uuid';

const app = express();
app.use(express.json());

const browserManager = new BrowserManager();
const PORT = parseInt(process.env.API_PORT || '3000', 10);

// リクエストログミドルウェア
app.use((req: Request, _res: Response, next: NextFunction) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// ヘルスチェック
app.get('/health', (_req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    browser: browserManager.isReady() ? 'ready' : 'initializing'
  });
});

// ブラウザ初期化
app.post('/browser/init', async (_req: Request, res: Response) => {
  try {
    await browserManager.initialize();
    res.json({ success: true, message: 'Browser initialized' });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// ページナビゲーション
app.post('/browser/navigate', async (req: Request, res: Response) => {
  try {
    const { url, waitUntil = 'domcontentloaded' } = req.body;
    if (!url) {
      return res.status(400).json({ success: false, error: 'URL is required' });
    }
    const result = await browserManager.navigate(url, waitUntil);
    res.json({ success: true, ...result });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// スクリーンショット取得
app.post('/browser/screenshot', async (req: Request, res: Response) => {
  try {
    const { fullPage = false, path } = req.body;
    const screenshot = await browserManager.screenshot({ fullPage, path });
    res.json({ success: true, screenshot });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// ページスナップショット（アクセシビリティツリー）
app.post('/browser/snapshot', async (_req: Request, res: Response) => {
  try {
    const snapshot = await browserManager.getSnapshot();
    res.json({ success: true, snapshot });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// 要素クリック
app.post('/browser/click', async (req: Request, res: Response) => {
  try {
    const { selector, text, ref } = req.body;
    await browserManager.click({ selector, text, ref });
    res.json({ success: true, message: 'Click performed' });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// テキスト入力
app.post('/browser/type', async (req: Request, res: Response) => {
  try {
    const { selector, text, submit = false, ref } = req.body;
    await browserManager.type({ selector, text, submit, ref });
    res.json({ success: true, message: 'Text typed' });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// ページコンテンツ取得
app.post('/browser/content', async (_req: Request, res: Response) => {
  try {
    const content = await browserManager.getContent();
    res.json({ success: true, ...content });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// JavaScript実行
app.post('/browser/evaluate', async (req: Request, res: Response) => {
  try {
    const { script } = req.body;
    if (!script) {
      return res.status(400).json({ success: false, error: 'Script is required' });
    }
    const result = await browserManager.evaluate(script);
    res.json({ success: true, result });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// ページ待機
app.post('/browser/wait', async (req: Request, res: Response) => {
  try {
    const { selector, text, timeout = 30000 } = req.body;
    await browserManager.wait({ selector, text, timeout });
    res.json({ success: true, message: 'Wait completed' });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// タブ一覧取得
app.get('/browser/tabs', async (_req: Request, res: Response) => {
  try {
    const tabs = await browserManager.getTabs();
    res.json({ success: true, tabs });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// 新しいタブを開く
app.post('/browser/tabs/new', async (req: Request, res: Response) => {
  try {
    const { url } = req.body;
    const tabId = await browserManager.newTab(url);
    res.json({ success: true, tabId });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// タブを閉じる
app.post('/browser/tabs/close', async (req: Request, res: Response) => {
  try {
    const { tabId } = req.body;
    await browserManager.closeTab(tabId);
    res.json({ success: true, message: 'Tab closed' });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// タブを選択
app.post('/browser/tabs/select', async (req: Request, res: Response) => {
  try {
    const { tabId } = req.body;
    await browserManager.selectTab(tabId);
    res.json({ success: true, message: 'Tab selected' });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// ブラウザ終了
app.post('/browser/close', async (_req: Request, res: Response) => {
  try {
    await browserManager.close();
    res.json({ success: true, message: 'Browser closed' });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// セッション情報取得
app.get('/session', async (_req: Request, res: Response) => {
  try {
    const session = await browserManager.getSessionInfo();
    res.json({ success: true, session });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// プロファイル保存（テスト用）
app.post('/save-profile', async (_req: Request, res: Response) => {
  try {
    await browserManager.close();
    res.json({ success: true, message: 'Profile saved and browser closed' });
  } catch (error) {
    res.status(500).json({ success: false, error: String(error) });
  }
});

// エラーハンドリング
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ success: false, error: err.message });
});

// サーバー起動
const server = app.listen(PORT, async () => {
  console.log(`Browser API server running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);

  // 自動的にブラウザを初期化
  console.log('Initializing browser...');
  try {
    await browserManager.initialize();
    console.log('Browser initialized successfully');
  } catch (error) {
    console.error('Failed to initialize browser:', error);
  }
});

// グレースフルシャットダウン
process.on('SIGTERM', async () => {
  console.log('[SIGNAL] SIGTERM received, shutting down gracefully...');
  try {
    await browserManager.close();
    console.log('[SIGNAL] Browser manager closed successfully');
  } catch (error) {
    console.error('[SIGNAL] Error closing browser manager:', error);
  }
  server.close(() => {
    console.log('[SIGNAL] Server closed, exiting process');
    process.exit(0);
  });

  // Timeout to force exit if graceful shutdown takes too long
  setTimeout(() => {
    console.error('[SIGNAL] Forced exit after timeout');
    process.exit(1);
  }, 8000);
});

process.on('SIGINT', async () => {
  console.log('[SIGNAL] SIGINT received, shutting down gracefully...');
  try {
    await browserManager.close();
    console.log('[SIGNAL] Browser manager closed successfully');
  } catch (error) {
    console.error('[SIGNAL] Error closing browser manager:', error);
  }
  server.close(() => {
    console.log('[SIGNAL] Server closed, exiting process');
    process.exit(0);
  });
});

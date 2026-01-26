# Playwright + VNC ブラウザ環境
FROM node:20-bookworm-slim

# 環境変数設定
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV VNC_PORT=5900
ENV NOVNC_PORT=6080
ENV API_PORT=3000
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    # VNC関連
    xvfb \
    x11vnc \
    novnc \
    websockify \
    fluxbox \
    # Playwright依存
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    # ユーティリティ
    supervisor \
    curl \
    wget \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ
WORKDIR /app

# Playwrightのインストール
RUN npm init -y && \
    npm install playwright@latest && \
    npx playwright install chromium --with-deps

# browser-apiの依存関係（キャッシュ活用のため先にpackage.jsonをコピー）
COPY browser-api/package*.json ./browser-api/
RUN cd browser-api && npm install

# browser-apiのソースコード（.dockerignoreでnode_modules除外）
COPY browser-api/ ./browser-api/

# TypeScriptビルド
RUN cd browser-api && npm run build

# supervisordの設定
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# VNCパスワード設定（オプション）
RUN mkdir -p ~/.vnc && x11vnc -storepasswd "" ~/.vnc/passwd || true

# スタートアップスクリプト
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# ポート公開
EXPOSE ${VNC_PORT} ${NOVNC_PORT} ${API_PORT}

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${API_PORT}/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

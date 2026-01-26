# Config

## proxies.json

プロキシ設定ファイル。

**プロバイダー**: Webshare
**ダッシュボード**: https://dashboard.webshare.io/

### 形式

```json
{
  "proxies": [
    {"host": "IP", "port": PORT, "username": "USER", "password": "PASS"}
  ]
}
```

### プロキシのダウンロード方法

1. https://dashboard.webshare.io/ にログイン
2. Proxy > Proxy List に移動
3. Download をクリック
4. フォーマット: `IP:PORT:USER:PASS` で出力
5. このファイルに変換して保存

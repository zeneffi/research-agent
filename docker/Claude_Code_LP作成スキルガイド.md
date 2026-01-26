# Claude Codeでプロレベルのランディングページを作成するスキルガイド

> 調査日: 2026年1月22日（Claude Skills詳細追記: 2026年1月23日）
> 日本語・英語の両言語でWeb調査した結果をまとめたガイド

---

## 概要

Claude Code（およびClaude Artifact）を使えば、**プログラミング未経験者でもプロ品質のランディングページを半日〜数時間で制作可能**になった。従来は外注で20〜100万円、制作期間1〜3ヶ月かかっていた作業が、AIの活用により大幅に短縮・コスト削減できる。

---

## 1. なぜClaude CodeがLP制作に適しているのか

### 従来のLP制作の課題

| 項目 | 従来の課題 |
|------|-----------|
| 費用 | 外注で20〜100万円 |
| 期間 | 企画から完成まで1〜3ヶ月 |
| 修正 | 変更のたびに追加費用発生 |
| 専門知識 | HTML/CSS、デザインスキルが必要 |

### Claude Code/Artifactの利点

- **単一HTMLファイル**として完結したコードを出力可能
- インライン CSS & JSを含む自己完結型
- レスポンシブ対応も自動生成
- 修正は自然言語で指示するだけ

---

## 2. プロンプト設計テクニック（日本語情報）

### 基本プロンプト構造

Zennの記事で紹介されている**LP作成プロンプトの基本構造**:

```markdown
# 命令
あなたは一流のWebデザイナー兼コピーライターです。
以下の条件に従って、ビジネス志向のランディングページ（LP）を日本語でフル生成してください。
最終納品物は **単一の HTML ファイル（内部にインライン CSS & 必要最小の JS を含む）** とします。

## 0. デザインスタイル
次のデザインを採用し、色・フォント・レイアウト・装飾のトーンで表現してください。
- 〔例：プロフェッショナルなITコンサル風、おしゃれなオーガニック風 など〕

## 1. 基本情報
- LPの目的：〔例：SaaSの無料トライアル登録を獲得〕
- 商品・サービス：〔例：中小企業向け売上分析 SaaS〕
- ターゲット：〔例：商学部の学生起業家、20〜25歳〕
- メインカラー：〔例：#0052CC〕
- アクセント色：〔例：#FFB300〕

## 2. ページ構成
1. ヒーローセクション（キャッチコピー + CTA）
2. 課題提示 & ベネフィット（3~4項目、アイコン付きカード）
3. 機能／特徴ハイライト（4~6項目）
4. 社会的証明（成功事例 + 口コミ）
5. 料金プラン（2〜3段階）
6. FAQ（5問5答）
7. 今すぐ行動を促すセクション
8. フッター
```

### デザインスタイルの例

| スタイル名 | 適用シーン |
|-----------|-----------|
| プロフェッショナルなITコンサル風 | BtoB SaaS、コンサルサービス |
| おしゃれなオーガニック風 | 自然派商品、食品、美容 |
| 近未来的なサイバーパンク風 | テック系スタートアップ |
| ミニマルモダン | 高級ブランド、建築 |

---

## 3. 11要素フレームワーク（英語情報）

MCP Marketで公開されている**Claude Code Skill「Landing Page Guide」**では、高コンバージョンLPの11必須要素を定義:

### 11 Essential Elements for Landing Pages

1. **Hero Section** - 第一印象を決める
2. **Problem Statement** - ユーザーの課題を言語化
3. **Solution Overview** - 解決策の提示
4. **Features & Benefits** - 機能と利益
5. **Social Proof** - 証言・実績
6. **Pricing** - 料金体系
7. **FAQ** - よくある質問
8. **CTA (Call to Action)** - 行動喚起
9. **Trust Indicators** - 信頼性の証明
10. **Mobile Responsiveness** - モバイル対応
11. **SEO Optimization** - 検索最適化

---

## 4. ツール組み合わせのベストプラクティス

### 推奨ワークフロー

```
1. ChatGPT / Claude → LP構成・コピーライティング
2. v0 (Vercel) → UIデザイン・Reactコンポーネント生成
3. Cursor / Claude Code → コード調整・デプロイ準備
```

### v0 + Cursorの組み合わせ

日本語記事で多く紹介されている組み合わせ:

1. **v0でデザイン生成**: 「シンプルかつ洗練された新商品の紹介LPを日本語で作成して」
2. **Cursorで微調整**: アニメーション追加、レスポンシブ調整
3. **Vercelでデプロイ**: ワンクリックで公開

---

## 5. 技術仕様のベストプラクティス

### 出力フォーマット

```markdown
### 技術仕様
- レスポンシブ対応（Flexbox / Grid使用、幅768px未満で縦並び）
- Webフォント：Google Fonts から１種類読み込み
- アニメーション：ページロード時にフェードイン（CSS keyframes）
- アイコン：Font Awesome SVG を直接使用
- HTML内コメントで主要セクション開始位置を明示
```

### 出力指示のコツ

- **「単一HTMLファイルで出力」** を明示する
- コードブロックは ` ```html ` から始め ` ``` ` で終わる
- 「VS Codeでそのまま貼り付けて動作すること」を保証させる

---

## 6. 実践プロンプト例

### 例1: SaaS商品LP

```
あなたは一流のWebデザイナーです。
以下の条件でSaaS紹介LPを作成してください。

【サービス】クラウド在庫管理システム「StockAI」
【ターゲット】中小EC事業者
【目的】14日間無料トライアル登録
【デザイン】プロフェッショナルなSaaS風、ブルー基調
【必須セクション】ヒーロー、機能紹介、料金プラン、FAQ、CTA

出力は単一HTMLファイル（インラインCSS含む）でお願いします。
```

### 例2: 参考デザインを模倣

```
以下のURLのデザインを参考に、別サービスのLPを作成してください。
参考URL: [参考サイトURL]

【サービス名】〇〇
【変更点】
- カラーをグリーン系に
- ターゲットを医療従事者に
- 価格帯を高めに設定

技術仕様:
- Next.js 14 + ShadCN UI
- レスポンシブ対応必須
```

---

## 7. よくある失敗と対策

| 失敗パターン | 対策 |
|-------------|------|
| デザインが汎用的すぎる | デザインスタイルを具体的に指定する |
| コンバージョン要素が弱い | CTAボタンの文言を「動詞+利益」形式に |
| モバイルで崩れる | レスポンシブ要件を明示する |
| コードが複雑すぎる | 「単一HTMLファイル」「インラインCSS」を指定 |

---

## 8. Claude Skills詳細ガイド

Claude Codeの**Skills**機能は、Claudeの能力を拡張するための再利用可能な指示セットである。SKILL.mdファイルを作成することで、カスタムスキルをClaudeのツールキットに追加できる。

### 8.1 Skillsの基本概念

Skills（スキル）とは：
- **SKILL.md**ファイルに指示を記述
- Claudeが関連する文脈で自動的にロード
- `/skill-name`でユーザーから直接呼び出し可能
- 複数のAIツールで動作する**Agent Skills オープンスタンダード**に準拠

### 8.2 SKILL.mdの構造

```yaml
---
name: my-skill
description: スキルの説明（Claudeがいつ使うか判断するために使用）
disable-model-invocation: true  # trueでユーザー呼び出しのみ
allowed-tools: Read, Grep, Glob  # 使用可能なツールを制限
context: fork  # サブエージェントで実行
agent: Explore  # 使用するエージェントタイプ
---

ここにスキルの指示を記述...
```

### 8.3 フロントマター設定一覧

| フィールド | 必須 | 説明 |
|-----------|------|------|
| `name` | No | スキル名（省略時はディレクトリ名、小文字・数字・ハイフンのみ） |
| `description` | 推奨 | スキルの説明と使用タイミング |
| `argument-hint` | No | 引数のヒント（例: `[issue-number]`） |
| `disable-model-invocation` | No | trueでClaude自動呼び出しを無効化 |
| `user-invocable` | No | falseでメニューから非表示 |
| `allowed-tools` | No | 使用可能なツールのリスト |
| `model` | No | 使用するモデル |
| `context` | No | `fork`でサブエージェント実行 |
| `agent` | No | エージェントタイプ（Explore, Plan等） |

### 8.4 スキルの保存場所

| レベル | パス | 適用範囲 |
|-------|-----|---------|
| Enterprise | 管理設定参照 | 組織全体 |
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` | 全プロジェクト |
| Project | `.claude/skills/<skill-name>/SKILL.md` | 当該プロジェクト |
| Plugin | `<plugin>/skills/<skill-name>/SKILL.md` | プラグイン有効時 |

### 8.5 LP制作に使えるClaude Skills（MCP Market）

MCP Marketには**32,300以上のスキル**が公開されており、LP制作に役立つものが多数ある：

#### Landing Page Guide（bear2u）
- **GitHub Stars**: 562
- **用途**: 11要素フレームワークを使用した高コンバージョンLP生成
- **技術**: Next.js 14+ / ShadCN UI / TypeScript
- **特徴**: SEO最適化、レスポンシブ対応、アクセシビリティ対応
- **インストール**: `npx skillfish add bear2u/my-skills/default/landing-page-guide`

#### Frontend Design（haduyson）
- **用途**: 汎用的なAI美学を避けた、独自性のあるUI制作
- **特徴**:
  - デザインシンキングプロセスで独自の美学を確立
  - スクリーンショットからカラー・タイポグラフィ・レイアウトを抽出
  - 高度なタイポグラフィ、モーション、レイアウトに注力
- **インストール**: `npx skillfish add haduyson/teletask/claude/frontend-design`

#### Skill Writer（warpcode）
- **用途**: 自分でスキルを作成するためのガイド
- **特徴**: SKILL.mdの構造化、フロントマター設計、検証・デバッグ支援
- **インストール**: `npx skillfish add warpcode/dotfiles/generic-.config-opencode/skill-writer`

### 8.6 カスタムスキルの作成例：LP生成スキル

```yaml
---
name: create-landing-page
description: 高品質なランディングページを生成。SaaS、EC、サービス紹介などのLP作成時に使用。
disable-model-invocation: true
allowed-tools: Read, Write, Bash
---

# ランディングページ生成スキル

ユーザーの要件に基づき、プロ品質のLPを生成します。

## 必須確認項目
1. サービス/商品名
2. ターゲットユーザー
3. LPの目的（問い合わせ獲得、登録、購入など）
4. デザインスタイル

## 出力形式
- 単一HTMLファイル（インラインCSS/JS含む）
- レスポンシブ対応（モバイルファースト）
- 11要素フレームワーク準拠

## セクション構成
1. ヒーロー（キャッチコピー + CTA）
2. 課題提示
3. 解決策
4. 機能・特徴
5. 社会的証明
6. 料金プラン（任意）
7. FAQ
8. 最終CTA
9. フッター
```

### 8.7 動的コンテキスト注入

`!command`構文でシェルコマンドの実行結果をスキルに注入可能：

```yaml
---
name: pr-summary
description: Pull Requestの変更を要約
context: fork
agent: Explore
---

## PRコンテキスト
- PR差分: !`gh pr diff`
- PRコメント: !`gh pr view --comments`
- 変更ファイル: !`gh pr diff --name-only`

## タスク
このPRを要約してください...
```

### 8.8 スキルのインストール方法

#### Skill.Fish（推奨）
```bash
npx skillfish add <author>/<repo>/<path>/<skill-name>
```

#### 手動インストール
1. GitHubからSKILL.mdをダウンロード
2. `~/.claude/skills/<skill-name>/SKILL.md`に配置
3. Claude Codeを再起動

---

## 9. 参考リソース

### 日本語

- [AIツールClaudeで高品質なLPを制作する完全ガイド](https://note.com/tsuchi278/n/n5d7417165368)
- [Claude Artifact用のLP作成プロンプト - Zenn](https://zenn.dev/acntechjp/articles/deeb0cbe5ff6d1)
- [話題のClaude Codeで本気のLPを制作してみた](https://biz.addisteria.com/claude-code/)
- [Claude4 x Claude Codeで半日でランディングページを制作した話 - Qiita](https://qiita.com/sunazuka/items/f1310d3b571c90075353)
- [ChatGPT+v0+CursorでLP作成](https://dodotechno.com/ai-landing-page/)
- [AI爆速LP作成ガイド：V0 & Cursor Composer](https://note.com/ryyo_note/n/nd46d8422f337)

### 英語

- [Landing Page Guide - Claude Code Skill](https://mcpmarket.com/tools/skills/landing-page-guide)
- [How to Create HTML Landing Pages with AI - Bind AI](https://blog.getbind.co/how-to-create-html-landing-pages-with-ai/)
- [How To Create a Stunning No-Code Landing Page with Claude Code - YouTube](https://www.youtube.com/watch?v=YOIvdRG6OKw)
- [GitHub: claude-code-demo-landing-page](https://github.com/carlvellotti/claude-code-demo-landing-page)

### 公式ドキュメント（Claude Skills）

- [Extend Claude with skills - 公式ドキュメント](https://code.claude.com/docs/en/skills)
- [MCP Market - Agent Skills Directory](https://mcpmarket.com/tools/skills)
- [Claude Code GitHub Repository](https://github.com/anthropics/claude-code)

---

## 10. まとめ

Claude Codeでプロレベルのランディングページを作成するポイント:

1. **明確なプロンプト設計** - デザインスタイル、ターゲット、目的を具体的に指定
2. **11要素フレームワーク** - ヒーロー、課題、解決策、証明、CTAの流れを意識
3. **技術仕様の指定** - 単一HTML、インラインCSS、レスポンシブ対応を明示
4. **ツールの組み合わせ** - v0でデザイン、Cursor/Claude Codeで仕上げ
5. **反復改善** - 自然言語での修正指示を繰り返す
6. **Claude Skillsの活用** - MCP Marketの既存スキルを活用、またはカスタムスキルを作成

### Claude Skillsを活用する利点

- **再利用性**: 一度作成したスキルは何度でも使える
- **標準化**: チーム内でLP制作のベストプラクティスを共有
- **効率化**: `npx skillfish add`でインストール、`/skill-name`で呼び出し
- **拡張性**: サブエージェントやツール制限で高度なワークフローを構築

従来の制作プロセスを**半日〜数時間に短縮**し、**コストを大幅削減**できる時代が到来している。Claude Skillsを活用すれば、さらに効率的かつ一貫性のあるLP制作が可能になる。

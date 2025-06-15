# Web Crawler with Crawl4AI

Webサイトをクロールしてマークダウン形式で保存するPythonスクリプトです。

## 必要な環境

- Python 3.7+
- crawl4ai
- nest-asyncio

## インストール

```bash
pip install crawl4ai nest-asyncio
```

## 使い方

### 基本的な使用例

```bash
# Figma Plugin Docsをデフォルトの./docsディレクトリに保存
python main.py "https://www.figma.com/plugin-docs/"

# 出力ディレクトリを指定
python main.py "https://www.figma.com/plugin-docs/" -o ./figma-docs

# 最大深度を指定（デフォルト: 3）
python main.py "https://www.figma.com/plugin-docs/" -d 5

# すべてのオプションを指定
python main.py "https://www.figma.com/plugin-docs/" -o ./output -d 2

```



### オプション

| オプション    | 短縮形 | デフォルト | 説明             |
| ------------- | ------ | ---------- | ---------------- |
| `--output`    | `-o`   | `./docs`   | 出力ディレクトリ |
| `--max-depth` | `-d`   | `3`        | 最大クロール深度 |

### ヘルプ

```bash
python main.py --help
```

## 機能

- 深度優先探索によるWebクロール
- 同一ドメイン内のリンクのみをクロール
- URLパターンフィルタリング（現在はFigma Plugin Docs用）
- マークダウン形式での出力
- 非同期処理による高速クロール

## 制限事項

- 現在のフィルタはFigma Plugin Docs専用（`*figma.com/plugin-docs/*`）
- 他のサイトをクロールする場合はフィルタの修正が必要

## 出力形式

各ページは以下の形式でファイル名が生成されます：

- URL: `https://example.com/path/to/page` → ファイル名: `path-to-page.md`
- ルートURL → ファイル名: `index.md`

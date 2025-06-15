import asyncio
import argparse
import os
from urllib.parse import urlparse

# ノートブック実行時の asyncio 再入場許可
import nest_asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter

nest_asyncio.apply()


async def crawl_and_save(
    root_url: str, output_dir: str = "./docs", max_depth: int = 3, css_selector: str = None
):
    # 保存先ディレクトリを作成
    os.makedirs(output_dir, exist_ok=True)

    # 1. URLに基づいて動的にフィルタパターンを生成
    parsed_url = urlparse(root_url)
    domain = parsed_url.netloc
    url_pattern = f"*{domain}*"
    url_filter = URLPatternFilter(patterns=[url_pattern])
    filter_chain = FilterChain([url_filter])

    # 2. 深いクロール戦略の設定
    strategy = BFSDeepCrawlStrategy(
        max_depth=max_depth,  # 引数で指定された階層まで
        include_external=False,  # 同一ドメイン外は除外
        max_pages=12000,  # 最大 100 ページ
        filter_chain=filter_chain,  # パス制限を適用
    )

    # 3. クロール設定
    config_params = {
        "deep_crawl_strategy": strategy,
        "scraping_strategy": LXMLWebScrapingStrategy(),
        "wait_for_images": False,
        "scan_full_page": True,
        "page_timeout": 120000,
        "js_code": [
            # 例: ボタンをクリックして1秒待機してから抽出開始
            "(async () => { document.querySelector('button.load-more')?.click(); await new Promise(r=>setTimeout(r,1000)); })();"
        ],
        "verbose": True,
    }

    if css_selector:
        config_params["css_selector"] = css_selector

    run_config = CrawlerRunConfig(**config_params)

    # 4. 非同期クロール実行
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(url=root_url, config=run_config)

        for res in results:
            if not res.success:
                continue
            # URL からファイル名を生成
            path = urlparse(res.url).path.strip("/").replace("/", "-") or "index"
            filename = os.path.join(output_dir, f"{path}.md")
            # Markdown を書き出し
            with open(filename, "w", encoding="utf-8") as f:
                f.write(res.markdown.raw_markdown)
            print(f"Saved: {filename}")


# スクリプト実行用エントリポイント
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl and save web pages as Markdown")
    parser.add_argument("url", help="Root URL to crawl")
    parser.add_argument(
        "-o", "--output", default="./docs", help="Output directory (default: ./docs)"
    )
    parser.add_argument(
        "-d", "--max-depth", type=int, default=3, help="Maximum crawl depth (default: 3)"
    )
    parser.add_argument(
        "-s",
        "--selector",
        help="CSS selector to extract specific content (e.g., '.markdown-preview-sizer')",
    )

    args = parser.parse_args()
    asyncio.run(crawl_and_save(args.url, args.output, args.max_depth, args.selector))

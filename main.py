#!/usr/bin/env python3
"""
Web Crawler with Crawl4AI

Webサイトをクロールしてマークダウン形式で保存するPythonスクリプトです。
"""

import argparse
import asyncio
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Set, List
import nest_asyncio

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


class WebCrawler:
    def __init__(self, start_url: str, output_dir: str = "./docs", max_depth: int = 3, css_selector: str = None, allow_query: bool = False):
        """
        Webクローラーを初期化
        
        Args:
            start_url: 開始URL
            output_dir: 出力ディレクトリ
            max_depth: 最大クロール深度
            css_selector: 指定したCSSセレクタのDOM要素のみを抽出
            allow_query: クエリパラメータ付きURLへのアクセスを許可するかどうか
        """
        self.start_url = start_url
        self.output_dir = Path(output_dir)
        self.max_depth = max_depth
        self.css_selector = css_selector
        self.allow_query = allow_query
        self.visited_urls: Set[str] = set()
        self.domain = urlparse(start_url).netloc
        
        # 出力ディレクトリを作成
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # URLパターンフィルタ（設定されていない場合は全てのドメインを許可）
        self.allowed_patterns = [
            r".*figma\.com/plugin-docs/.*",
            r".*example\.com.*",  # テスト用
            r".*learn\.microsoft\.com.*",  # Microsoft Learn用
            r".*"  # 全てのURLを許可（汎用的な使用のため）
        ]
    
    def is_valid_url(self, url: str) -> bool:
        """
        URLが有効かどうかをチェック
        
        Args:
            url: チェックするURL
            
        Returns:
            bool: URLが有効かどうか
        """
        parsed = urlparse(url)
        
        # 同一ドメインかチェック
        if parsed.netloc != self.domain:
            return False
        
        # クエリパラメータのチェック
        if not self.allow_query and parsed.query:
            # 開始URLと同じクエリパラメータの場合のみ許可
            start_parsed = urlparse(self.start_url)
            if parsed.query != start_parsed.query:
                return False
        
        # ベースURL配下かチェック
        if not parsed.path.startswith(urlparse(self.start_url).path):
            return False
        
        # URLパターンフィルタリング
        for pattern in self.allowed_patterns:
            if re.match(pattern, url):
                return True
        
        return False
    
    def url_to_filename(self, url: str) -> str:
        """
        URLをファイル名に変換
        
        Args:
            url: 変換するURL
            
        Returns:
            str: ファイル名
        """
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if not path:
            filename = "index"
        else:
            # パスをファイル名に変換
            filename = path.replace('/', '-')
            filename = re.sub(r'[^\w\-_.]', '-', filename)
            filename = re.sub(r'-+', '-', filename)
            filename = filename.strip('-')
        
        # クエリパラメータがある場合はファイル名に追加
        if parsed.query:
            # クエリパラメータを安全なファイル名形式に変換
            query_safe = re.sub(r'[^\w\-_=&]', '-', parsed.query)
            query_safe = re.sub(r'-+', '-', query_safe)
            query_safe = query_safe.strip('-')
            filename += f"--{query_safe}"
        
        if not filename.endswith('.md'):
            filename += '.md'
        
        return filename
    
    def extract_links(self, content: str, base_url: str) -> List[str]:
        """
        コンテンツからリンクを抽出
        
        Args:
            content: HTMLコンテンツ
            base_url: ベースURL
            
        Returns:
            List[str]: 抽出されたリンクのリスト
        """
        links = []
        unique_links = set()  # 重複を防ぐためのセット
        
        # HTMLからリンクを抽出
        html_link_pattern = r'href=["\']([^"\']+)["\']'
        matches = re.findall(html_link_pattern, content)
        
        for match in matches:
            # JavaScriptリンクやメールリンクをスキップ
            if match.startswith(('javascript:', 'mailto:', '#')):
                continue
                
            full_url = urljoin(base_url, match)
            
            # フラグメント（#以降）を除去して重複チェック
            clean_url = full_url.split('#')[0]
            
            if (self.is_valid_url(clean_url) and 
                clean_url not in self.visited_urls and 
                clean_url not in unique_links):
                links.append(clean_url)
                unique_links.add(clean_url)
        
        return links
    
    async def crawl_page(self, url: str) -> tuple[str, List[str]]:
        """
        単一ページをクロール
        
        Args:
            url: クロールするURL
            
        Returns:
            tuple: (マークダウンコンテンツ, 抽出されたリンク)
        """
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=10,
            extraction_strategy=None,
            chunking_strategy=None,
            css_selector=self.css_selector,
            screenshot=False,
            user_agent="Mozilla/5.0 (compatible; WebCrawler/1.0)"
        )
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=crawler_config
                )
                
                if result.success:
                    markdown_content = result.markdown or ""
                    links = self.extract_links(result.html or "", url)
                    return markdown_content, links
                else:
                    print(f"Failed to crawl {url}: {result.error_message}")
                    return "", []
                    
        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")
            return "", []
    
    async def save_content(self, url: str, content: str):
        """
        コンテンツをファイルに保存
        
        Args:
            url: 元のURL
            content: マークダウンコンテンツ
        """
        filename = self.url_to_filename(url)
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {url}\n\n")
                f.write(content)
            print(f"Saved: {filepath}")
        except Exception as e:
            print(f"Error saving {url} to {filepath}: {str(e)}")
    
    async def crawl_recursive(self, url: str, depth: int = 0):
        """
        再帰的にWebサイトをクロール
        
        Args:
            url: クロールするURL
            depth: 現在の深度
        """
        if depth > self.max_depth or url in self.visited_urls:
            return
        
        if not self.is_valid_url(url):
            return
        
        print(f"Crawling (depth {depth}): {url}")
        self.visited_urls.add(url)
        
        # ページをクロール
        content, links = await self.crawl_page(url)
        
        if content:
            await self.save_content(url, content)
        
        # デバッグ情報
        print(f"Found {len(links)} links at depth {depth}")
        for i, link in enumerate(links[:5]):  # 最初の5つのリンクを表示
            print(f"  Link {i+1}: {link}")
        if len(links) > 5:
            print(f"  ... and {len(links) - 5} more links")
        
        # 見つかったリンクを再帰的にクロール
        if depth < self.max_depth:
            tasks = []
            for link in links:
                if link not in self.visited_urls:
                    tasks.append(self.crawl_recursive(link, depth + 1))
            
            if tasks:
                # 同時実行数を制限（最大10並行）
                batch_size = 10
                for i in range(0, len(tasks), batch_size):
                    batch = tasks[i:i + batch_size]
                    await asyncio.gather(*batch, return_exceptions=True)
    
    async def start_crawling(self):
        """
        クロールを開始
        """
        print(f"Starting crawl from: {self.start_url}")
        print(f"Output directory: {self.output_dir}")
        print(f"Max depth: {self.max_depth}")
        if self.css_selector:
            print(f"CSS Selector: {self.css_selector}")
        print(f"Allow query parameters: {self.allow_query}")
        print("-" * 50)
        
        await self.crawl_recursive(self.start_url)
        
        print("-" * 50)
        print(f"Crawling completed. Total pages crawled: {len(self.visited_urls)}")
        print(f"Files saved to: {self.output_dir}")


def main():
    """
    メイン関数
    """
    parser = argparse.ArgumentParser(
        description="Webサイトをクロールしてマークダウン形式で保存するPythonスクリプト"
    )
    
    parser.add_argument(
        "url",
        help="クロールを開始するURL"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="./docs",
        help="出力ディレクトリ (デフォルト: ./docs)"
    )
    
    parser.add_argument(
        "-d", "--max-depth",
        type=int,
        default=3,
        help="最大クロール深度 (デフォルト: 3)"
    )
    
    parser.add_argument(
        "-s", "--selector",
        default=None,
        help="指定したCSSセレクタのDOM要素のみを抽出"
    )
    
    parser.add_argument(
        "--allow-query",
        action="store_true",
        help="クエリパラメータ付きURLへのアクセスを許可する"
    )
    
    args = parser.parse_args()
    
    # nest-asyncioを適用（Jupyter環境など既存のイベントループがある場合に必要）
    nest_asyncio.apply()
    
    # クローラーを作成して実行
    crawler = WebCrawler(
        start_url=args.url,
        output_dir=args.output,
        max_depth=args.max_depth,
        css_selector=args.selector,
        allow_query=args.allow_query
    )
    
    try:
        asyncio.run(crawler.start_crawling())
    except KeyboardInterrupt:
        print("\nCrawling interrupted by user.")
    except Exception as e:
        print(f"Error during crawling: {str(e)}")


if __name__ == "__main__":
    main()
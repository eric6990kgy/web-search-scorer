"""
自動搜尋並評分網路資訊系統（優化版評分邏輯）
適合一般網路內容的實用評分系統
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from datetime import datetime
import time
from typing import List, Dict
import warnings
from urllib.parse import urlparse, urljoin
warnings.filterwarnings('ignore')


class WebContentScorer:
    """網路內容搜尋與評分系統（優化版）"""
    
    def __init__(self, serpapi_key=None):
        """初始化系統"""
        self.serpapi_key = "1af6b7da5496c681d01b3eeb8dda9635ee83817e66bfd355073f1596c3b366ff"
        self.results = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
        }
        
        # 黑名單網域（排除維基百科等）
        self.blacklist_domains = [
            'wikipedia.org',
            'wiki',
            'baike.baidu.com',
            '維基百科',
            'wikimedia'
        ]
        
    def search_google_serpapi(self, keyword: str, num_results: int = 10) -> List[Dict]:
        """使用 SerpAPI 搜尋 Google"""
        if not self.serpapi_key:
            print("⚠ 未提供 SerpAPI 密鑰，將使用備用搜尋方法")
            return self.search_duckduckgo(keyword, num_results)
        
        try:
            params = {
                "engine": "google",
                "q": keyword,
                "api_key": self.serpapi_key,
                "num": num_results * 2,  # 多抓一些，過濾後可能不足
                "hl": "zh-tw"
            }
            
            response = requests.get("https://serpapi.com/search", params=params, timeout=15)
            data = response.json()
            
            results = []
            for item in data.get("organic_results", []):
                url = item.get("link", "")
                
                # 檢查是否在黑名單中
                if any(blocked in url.lower() for blocked in self.blacklist_domains):
                    print(f"   ⊗ 已過濾黑名單網站: {url}")
                    continue
                
                results.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "snippet": item.get("snippet", ""),
                    "source": item.get("displayed_link", "")
                })
                
                if len(results) >= num_results:
                    break
            
            print(f"✓ 使用 SerpAPI 找到 {len(results)} 筆結果（已過濾黑名單）")
            return results
            
        except Exception as e:
            print(f"⚠ SerpAPI 搜尋失敗: {e}")
            return self.search_duckduckgo(keyword, num_results)
    
    def search_duckduckgo(self, keyword: str, num_results: int = 10) -> List[Dict]:
        """使用 DuckDuckGo 搜尋（免費方案）"""
        try:
            url = f"https://html.duckduckgo.com/html/?q={keyword}"
            response = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for result in soup.find_all('div', class_='result'):
                title_tag = result.find('a', class_='result__a')
                snippet_tag = result.find('a', class_='result__snippet')
                
                if title_tag and title_tag.get('href'):
                    url = title_tag.get('href')
                    if 'uddg=' in url:
                        url = url.split('uddg=')[1].split('&')[0]
                    
                    # 檢查黑名單
                    if any(blocked in url.lower() for blocked in self.blacklist_domains):
                        continue
                    
                    results.append({
                        "title": title_tag.get_text(strip=True),
                        "url": url,
                        "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                        "source": urlparse(url).netloc
                    })
                    
                    if len(results) >= num_results:
                        break
            
            print(f"✓ 使用 DuckDuckGo 找到 {len(results)} 筆結果")
            return results
            
        except Exception as e:
            print(f"❌ 搜尋失敗: {e}")
            return []
    
    def extract_content_advanced(self, url: str) -> Dict:
        """進階內容抓取方法"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取標題
            title = ""
            title_candidates = [
                soup.find('h1'),
                soup.find('title'),
                soup.find('meta', property='og:title'),
                soup.find('meta', attrs={'name': 'title'})
            ]
            for candidate in title_candidates:
                if candidate:
                    if candidate.name == 'meta':
                        title = candidate.get('content', '')
                    else:
                        title = candidate.get_text(strip=True)
                    if title:
                        break
            
            # 移除不需要的元素
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 
                           'aside', 'iframe', 'noscript', 'form']):
                tag.decompose()
            
            # 找主要內容
            main_content = None
            content_selectors = [
                'article',
                '[role="main"]',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content',
                'main',
                '#content',
                '#main'
            ]
            
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            if not main_content:
                main_content = soup.find('body')
            
            if main_content:
                paragraphs = main_content.find_all(['p', 'div', 'span', 'li'])
                texts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if 20 < len(text) < 1000:
                        texts.append(text)
                
                content = ' '.join(texts)
                content = re.sub(r'\s+', ' ', content).strip()
                
                # 提取發布日期
                publish_date = None
                date_meta = soup.find('meta', property='article:published_time')
                if not date_meta:
                    date_meta = soup.find('meta', attrs={'name': 'date'})
                if date_meta:
                    publish_date = date_meta.get('content', '')
                
                return {
                    "content": content,
                    "title": title,
                    "publish_date": publish_date,
                    "method": "beautifulsoup_advanced",
                    "success": True
                }
            
            return {
                "content": "",
                "title": title,
                "publish_date": None,
                "method": "beautifulsoup_advanced",
                "success": False,
                "error": "未找到主要內容"
            }
            
        except requests.exceptions.Timeout:
            return {
                "content": "",
                "title": "",
                "publish_date": None,
                "method": "failed",
                "success": False,
                "error": "請求超時"
            }
        except Exception as e:
            return {
                "content": "",
                "title": "",
                "publish_date": None,
                "method": "failed",
                "success": False,
                "error": str(e)
            }
    
    def calculate_relevance_score(self, keyword: str, content: str, title: str, snippet: str = "") -> float:
        """
        計算相關性評分（優化版）
        
        評分標準：
        - TF-IDF 語義相似度：40分
        - 標題完全匹配：25分
        - 標題部分匹配：15分
        - 關鍵詞頻率加分：最多20分
        - 關鍵詞位置加分（前段）：15分
        - 小標題包含關鍵詞：10分
        """
        if not content and not title:
            return 0.0
        
        try:
            # 準備文字（標題權重更高）
            weighted_content = f"{title} {title} {title} {snippet} {content}"
            keywords = keyword.split()
            
            # TF-IDF 相似度（40分）
            vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b\w+\b')
            tfidf_matrix = vectorizer.fit_transform([keyword, weighted_content])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            base_score = similarity * 40
            
            content_lower = content.lower()
            title_lower = title.lower()
            keyword_lower = keyword.lower()
            
            # 標題匹配加分（25分或15分）
            if keyword_lower in title_lower:
                base_score += 25
            elif any(kw.lower() in title_lower for kw in keywords if len(kw) > 2):
                base_score += 15
            
            # 關鍵詞頻率加分（最多20分）
            keyword_count = content_lower.count(keyword_lower)
            for kw in keywords:
                if len(kw) > 2:
                    keyword_count += content_lower.count(kw.lower()) * 0.5
            
            frequency_bonus = min(keyword_count * 2, 20)
            base_score += frequency_bonus
            
            # 關鍵詞位置加分（15分）
            # 前500字出現：+15分
            # 前1000字出現：+10分
            # 前2000字出現：+5分
            if len(content_lower) > 0:
                if content_lower[:500].count(keyword_lower) > 0:
                    base_score += 15
                elif content_lower[:1000].count(keyword_lower) > 0:
                    base_score += 10
                elif content_lower[:2000].count(keyword_lower) > 0:
                    base_score += 5
            
            return min(base_score, 100)
            
        except Exception as e:
            print(f"   ⚠ 計算相關性時出錯: {e}")
            return 0.0
    
    def calculate_quality_score(self, content: str, url: str, title: str, publish_date: str = None) -> float:
        """
        計算內容品質評分（優化版 - 適合一般網路內容）
        
        評分標準：
        - 內容深度（長度+結構）：30分
        - 內容豐富度（數字、列表、引用）：25分
        - 網站類型與信任度：20分
        - 時效性（發布日期）：15分
        - 可讀性（段落、標題）：10分
        """
        score = 0
        
        # 1. 內容深度評分（30分）
        content_length = len(content)
        sentences = re.split(r'[.!?。！？]', content)
        valid_sentences = [s for s in sentences if len(s.strip()) > 10]
        
        # 長度評分（15分）
        if content_length > 3000:
            score += 15
        elif content_length > 2000:
            score += 12
        elif content_length > 1000:
            score += 9
        elif content_length > 500:
            score += 6
        elif content_length > 200:
            score += 3
        
        # 結構評分（15分）
        if len(valid_sentences) > 30:
            score += 15
        elif len(valid_sentences) > 20:
            score += 12
        elif len(valid_sentences) > 10:
            score += 8
        elif len(valid_sentences) > 5:
            score += 4
        
        # 2. 內容豐富度評分（25分）
        # 包含數字/數據（8分）
        numbers_count = len(re.findall(r'\d+', content))
        if numbers_count > 10:
            score += 8
        elif numbers_count > 5:
            score += 5
        elif numbers_count > 0:
            score += 3
        
        # 包含引用或引號（7分）
        has_quotes = bool(re.search(r'["""\'\'「」『』]', content))
        if has_quotes:
            score += 7
        
        # 標點符號豐富度（表示結構化內容）（10分）
        punctuation_count = len(re.findall(r'[,，、;；:：]', content))
        if punctuation_count > 20:
            score += 10
        elif punctuation_count > 10:
            score += 6
        elif punctuation_count > 5:
            score += 3
        
        # 3. 網站類型與信任度評分（20分）
        url_lower = url.lower()
        
        # 新聞媒體網站（15分）
        news_domains = [
            'news', 'bbc', 'cnn', 'nytimes', 'reuters', 'bloomberg',
            'guardian', 'washingtonpost', 'forbes', 'techcrunch',
            'theverge', 'wired', 'engadget', 'cnet'
        ]
        
        # 專業網站（12分）
        professional_domains = [
            '.gov', '.edu', '.org',
            'medium', 'github', 'stackoverflow',
            'arxiv', 'scholar', 'research'
        ]
        
        # 一般可信網站（8分）
        trusted_domains = [
            'https://',  # 至少有 HTTPS
        ]
        
        if any(domain in url_lower for domain in news_domains):
            score += 15
        elif any(domain in url_lower for domain in professional_domains):
            score += 12
        elif url.startswith('https://'):
            score += 8
        else:
            score += 3  # 基本分
        
        # 4. 時效性評分（15分）
        if publish_date:
            try:
                # 嘗試解析日期
                date_formats = [
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d',
                    '%Y/%m/%d'
                ]
                
                pub_date = None
                for fmt in date_formats:
                    try:
                        pub_date = datetime.strptime(publish_date[:19], fmt)
                        break
                    except:
                        continue
                
                if pub_date:
                    days_ago = (datetime.now() - pub_date).days
                    
                    if days_ago <= 7:
                        score += 15  # 一週內
                    elif days_ago <= 30:
                        score += 12  # 一個月內
                    elif days_ago <= 90:
                        score += 9   # 三個月內
                    elif days_ago <= 180:
                        score += 6   # 半年內
                    elif days_ago <= 365:
                        score += 3   # 一年內
                    else:
                        score += 1   # 超過一年
            except:
                score += 5  # 有日期但解析失敗，給中性分
        else:
            score += 5  # 無日期資訊，給中性分
        
        # 5. 可讀性評分（10分）
        # 標題品質（5分）
        title_length = len(title)
        if 10 < title_length < 100:
            score += 5
        elif 5 < title_length < 150:
            score += 3
        
        # 無垃圾內容（5分）
        spam_keywords = [
            '點擊這裡', '立即購買', '廣告', '推廣', 'AD', '贊助',
            '限時優惠', '馬上搶購', '特價'
        ]
        spam_count = sum(1 for kw in spam_keywords if kw in content)
        score += max(5 - spam_count * 2, 0)
        
        return min(score, 100)
    
    def calculate_final_score(self, relevance: float, quality: float) -> float:
        """
        計算最終綜合評分
        
        權重分配：
        - 相關性：60%（找到對的內容最重要）
        - 品質：40%（內容要有價值）
        """
        final_score = (relevance * 0.60) + (quality * 0.40)
        return round(final_score, 2)
    
    def run(self, keyword: str, num_results: int = 10) -> pd.DataFrame:
        """執行完整的搜尋、抓取和評分流程"""
        print(f"\n{'='*70}")
        print(f"🔍 開始搜尋關鍵詞: 「{keyword}」")
        print(f"{'='*70}\n")
        
        # 步驟 1: 搜尋
        print("📡 步驟 1/3: 正在搜尋...")
        search_results = self.search_google_serpapi(keyword, num_results)
        
        if not search_results:
            print("❌ 搜尋失敗，未找到任何結果")
            return pd.DataFrame()
        
        # 步驟 2: 抓取內容
        print(f"\n📥 步驟 2/3: 正在抓取 {len(search_results)} 個網頁內容...")
        self.results = []
        
        for i, result in enumerate(search_results, 1):
            print(f"   [{i}/{len(search_results)}] {result['title'][:60]}...")
            
            # 抓取內容
            content_data = self.extract_content_advanced(result['url'])
            
            if not content_data['title']:
                content_data['title'] = result['title']
            
            # 計算評分
            if content_data['content'] and len(content_data['content']) > 100:
                relevance_score = self.calculate_relevance_score(
                    keyword, 
                    content_data['content'], 
                    content_data['title'],
                    result['snippet']
                )
                quality_score = self.calculate_quality_score(
                    content_data['content'],
                    result['url'],
                    content_data['title'],
                    content_data.get('publish_date')
                )
                final_score = self.calculate_final_score(relevance_score, quality_score)
                status = "✓"
            else:
                relevance_score = 0
                quality_score = 0
                final_score = 0
                status = "✗"
            
            print(f"       {status} 综合评分: {final_score:.1f} (相关性: {relevance_score:.1f}, 品质: {quality_score:.1f})")
            
            # 保存結果
            self.results.append({
                '排名': i,
                '标题': content_data['title'][:100],
                '来源': result['source'],
                '网址': result['url'],
                '相关性评分': round(relevance_score, 1),
                '品质评分': round(quality_score, 1),
                '综合评分': final_score,
                '内容长度': len(content_data['content']),
                '发布日期': content_data.get('publish_date', 'N/A') or 'N/A',
                '摘要': result['snippet'][:150] + '...' if len(result['snippet']) > 150 else result['snippet'],
                '抓取状态': '成功' if content_data.get('success') else '失敗'
            })
            
            time.sleep(0.8)
        
        # 步驟 3: 排序和輸出
        print(f"\n📊 步驟 3/3: 正在評分和排序...")
        df = pd.DataFrame(self.results)
        
        df = df.sort_values('综合评分', ascending=False).reset_index(drop=True)
        df['排名'] = range(1, len(df) + 1)
        
        success_count = len(df[df['抓取状态'] == '成功'])
        avg_score = df['综合评分'].mean()
        
        print(f"\n✅ 完成！")
        print(f"   • 共處理 {len(df)} 筆資料")
        print(f"   • 成功抓取 {success_count} 筆")
        print(f"   • 平均評分 {avg_score:.1f}")
        print()
        
        return df
    
    def export_results(self, df: pd.DataFrame, filename: str = None):
        """匯出結果到檔案"""
        if df.empty:
            print("⚠ 沒有結果可以匯出")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"搜尋結果_{timestamp}.xlsx"
        
        try:
            df.to_excel(filename, index=False, engine='openpyxl')
            print(f"✓ 結果已匯出到: {filename}")
        except ImportError:
            csv_filename = filename.replace('.xlsx', '.csv')
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"✓ 結果已匯出到: {csv_filename}")
        except Exception as e:
            csv_filename = filename.replace('.xlsx', '.csv')
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"✓ 結果已匯出到: {csv_filename}")


# ============================================================================
# 使用範例
# ============================================================================

def main():
    """主函數"""
    
    print("="*70)
    print("  網路內容自動搜尋與評分系統（優化版）")
    print("="*70)
    
    scorer = WebContentScorer()
    
    keyword = input("\n請輸入搜尋關鍵詞（直接按 Enter 使用預設「人工智慧」）: ").strip()
    if not keyword:
        keyword = "人工智慧"
    
    num = input("要搜尋幾筆資料？(預設 10): ").strip()
    num_results = int(num) if num.isdigit() else 10
    
    results_df = scorer.run(keyword, num_results=num_results)
    
    if not results_df.empty:
        print("\n" + "="*70)
        print("📋 搜尋結果匯總")
        print("="*70 + "\n")
        
        display_df = results_df[['排名', '标题', '综合评分', '相关性评分', '品质评分', '来源']].copy()
        display_df['标题'] = display_df['标题'].str[:50]
        
        pd.set_option('display.max_colwidth', 50)
        pd.set_option('display.width', 150)
        print(display_df.to_string(index=False))
        
        print("\n\n" + "="*70)
        print("🏆 TOP 3 最有價值的資料")
        print("="*70 + "\n")
        
        for i in range(min(3, len(results_df))):
            row = results_df.iloc[i]
            print(f"【第 {i+1} 名】综合评分: {row['综合评分']}")
            print(f"标题: {row['标题']}")
            print(f"来源: {row['来源']}")
            print(f"评分详情: 相关性 {row['相关性评分']:.1f} | 品质 {row['品质评分']:.1f}")
            print(f"网址: {row['网址']}")
            print(f"摘要: {row['摘要'][:120]}...")
            print("-" * 70 + "\n")
        
        export = input("是否匯出結果到檔案？(y/n): ").strip().lower()
        if export == 'y':
            scorer.export_results(results_df)
        
        return results_df
    else:
        print("❌ 未能獲取有效結果")
        return None


if __name__ == "__main__":
    results = main()
    
    print("\n" + "="*70)
    print("程式執行完畢！")
    print("="*70)

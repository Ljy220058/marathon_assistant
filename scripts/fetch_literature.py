"""批量搜索和下载马拉松助手知识库缺失文献。
使用 PubMed E-utilities + arXiv API 搜索，优先获取免费全文。
"""
import json, os, re, time, sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote, urlencode
from urllib.error import HTTPError

PROXY = "http://127.0.0.1:7890"
OUTPUT_DIR = Path("data/literature_fetched")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def fetch_json(url: str, max_retries: int = 3) -> dict:
    """通过代理请求 JSON。"""
    req = Request(url)
    req.set_proxy(PROXY, "http")
    for attempt in range(max_retries):
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

def pubmed_search(query: str, retmax: int = 5) -> list[str]:
    """PubMed 搜索，返回 PMID 列表。"""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(retmax),
        "retmode": "json",
        "sort": "relevance",
    }
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{urlencode(params)}"
    result = fetch_json(url)
    return result.get("esearchresult", {}).get("idlist", [])

def pubmed_fetch(pmids: list[str]) -> list[dict]:
    """批量获取 PubMed 摘要和元数据。"""
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
        "rettype": "abstract",
    }
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{urlencode(params)}"
    result = fetch_json(url)
    papers = []
    for pmid in pmids:
        info = result.get("result", {}).get(pmid, {})
        if info and "error" not in info:
            papers.append({
                "pmid": pmid,
                "title": info.get("title", ""),
                "authors": [a.get("name","") for a in info.get("authors",[])],
                "source": info.get("source", ""),
                "pubdate": info.get("pubdate", ""),
                "doi": info.get("elocationid", "").replace("doi: ", ""),
                "pmc": "",
            })
    return papers

def arxiv_search(query: str, max_results: int = 3) -> list[dict]:
    """arXiv API 搜索。"""
    params = {
        "search_query": query,
        "max_results": str(max_results),
        "sortBy": "relevance",
    }
    url = f"http://export.arxiv.org/api/query?{urlencode(params)}"
    req = Request(url)
    req.set_proxy(PROXY, "http")
    try:
        with urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
    except Exception as e:
        print(f"  arXiv error: {e}")
        return []

    papers = []
    entries = re.split(r"<entry>|</entry>", text)
    for i in range(1, len(entries), 2):
        entry = entries[i]
        title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        arxiv_id = re.search(r"<id>.*?/(.*?)</id>", entry)
        summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        papers.append({
            "title": title.group(1).strip() if title else "",
            "arxiv_id": arxiv_id.group(1).strip() if arxiv_id else "",
            "abstract": summary.group(1).strip()[:500] if summary else "",
            "url": f"https://arxiv.org/pdf/{arxiv_id.group(1).strip()}" if arxiv_id else "",
        })
    return papers

# ============================================================
# 文献搜索清单：P0 + P1 共计 14 个主题
# ============================================================
SEARCHES = [
    # P0: 评测命中的缺口
    ("omega3", "omega-3 fatty acid DHA EPA supplementation athletes endurance performance review"),
    ("reds", "IOC consensus statement RED-S relative energy deficiency in sport 2018 Mountjoy"),
    # P1: 损伤 CPG
    ("itbs_cpg", "iliotibial band syndrome runners treatment clinical practice guideline review"),
    ("achilles_cpg", "Achilles tendinopathy management runners clinical practice guideline Malliaras"),
    ("stress_fx", "stress fracture management athletes runners bone stress injury review"),
    # P1: 热安全
    ("heat_consensus", "exertional heat stroke heat acclimation athletes consensus recommendations Racinais"),
    ("precooling", "precooling cooling strategies endurance performance athletes review Bongers"),
    # P1: 生物力学
    ("cadence", "running cadence step rate injury biomechanics Heiderscheit review"),
    ("running_form", "running biomechanics gait foot strike technique performance review"),
    # P1: 补水电解质
    ("hydration", "ACSM position stand hydration fluid replacement exercise athletes Sawka"),
    ("hyponatremia", "exercise-associated hyponatremia consensus guidelines Hew-Butler"),
    # P1: 咖啡因/补剂
    ("caffeine", "caffeine supplementation endurance exercise performance meta-analysis systematic review Guest"),
    ("supplements_evidence", "evidence-based dietary supplements athletes IOC consensus review Peeling"),
    # P1: 跑步经济性（力量训练改善）
    ("running_economy_strength", "strength training heavy resistance running economy endurance runners review"),
]

def search_one(tag: str, query: str):
    """搜索一个主题，返回找到的文献列表。"""
    print(f"  [{tag}] {query[:60]}...", end=" ", flush=True)
    papers = []
    try:
        pmids = pubmed_search(query, retmax=3)
        if pmids:
            papers = pubmed_fetch(pmids[:3])
    except Exception as e:
        print(f"PubMed: {e}", end=" ")
    if not papers:
        try:
            papers = arxiv_search(query, max_results=2)
        except Exception:
            pass
    print(f"-> {len(papers)} papers")
    return papers

def main():
    # 输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / "literature_search_report.json"

    # 检查缓存
    if report_path.exists():
        print(f"Loading cached results from {report_path}")
        with open(report_path, encoding="utf-8") as f:
            all_results = json.load(f)
    else:
        all_results = {}
        for tag, query in SEARCHES:
            time.sleep(0.5)  # PubMed rate limit: ~3 req/sec without API key
            try:
                papers = search_one(tag, query)
                all_results[tag] = {
                    "query": query,
                    "papers": papers,
                }
            except Exception as e:
                print(f"    FAILED: {e}")
                all_results[tag] = {"query": query, "papers": [], "error": str(e)}

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

    # 汇总
    total = sum(len(v.get("papers", [])) for v in all_results.values())
    print(f"\n=== Search Complete: {total} papers across {len(all_results)} topics ===")
    for tag, info in all_results.items():
        papers = info.get("papers", [])
        print(f"\n--- {tag} ({len(papers)} papers) ---")
        for p in papers:
            title = p.get("title", "")[:100]
            src = p.get("source", "") or p.get("arxiv_id", "")
            doi = p.get("doi", "") or p.get("url", "")
            print(f"  {title}")
            print(f"    src: {src} | doi: {doi}")

    return all_results

if __name__ == "__main__":
    main()

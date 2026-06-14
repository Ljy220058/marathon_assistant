"""Retrieval benchmark: 5 methods compared"""
import sys, io, asyncio, json, aiohttp, re, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0,'apps/backend/src')
from marathon_qa_assistant.services.vector_store import load_chunks
chunks = load_chunks(Path('data/vector_kb/v2/chunks.jsonl'))

from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
emb = OllamaEmbeddings(model='nomic-embed-text', base_url='http://localhost:11434')
faiss = FAISS.load_local('data/vector_kb/v2/faiss_db', emb, allow_dangerous_deserialization=True)

class BM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1, self.b, self.N = k1, b, len(corpus)
        self.docs = corpus
        self.avgdl = sum(len(d) for d in corpus) / max(self.N, 1)
        self.df = defaultdict(int)
        for doc in corpus:
            for w in set(doc): self.df[w] += 1
    def idf(self, w): return math.log(1+(self.N-self.df.get(w,0)+0.5)/(self.df.get(w,0)+0.5))
    def score(self, q, doc):
        dl, s = len(doc), 0.0
        tf = Counter(doc)
        for t in q:
            if t in self.df:
                s += max(self.idf(t),0.01)*tf.get(t,0)*(self.k1+1)/(tf.get(t,0)+self.k1*(1-self.b+self.b*dl/self.avgdl))
        return s

def tok(text):
    return [t.lower() for t in re.findall(r'[a-zA-Z]+|\w+', text) if len(t)>=2]

bm25 = BM25([tok(c['text']) for c in chunks], k1=1.5, b=0.75)

def rrf(lists, k=60):
    scores = defaultdict(float)
    for lst in lists:
        for rank, (idx, _) in enumerate(lst):
            scores[idx] += 1.0/(k+rank+1)
    return sorted(scores.items(), key=lambda x:-x[1])

async def translate(q):
    async with aiohttp.ClientSession() as s:
        p = {'model':'qwen2.5:latest','prompt':'Translate to concise English keywords for academic search:\nChinese: '+q+'\nEnglish:','stream':False,'options':{'temperature':0.1,'num_predict':60}}
        async with s.post('http://localhost:11434/api/generate',json=p,timeout=aiohttp.ClientTimeout(10)) as r:
            return (await r.json()).get('response','').strip()

async def rerank(q, docs, n=8):
    if len(docs)<=n: return docs
    txt = '\n---\n'.join(['['+str(i)+'] '+d['text'][:200] for i,d in enumerate(docs)])
    p = {'model':'qwen2.5:latest','prompt':'Query: '+q+'\nRank these by relevance:\n'+txt+'\nReturn JSON: [[idx,score],...]','stream':False,'options':{'temperature':0.1,'num_predict':200}}
    async with aiohttp.ClientSession() as s:
        async with s.post('http://localhost:11434/api/generate',json=p,timeout=aiohttp.ClientTimeout(30)) as r:
            d = await r.json()
            resp = d.get('response','')
            try:
                st=resp.find('['); en=resp.rfind(']')+1
                if 0<=st<en: return [docs[int(p[0])] for p in json.loads(resp[st:en]) if 0<=int(p[0])<len(docs)][:n]
            except: pass
    return docs[:n]

async def search(name, query, en_query):
    # vec_zh uses Chinese query, all others use English translation
    actual_q = query if name == 'vec_zh' else en_query
    if name in ('vec_zh','vec_en'):
        docs = faiss.similarity_search(actual_q, k=8)
        return Counter(d.metadata.get('expert_domain','?') for d in docs)
    elif name == 'bm25':
        qt = tok(actual_q)
        bs = sorted([(i,bm25.score(qt,bm25.docs[i])) for i in range(len(chunks))], key=lambda x:-x[1])
        return Counter(chunks[i].get('expert_domain','?') for i,_ in bs[:8])
    elif name in ('rrf','rerank'):
        vd = faiss.similarity_search(actual_q, k=15)
        vi = []
        for d in vd:
            cid = d.metadata.get('chunk_id','')
            for i,c in enumerate(chunks):
                if c.get('chunk_id')==cid: vi.append((i,0)); break
        qt = tok(actual_q)
        bs = sorted([(i,bm25.score(qt,bm25.docs[i])) for i in range(len(chunks))], key=lambda x:-x[1])
        fused = rrf([vi[:15], bs[:15]])
        if name == 'rrf':
            return Counter(chunks[i].get('expert_domain','?') for i,_ in fused[:8])
        else:
            cands = [chunks[i] for i,_ in fused[:15]]
            reranked = await rerank(en_query, cands)
            return Counter(h.get('expert_domain','?') for h in reranked)

async def main():
    # 真实测试：中文 query → CN-vec, 翻译后英文 → EN-vec
    chinese_qs = [
        ('膝盖外侧疼还能跑步吗', 'rehab_safety'),
        ('跟腱炎怎么恢复', 'rehab_safety'),
        ('肌酸补剂有用吗', 'nutrition'),
        ('赛前碳水怎么吃', 'nutrition'),
        ('热天比赛怎么准备', 'race_strategy'),
    ]
    methods = ['vec_zh','vec_en','bm25','rrf','rerank']
    labels = {'vec_zh':'CN-vec','vec_en':'EN-vec','bm25':'BM25','rrf':'RRF','rerank':'Rerank'}

    en_map = {}
    for cq, domain in chinese_qs:
        en_map[cq] = await translate(cq)
        print('TR:', cq, '->', en_map[cq])

    print()
    header = 'Method'.rjust(10)
    for cq,_ in chinese_qs: header += '  ' + cq[:6].rjust(6)
    header += '  Avg'
    print(header)
    print('-'*70)

    totals = {m:0 for m in methods}
    for method in methods:
        row = labels[method].rjust(10)
        for cq, domain in chinese_qs:
            en_q = en_map[cq]
            # CN-vec: 用中文原始query; 其他: 用英文翻译
            search_q = cq if method == 'vec_zh' else en_q
            d = await search(method, search_q, en_q)
            target = d.get(domain,0)
            t = sum(d.values())
            pct = target*100//t if t else 0
            totals[method] += pct
            row += '  %d/%d%2d' % (target, t, pct)
        avg = totals[method]//len(chinese_qs)
        row += '   %2d' % avg
        print(row)

asyncio.run(main())

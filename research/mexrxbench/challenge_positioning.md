# Challenge Positioning: RuleML+RR 2026 Rule Challenge

## 鎶曠绫诲瀷閿佸畾

鏈枃瀹氫綅涓?**Challenge Proposal + Challenge Solution** 鐨勬贩鍚堝瀷 Rule Challenge 璁烘枃銆?

涓€鍙ヨ瘽鎶曠涓诲紶锛?

> We define evidence-bounded exercise prescription as a rule-oriented challenge and provide M-EXRxBench plus a rule-governed multi-agent RAG prototype as a reference solution.

Current default artifact: M-EXRxBench v0.4 with 500 synthetic cases. Historical v0.3/v0.2 benchmark files are retained only as archive snapshots and are not default reviewer runner inputs.

涓枃涓诲紶锛?

> 鏈枃涓嶆槸鎻愪氦涓€涓細鐢熸垚椹媺鏉捐鍒掔殑 LLM 搴旂敤锛岃€屾槸鎻愬嚭涓€涓珮椋庨櫓杩愬姩澶勬柟鐢熸垚鐨勮鍒欐不鐞嗘寫鎴橈細鐢?`M-EXRxBench` 瀹氫箟浠诲姟銆佹渚嬪拰楠屾敹鎸囨爣锛屽苟鐢?Rule-Governed M-EXRx Agent 灞曠ず鍙傝€冭В娉曘€?

## 涓轰粈涔堟槸 Rule Challenge

RuleML+RR 2026 Rule Challenge 瀹樻柟鎺ュ彈涓ょ被璁烘枃锛?

- **Challenge Proposal**锛氬畾涔夐渶瑕?rule-based reasoning 鐨勬柊闂銆乥enchmark銆乨ataset銆乻uccess criteria銆?
- **Challenge Solution**锛氭彁渚涚郴缁熸€ц兘璇佹嵁銆乥enchmark銆佸姣斿疄楠屻€佸伐鍏锋垨鐪熷疄搴旂敤妗堜緥銆?

鎴戜滑鐨勫伐浣滃悓鏃舵弧瓒充袱鑰咃細

| 缁村害 | 鏈枃瀵瑰簲鐗?| 璁烘枃鍙欎簨 |
|---|---|---|
| Challenge Proposal | `M-EXRxBench`銆乧ase schema銆乬old labels銆乪valuation metrics | 鎶婅繍鍔ㄥ鏂圭敓鎴愬畾涔変负 evidence-bounded, safety-sensitive, rule-checkable task |
| Challenge Solution | Rule-Governed M-EXRx Agent銆丷iskGate銆丒videnceGate銆丳rescriptionContract銆丷ule Auditor | 灞曠ず涓€涓鍒欏眰浣滀负 reasoner of record 鐨?reference implementation |
| Evaluation Infrastructure | runner銆乼race/result schema銆乮ndependent evaluator銆乥aseline protocol | 璁?challenge 鍙互琚鐜般€佹瘮杈冨拰鎵╁睍 |
| Open Resources | benchmark files銆乺ule files銆乻ample traces銆乤rtifact checklist | 婊¤冻 Rule Challenge 鐨?open science / resources 瑕佹眰 |

## 璁烘枃杈圭晫

鏈枃鍙０绉帮細

- 绯荤粺鏄繍鍔ㄨ缁冨喅绛栨敮鎸?artifact锛屼笉鏄尰瀛﹁瘖鏂郴缁熴€?
- 绯荤粺浠ュ崐椹缁冧綔涓?case study锛屼絾鏍稿績浠诲姟鏄?evidence-bounded exercise prescription銆?
- LLM 鍙敤浜庡€欓€夌敓鎴愬拰瑙ｉ噴缁勭粐锛涙渶缁堝悎娉曟€х敱瑙勫垯灞傘€佽瘉鎹眰銆佸鏂瑰悎绾﹀拰瀹¤鍣ㄥ喅瀹氥€?
- 瀵归珮椋庨櫓鎴栬瘉鎹笉瓒冲満鏅紝绯荤粺蹇呴』闄嶇骇銆佹緞娓呫€侀儴鍒嗗洖绛旀垨鎷掔粷锛岃€屼笉鏄嚜鐢辩敓鎴愯缁冨鏂广€?

鏈枃涓嶅０绉帮細

- 宸茬粡瀹屾垚涓村簥楠岃瘉銆?
- 鍙浛浠ｅ尰鐢熴€佸悍澶嶅笀銆佽繍鍔ㄥ尰瀛︿笓瀹舵垨鐜板満鏁欑粌銆?
- 瀵规墍鏈変汉缇ゃ€佺柧鐥呫€佺幆澧冨拰鍙┛鎴磋澶囨暟鎹潎鍙潬銆?
- `M-EXRxBench` 鏄湡瀹炴偅鑰呮暟鎹泦銆傚綋鍓嶇増鏈簲澹版槑涓?expert-informed synthetic benchmark銆?

## 涓庢櫘閫?LLM / RAG / Multi-Agent 绯荤粺鐨勫尯鍒?

| 鏅€氳矾绾?| 椋庨櫓 | 鏈枃璺嚎 |
|---|---|---|
| LLM 鐩存帴鐢熸垚璁粌璁″垝 | 瀹规槗杩囧害鑷俊銆佸拷鐣ョ孩鏃椼€佺紪閫犱緷鎹?| RiskGate 鍏堣鍐宠兘鍚﹁繘鍏ュ鏂硅矾寰?|
| RAG 妫€绱㈠埌璧勬枡鍚庣敓鎴愬缓璁?| 妫€绱㈢浉鍏充笉绛変簬澶勬柟鍚堟牸 | EvidenceGate 鍐冲畾鍝簺 evidence layer 鏈夊鏂硅祫鏍?|
| 澶氫釜涓撳鑷敱璁ㄨ鍚庣敱鏁欑粌鎬荤粨 | 瑙掕壊澶氫絾鏉冭矗涓嶆竻锛屽鏄撲簰鐩歌儗涔?| 涓変釜甯搁┗ agent + 鏉′欢涓撳 + Rule Auditor 鍚﹀喅鏉?|
| 鍙戠幇闂鍚庤 LLM 閲嶅啓 | repair 鍙兘缁曡繃瀹夊叏杈圭晫 | bounded repair 鍙兘鍒犻櫎銆侀檷绾с€佹浛鎹负宸叉壒鍑嗗姩浣滐紝骞堕噸鏂板璁?|
| 杈撳嚭鑷劧璇█璁″垝 | 闅句互澶嶆煡鍜屾瘮杈?| 杈撳嚭 FinalPlan + Trace + AuditResult |

## 鏈€浣庢姇绋块棴鐜?

鏈€浣庡彲鎶曠増鏈繀椤诲舰鎴愪互涓嬮棴鐜細

```text
Challenge definition
-> M-EXRxBench v0.4 / 500 synthetic cases
-> system-visible / evaluator-only gold split
-> rule-governed reference solution
-> independent evaluator
-> baseline comparison
-> trace examples
-> CEURART 8-15 page paper
-> artifact checklist and resource release plan
```

濡傛灉 500-case benchmark銆佹棤娉勬紡 evaluator 鎴?fail-closed regression 鏈畬鎴愶紝璁烘枃鍙兘浣滀负 internal draft锛屼笉搴斿０绉拌揪鍒?Rule Challenge 鎶曠绾у埆銆?

# threads-bench

給 Claude Code 跟 Claude 用的 Threads 對標 skill。

我自己經營 Threads 帳號時最常卡的一件事：題目想不出來，或是寫了一篇覺得應該會中，結果沒中。這兩件事靠自己的歷史資料都解不了，因為你沒寫過的題目，資料裡永遠不會出現。

所以做了這個。你丟一個題目給它，或丟一篇貼文連結，它會開瀏覽器去 Threads 上看同一題別人怎麼寫、效果怎樣，然後整理成三份東西：

| 檔案 | 內容 | 什麼時候看 |
|---|---|---|
| `benchmarks/opportunities.md` | 題材機會清單。哪些題有人問沒人答、哪些題別人寫爆了你還沒寫 | 想不到要寫什麼時，打 `/threads-bench topics` 幫你挑 |
| `benchmarks/playbook.md` | 打法手冊。形式、發文時間、手法，不含題材 | 動筆之前 |
| `benchmarks/reports/<日期>-<主題>.md` | 完整報告。每則提到的貼文都附原文連結，點得回去查 | 想知道它為什麼這樣建議 |

它學的是別人**做了什麼事**，形式、切角、檔期、有沒有配圖這種。它不學別人**怎麼寫**，句式、用字一律不碰。文字照抄會被演算法當成重複內容，這個 skill 有一條紅線專門擋這件事。

---

## 它是怎麼運作的

```
你：「中元節（任何一個你想研究的主題）」  或  貼一個 Threads 連結
        │
        ▼
① 定義主題 ─────────────── 先問你：核心詞是什麼、相關場所／載體是什麼、要排除什麼
        │                    例：核心詞「中元節、普渡」，場所詞「基隆中元祭、家樂福普渡」
        │                    你確認過才往下，避免撈到一堆不相關的
        ▼
② 開瀏覽器抓資料 ────────── 只在 threads.com 站內
        │                    關鍵字搜尋 → 長尾複合詞 → tag 頁
        │                    抓 15 到 25 則，每則都要拿到貼文的永久連結
        ▼
③ 算相對表現 ────────────── 對每個帳號開 profile 看粉絲數、近 5 篇平均讚數
        │                    算「這篇 ÷ 他自己的平均」
        │                    → 145 粉絲的帳號拿到 506 讚，那是題目對，不是帳號大
        ▼
④ 歸類成機會 ────────────── 空白型（有人問沒人答）
        │                    熱區型（別人寫爆了，你還沒寫）
        │                    半成品型（別人只答了一半）
        │                    每個機會標信心：3 則以上佐證才算 Usable
        ▼
⑤ 跟上次結果比對 ────────── 同一則貼文再出現就更新數字
        │                    結論互相矛盾就兩邊都留，不自動裁決
        ▼
⑥ 守門 ──────────────────── 每個建議過演算法紅線（不能建議「留言+1」這類互動誘導）
        │                    被淘汰的也寫進報告，不默默刪
        ▼
⑦ 寫檔 ──────────────────── opportunities.md / playbook.md / reports/ / index.jsonl
        │                    全部在 benchmarks/ 底下，不碰你其他檔案
        ▼
⑧ 報告 ──────────────────── 第一段：這次 bench 的整理
                             第二段：這次的 Top 5 主題
```

③ 那步是我覺得最有用的地方。一個 145 粉絲的帳號，平常一篇 2 到 24 讚，某篇「怎麼拜」的教學文拿到 506 讚 354 分享。看絕對數字你會覺得普通，除以他自己的平均才知道那是題目對。

不用事先準備任何資料。它不看你自己的貼文，不看你的帳號調性，只看別人之間誰的打法效率高。建議合不合你的帳號、這題你寫過沒有，你自己判斷，你比它清楚。

---

## 怎麼用

```
/threads-bench 中元節
/threads-bench https://www.threads.com/@某帳號/post/xxxx 這篇為什麼輸
/threads-bench topics
```

前兩種是跑一次 bench。報告分兩段：

1. 這次 bench 的整理（誰做得好、打法、被淘汰的建議）
2. 這次的 Top 5 主題，從這次找到的機會裡排出最值得寫的，最多 5 個

第三種不抓資料。把你跑過的所有 bench 累積的機會攤開，挑出現在最值得寫的 5 個，不用再開瀏覽器。太舊的會標「建議重跑 bench」。

第二種是我自己最常用的。某篇寫了沒中，連結丟進去，不用先想清楚要對標什麼。

第一次跑會問你要**低 token 版**（15 則樣本、報告精簡，快而便宜）還是**高 token 版**（25 則、逐帳號算基線、報告完整，慢而貴）。

跑完看 `benchmarks/reports/` 裡的報告。之後想寫文，先翻 `opportunities.md` 挑題，再翻 `playbook.md` 看打法。

---

## 安裝

先看你是用哪一種 Claude：

```
你在哪裡跟 Claude 對話？
  ├─ 終端機（打 claude 指令）        → 看「Claude Code」
  ├─ VS Code 裡的 Claude 擴充功能    → 看「Claude Code」，瀏覽器不用加 --chrome
  └─ Claude 桌面 App 的 Cowork 模式  → 看「Claude Desktop」
```

### Claude Code

#### macOS / Linux

```bash
git clone https://github.com/partylogo/threads-bench.git ~/.claude/skills/threads-bench
```

重開 Claude Code，打 `/threads-bench` 看有沒有出現。

#### Windows

在 PowerShell：

```powershell
git clone https://github.com/partylogo/threads-bench.git "$env:USERPROFILE\.claude\skills\threads-bench"
```

**要在原生 Windows 跑，不要在 WSL 裡。** WSL 不支援 Claude Code 的 Chrome 整合。

#### 只裝給某一個專案

不想全域安裝，clone 到專案底下的 `.claude/skills/threads-bench/` 也可以。只有在那個專案開 Claude Code 才看得到。

#### 接瀏覽器（Claude Code 必做）

1. Chrome（或 Edge、Brave、Arc）裝 [Claude in Chrome](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn) 擴充功能，版本 1.0.36 以上。
2. 在 Chrome 裡登入 Threads。搜尋頁沒登入會撞登入牆，什麼都抓不到。
3. 啟動時加旗標 `claude --chrome`。或在 Claude Code 裡打 `/chrome`，選 **Enabled by default**，之後就不用加。
4. 第一次操作 threads.com 會問權限，選允許整個站台。

限制：

- 要 Pro / Max / Team / Enterprise 方案，並且用 `/login` 登入。用 API key 登入的帳號不能用瀏覽器。
- 透過 Bedrock、Vertex 這類第三方平台用 Claude 的，也不能用瀏覽器。

### Claude Desktop（Cowork）

Cowork 有內建瀏覽器，不用裝擴充功能。

#### 1. 打包 skill

整個資料夾壓成 zip。SKILL.md 要在資料夾的第一層：

```
threads-bench.zip
└── threads-bench/
    ├── SKILL.md
    ├── modes/
    ├── knowledge/
    ├── scripts/
    └── templates/
```

macOS / Linux：

```bash
git clone https://github.com/partylogo/threads-bench.git
zip -r threads-bench.zip threads-bench -x "*.git*"
```

Windows：clone 之後對資料夾按右鍵 → 壓縮成 ZIP 檔案。

或直接到這個 repo 的 **Code → Download ZIP**。GitHub 給的 zip 解開後資料夾會叫 `threads-bench-main`，改名成 `threads-bench` 再壓一次。

#### 2. 上傳

1. 打開 Claude Desktop，Settings → Capabilities，確認 **Code execution** 是開的。
2. Customize → Skills → 「+」 → Upload a skill，選剛剛的 zip。
3. 上傳完在 Skills 清單裡把它開啟。

#### 3. 接瀏覽器

1. Settings → Cowork → **Preferred browser**，選內建瀏覽器（或 Claude in Chrome，兩個都能用）。
2. 第一次跑之前，先在內建瀏覽器登入 Threads。做法是叫 Claude「打開 threads.com」，瀏覽器會開在側欄，你在裡面登入。或從 Chrome 匯入登入狀態（一次性，可以挑只匯入 threads.com）。
3. Cowork 要指定一個工作資料夾，`benchmarks/` 會寫在那裡面。

限制：

- 內建瀏覽器 2026 年 8 月底開始開放 Pro / Max / Team，Enterprise 要管理員開。
- 內建瀏覽器暴露給 skill 的工具名稱沒有公開文件，skill 是靠「有 navigate 跟 find 的那組工具」自動認的。如果跑起來說找不到瀏覽器工具，把 Claude 列出的工具名稱貼給我，我補進 SKILL.md 那張表。

### 共同需求

- Python 3（安全寫檔腳本用。macOS 和多數 Linux 內建，Windows 到 python.org 裝，Cowork 的容器自己有）
- Threads 帳號，並在瀏覽器裡登入

---

## 它不做什麼

- 不幫你寫文。它只給題材和打法，怎麼寫是你的事。
- 不抄別人的文字。句式、開場、用字一律不進建議。
- 不出 threads.com。不碰私人帳號、不碰私訊、不繞登入牆。
- 不碰你工作目錄裡的其他檔案。只寫 `benchmarks/`。
- 不寫沒有連結的參照。報告裡提到的每一則貼文都附原文連結，抓不到的會明講「無永久連結」。

---

## 檔案結構

```
threads-bench/
├── SKILL.md                    主流程（bench）
├── modes/topics.md             從累積的機會裡挑 Top 5 的規則
├── knowledge/
│   ├── red-lines.md            演算法紅線（R）與正向訊號（S）定義
│   └── data-confidence.md      佐證強度分級
├── templates/FAILSAFE.md       寫檔安全規則：先備份、原子寫入、保留 5 份
└── scripts/
    ├── safe_write.py           安全寫檔腳本
    └── _atomic.py
```

# SAKE ATLAS｜清酒產地圖鑑

一本以「御朱印帳」為概念的清酒品飲圖鑑：每一款喝過的酒是一頁，每個縣是一枚收集到的印。

網站放在 GitHub 上，**之後更新只要上傳試算表或照片，網站會自動重新產生並發布**，不需要在自己電腦執行任何程式。

---

## 日常更新（最常用）

### 更新資料

1. 用 Excel 編輯 `sake-master-v6-dynamic-id.xlsx`，存檔後**關閉 Excel**。
2. 到 GitHub 上這個 repository，點進 `data` 資料夾 →「Add file」→「Upload files」。
3. 把試算表拖進去（**檔名保持一樣**，會直接取代舊的）→ 按「Commit changes」。
4. 等 2～3 分鐘，網站就更新了。

> `data/` 裡請只放一份試算表。

### 新增照片

1. 照片用**品飲編號**命名：`T00025.jpg`。同一次品飲有好幾張：`T00025.jpg`、`T00025-2.jpg`、`T00025-3.jpg`。
2. 點進 `photos` 資料夾 →「Add file」→「Upload files」→ 拖進照片 →「Commit changes」。
3. 等 2～3 分鐘。照片會自動：
   - 縮成網頁用的大小（**不裁切**，保留原始比例，9:16、3:4 都可以）
   - 存到 `static/images/t-T00025.webp`，原始照片從 `photos/` 移走
   - 每支酒用「最近一次」有照片的品飲當封面，其他次的照片放進那一次的品飲紀錄

jpg、png、webp、heic（iPhone）都可以，不用先裁切或縮小。網頁上傳單一檔案上限 25 MB、一次最多 100 個檔案。

**同時新增品飲紀錄和照片**：先上傳試算表，再上傳照片（照片要對得上試算表裡的品飲編號）。一起上傳也可以。

### 換掉或刪除照片

- **換照片**：用同樣的檔名再上傳到 `photos/` 一次，會蓋掉舊的。
- **刪照片**：到 `static/images/` 找到 `t-T00025.webp`，點開 → 右上角「…」→「Delete file」→ Commit。

### 確認有沒有成功

到 repository 上方的「**Actions**」分頁：

- 綠色勾勾 ✓：成功，網站已更新
- 紅色叉叉 ✗：失敗，點進去看哪一步出錯（最常見：試算表在 Excel 開著時上傳、或欄位名稱被改掉）
- 點進最新一次 → **Summary** 會列出照片對應結果；對不上的照片會留在 `photos/`，改好檔名重新上傳即可

---

## 第一次設定（只要做一次）

### 1. 建立 repository

1. 登入 GitHub，右上角「+」→「New repository」。
2. Repository name 填 `sake-atlas`（會成為網址的一部分），選 **Public**，其他不用勾，按「Create repository」。

### 2. 上傳檔案

**建議用 GitHub Desktop**（免費，desktop.github.com），因為檔案多、而且有一個隱藏資料夾 `.github`：

1. GitHub Desktop →「File」→「Clone repository」→ 選剛剛的 `sake-atlas`，存到電腦。
2. 把這個壓縮檔解開後**裡面所有的東西**（包含 `.github` 資料夾）複製進剛剛 clone 下來的資料夾。
   - Mac 的 Finder 預設不顯示隱藏資料夾，按 `Cmd + Shift + .` 就看得到 `.github`
   - Windows：檔案總管 →「檢視」→ 勾選「隱藏的項目」
3. 回到 GitHub Desktop，左下填「第一次上傳」→「Commit to main」→ 右上「Push origin」。

<details>
<summary>不想裝 GitHub Desktop，只用網頁上傳</summary>

1. 在 repository 頁面點「uploading an existing file」，把資料夾拖進去（一次最多 100 個檔案，`static/images` 照片較多，分兩三次上傳）。
2. 網頁拖曳通常會漏掉隱藏的 `.github` 資料夾，所以要手動建立：「Add file」→「Create new file」，檔名輸入 `.github/workflows/deploy.yml`，把壓縮檔裡同名檔案的內容整個貼上 → Commit。
</details>

### 3. 打開 GitHub Pages

repository →「**Settings**」→ 左側「**Pages**」→「Build and deployment」的 Source 選「**GitHub Actions**」。

### 4. 第一次發布

> 第 2 步上傳完時，Actions 可能已經自動跑了一次並出現紅色叉叉——那是因為當時還沒打開 Pages，不用理它。

到「Actions」分頁，左側點「建置並發布網站」→ 右側「Run workflow」→「Run workflow」。完成後網址是：

```
https://你的帳號.github.io/sake-atlas/
```

之後每次上傳都會自動發布，不用再按。

### 5.（選填）自己的網域

Settings → Pages →「Custom domain」填入網域，依畫面指示到網域商設定 DNS。

---

## 資料夾內容

| 位置 | 用途 |
| --- | --- |
| `data/sake-master-v6-dynamic-id.xlsx` | **主要資料**：酒款主資料、品飲紀錄 |
| `photos/` | **照片收件匣**：新照片放這裡，處理完會自動移走 |
| `static/images/` | 處理好的網頁版照片（`t-品飲編號.webp`） |
| `static/` | 樣式（site.css）、互動（site.js）、水墨背景、分享預覽圖 |
| `data/catalog-meta.json`、`data/prefectures.geojson` | 網站設定與地圖輪廓 |
| `build.py` | 把資料轉成網站的程式 |
| `.github/workflows/deploy.yml` | 自動建置與發布的設定 |
| `docs/` | 設計說明（DESIGN.md）與產品設定（PRODUCT.md） |
| `tools/` | 產生各縣水墨畫的工具 |

建置產生的 `dist/`（網站本體）與 `preview.html` 不放進 repository，GitHub 每次會重新產生。

## 網站有哪些頁面

- `/` 首頁：地圖與右頁（滑過縣名會換成該縣的紀錄並蓋上酒造朱印）、最近喝過的折帖、照片、依酒米／酒種／酒造的索引、特定名稱酒對照表
- `/sake/` 全部酒款：搜尋、篩選（區域、縣、酒種、酒米、有照片、有心得）、排序、酒帖與清單兩種顯示
- `/sake/S0001/` 每一款酒各自一頁，有自己的網址與分享預覽
- `/pref/yamagata/` 每個縣一頁（共 39 頁），依酒造分組
- `/guide/` 入門：特定名稱酒分類表、精米步合米粒、常見用語
- `/about/` 關於

篩選條件會寫在網址上，例如 `/sake/?rice=雄町&photo=1`，可以直接分享給別人。


## 在自己電腦預覽（選用）

```sh
pip install -r requirements.txt
python3 build.py
```

完成後雙擊 `preview.html` 就能在瀏覽器看整個網站。注意：在自己電腦建置時，`photos/` 裡的原始照片**不會**被移走。

## 網站設定

`build.py` 最上方的 `SITE`：

- `contact_email`：填了之後，「關於」頁會出現合作與品飲會的聯絡方式。
- `url`：用 GitHub Pages 時不用填，會自動帶入（用來產生 `sitemap.xml` 和分享預覽圖網址）。

## 殿堂朱印

喜歡程度達 4.5 分以上的酒，酒名旁會蓋一枚「殿堂」朱印。門檻在 `build.py` 的 `DENDO = 4.5`。

## 風味描述怎麼寫

直接在試算表「品飲紀錄」欄用平常的話寫就好，例如「紅蘋果香明顯，口感圓潤，尾段微苦」。建置時會自動找出風味詞，酒款頁就會出現：

- **香氣輪**：這支酒的香氣以朱色標在輪上，滑過任何一種香氣都會顯示說明。
- **利き猪口**：口感會畫成從上往下看的品酒杯（白瓷、杯底藍色蛇之目）。酒色依酒的特性：白濁、琥珀、粉紅、甘口偏暖、飽滿較濃、輕盈較淡；有酸度會泛起輕快的漣漪，圓潤的漣漪緩慢平順；有氣泡感會冒泡。滑過口感詞時，杯中的酒會盪一下。
- **心得裡的風味詞**：會加上朱色虛線，滑過或點一下就會就地顯示說明。
- 全部酒款頁會多一個「風味」篩選，酒款頁也會出現「風味相近的酒」。

會被辨認的詞列在 `build.py` 的 `AROMA`（香氣）與 `PALATE`（口感）。想新增香氣（例如「荔枝」），照同樣格式加一行，寫上說明就好。前面有「不、無、沒」的詞會自動略過（例如「不甜」）。

如果想直接指定，不靠自動辨認，填試算表的「香氣標籤」「口感標籤」欄即可（例如「蘋果、白花」）。有填香氣標籤的酒，酒卡底部會出現香氣色條。

## 法規提醒

頁尾已放上「禁止酒駕」「飲酒過量，有害健康」與未滿十八歲勿飲酒的提醒。日後若有店家合作或付費推薦，依《菸酒管理法》第 37 條，廣告或促銷內容的警語標示有面積規定，也不得鼓勵飲酒；網站本身不可加入任何線上訂購或購物車功能。實際做法建議先洽詢主管機關或律師。

## 各縣的水墨風景

首頁右頁與縣別頁背後的水墨畫在 `static/scenes/`，由 `tools/paint_scenes.py` 產生（需要 numpy 與 Pillow）。畫題寫在 `build.py` 的 `SCENE_CAPTION`。想改某個縣的構圖，修改 `paint_scenes.py` 裡 `SCENES` 對應的那一行，然後執行：

```sh
python3 tools/paint_scenes.py yamagata
```

## 字型

標題使用霞鶩文楷 TC（LXGW WenKai TC），內文使用 Noto Sans TC，皆由 Google Fonts 載入，不需另外上傳字型檔。

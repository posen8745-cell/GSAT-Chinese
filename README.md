# GSAT-Chinese｜學測國文逐題練習網站

網站使用 GitHub Pages，預計網址：`https://posen8745-cell.github.io/GSAT-Chinese/`。

## 這次修改

- **歷屆官方試卷（108–115）**：每個年度新增「原題・一題一題作答」按鈕，並有獨立的「官方原題・逐題作答」分頁。
- **一題一頁**：題號、完整題幹及原卷圖片（含原卷公式、插圖與選項）、作答區、核對、上下題、直接跳題、訂正筆記。單選／多選與非選擇題分開處理。
- **115 年第 1–3 題**：已根據大考中心原卷及參考答案核對，直接寫入 HTML；只更新 `index.html` 就能先練這三題。
- **108–115 年其他原題**：必須執行下述 GitHub Actions 產生原卷逐題圖片才能直接在頁面顯示，不會冒充已經完成、也不顯示空白答題卡。
- **原本自編國綜題庫**：28 題與 `questions.json` 均保留，**不是**官方原題。
- **國寫**：維持草稿練習，不用選擇題邏輯自動給分。

## GitHub 上傳（重要）

先將 ZIP **解壓縮**，將其內容依照下列路徑放到 Repository 的根目錄（**不是**直接上傳 ZIP 本身）：

```text
GSAT-Chinese/
  index.html
  questions.json
  official-sources.json
  README.md
  scripts/
    build_official_questions.py
  .github/
    workflows/
      build-official-question-images.yml
```

如果用 macOS Finder，看不到 `.github` 隱藏資料夾，可按 **Command + Shift + .**。上傳時務必保留目錄結構。

如果只替換 `index.html`，官方 115 年第 1–3 題可直接顯示，其餘題目仍會提示「尚未建立原題圖片」。

### 產生 8 年官方原題圖片

1. 在 Repository 點 **Actions**，選 **Build official Chinese question images**。
2. 點 **Run workflow → Run workflow**。如果 GitHub 提示啟用 workflows，先依畫面啟用。
3. 流程會下載大考中心 108–115 學年度的國文／國綜原卷及答案，依題號裁圖並產生 `assets/chinese/manifest.json`、逐題 WebP 圖片和 `assets/chinese/review.html`。
4. 若推送權限不足，檢查 **Settings → Actions → General → Workflow permissions** 的設定以及分支保護規則；也可下載 Actions 產出的 Artifact，手動上傳到 Repository。
5. 在網站查看各題，並開啟 `https://posen8745-cell.github.io/GSAT-Chinese/assets/chinese/review.html` **逐題檢查圖片是否裁切完整**，特別是閱讀題組共用文章、跨頁題、插圖、混合與非選擇題。

> **注意：圖片擷取工具在此環境只能使用合成 PDF 測試切圖邏輯，尚未實際從大考中心下載並完整跑過 8 年官方原卷。** GitHub Actions 執行可能失敗，生成的題目圖片也可能漏掉跨頁內容，仍需人工檢查。這個 ZIP 不包含已生成的 8 年逐題圖片，因此 **不能宣稱 108–115 年原題全部完成上線**。

## 資料與評分

- 官方題目的資料與自編題目分開。官方客觀題的答案由大考中心答案表核對；若答案擷取不可靠，網站不會啟用該題的自動批改。
- 多選題的練習結果以「整題完全正確」判定，不換算正式部分給分或級分。
- 非選擇題草稿可保存，但需人工評閱。
- 官方作答另存於瀏覽器 `localStorage` 的 `gsat-chinese-official-v1`；原有自編題與國寫資料保留。
- 官方資料來源：大學入學考試中心 `https://www.ceec.edu.tw/xmfile?xsmsid=0J052424829869345634`。

## 補充

本網站是個人學習專案，並非大考中心官方服務。請避免將未核對或裁切不完整的試題當成完整官方原題。

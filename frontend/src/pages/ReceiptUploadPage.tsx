import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";

import { saveExpense } from "../api/expenses";
import { analyzeReceiptImage } from "../api/receipts";
import type { ExpenseSavePayload, ReceiptAnalyzeResult } from "../types";
import { readableError } from "../utils/errors";
import styles from "./ReceiptUploadPage.module.css";

const maxImageSize = 10 * 1024 * 1024;
const categories = ["食費", "日用品", "交通費", "医療費", "娯楽", "その他"];
const initialConfirmForm: ExpenseSavePayload = {
  shop_name: "",
  purchased_at: "",
  total_amount: 0,
  category: "その他",
  raw_ocr_text: "",
};

type ReceiptUploadPageProps = {
  onLogout: () => Promise<void>;
  isSubmitting: boolean;
};

export default function ReceiptUploadPage({ onLogout, isSubmitting }: ReceiptUploadPageProps) {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState<ReceiptAnalyzeResult | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [confirmForm, setConfirmForm] = useState<ExpenseSavePayload>(initialConfirmForm);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl("");
      return;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);

    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setResult(null);
    setMessage("");
    setError("");

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!file.type.startsWith("image/")) {
      setSelectedFile(null);
      setError("画像ファイルを選択してください。");
      return;
    }

    if (file.size > maxImageSize) {
      setSelectedFile(null);
      setError("画像サイズは10MB以下にしてください。");
      return;
    }

    setSelectedFile(file);
  }

  async function handleAnalyze() {
    if (!selectedFile) {
      setError("レシート画像を選択してください。");
      return;
    }

    setIsAnalyzing(true);
    setError("");
    setMessage("");
    setResult(null);

    try {
      const analyzedResult = await analyzeReceiptImage(selectedFile);
      setResult(analyzedResult);
      setConfirmForm({
        shop_name: analyzedResult.shop_name ?? "",
        purchased_at: analyzedResult.purchased_at ?? "",
        total_amount: analyzedResult.total_amount ?? 0,
        category: "その他",
        raw_ocr_text: analyzedResult.raw_ocr_text,
      });
      setMessage(analyzedResult.detail ?? "画像をアップロードしました。");
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleSave() {
    const validationError = validateConfirmForm(confirmForm);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSaving(true);
    setError("");
    setMessage("");

    try {
      const savedExpense = await saveExpense(confirmForm, selectedFile);
      navigate("/receipts/complete", { state: { expense: savedExpense } });
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setIsSaving(false);
    }
  }

  function clearSelection() {
    setSelectedFile(null);
    setResult(null);
    setConfirmForm(initialConfirmForm);
    setMessage("");
    setError("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  const hasSelection = selectedFile !== null;
  const isBusy = isSubmitting || isAnalyzing || isSaving;

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>レシート登録</p>
          <h1>画像をアップロード</h1>
        </div>
        <div className={styles.headerActions}>
          <button type="button" className={styles.buttonSecondary} onClick={() => navigate("/home")}>
            ホーム
          </button>
          <button
            type="button"
            className={styles.buttonSecondary}
            onClick={onLogout}
            disabled={isBusy}
          >
            ログアウト
          </button>
        </div>
      </header>

      {message && <p className={styles.notice}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}

      <section className={styles.uploadPanel} aria-label="レシート画像アップロード">
        <label className={styles.dropArea}>
          <span className={styles.dropIcon} aria-hidden="true">
            +
          </span>
          <strong>{hasSelection ? selectedFile.name : "レシート画像を選択"}</strong>
          <small>スマホではカメラ起動、PCでは画像ファイル選択に対応しています。</small>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
          />
        </label>

        <div className={styles.previewPanel}>
          {previewUrl ? (
            <img src={previewUrl} alt="選択したレシート画像のプレビュー" />
          ) : (
            <div className={styles.emptyPreview}>
              <strong>プレビュー</strong>
              <span>選択した画像がここに表示されます。</span>
            </div>
          )}
        </div>
      </section>

      <section className={styles.actionRow} aria-label="解析操作">
        <button
          type="button"
          className={styles.primaryButton}
          onClick={handleAnalyze}
          disabled={!hasSelection || isAnalyzing || isSaving}
        >
          {isAnalyzing ? "解析中..." : "OCR解析へ進む"}
        </button>
        <button
          type="button"
          className={styles.buttonSecondary}
          onClick={clearSelection}
          disabled={!hasSelection || isBusy}
        >
          選択を解除
        </button>
      </section>

      {isAnalyzing && (
        <section className={styles.loadingPanel} aria-live="polite">
          <span className={styles.spinner} aria-hidden="true" />
          <strong>画像を送信しています</strong>
        </section>
      )}

      {result && (
        <section className={styles.resultPanel} aria-labelledby="receipt-result-title">
          <div className={styles.resultHeading}>
            <div>
              <p className={styles.eyebrow}>確認・修正</p>
              <h2 id="receipt-result-title">支出として保存</h2>
            </div>
            <span>{result.image?.name ?? selectedFile?.name ?? "-"}</span>
          </div>

          <div className={styles.formGrid}>
            <label>
              店名
              <input
                type="text"
                value={confirmForm.shop_name}
                onChange={(event) =>
                  setConfirmForm((current) => ({ ...current, shop_name: event.target.value }))
                }
                placeholder="店名を入力"
              />
            </label>

            <label>
              購入日
              <input
                type="date"
                value={confirmForm.purchased_at}
                onChange={(event) =>
                  setConfirmForm((current) => ({ ...current, purchased_at: event.target.value }))
                }
              />
            </label>

            <label>
              合計金額
              <input
                type="number"
                min="1"
                inputMode="numeric"
                value={confirmForm.total_amount || ""}
                onChange={(event) =>
                  setConfirmForm((current) => ({
                    ...current,
                    total_amount: Number(event.target.value),
                  }))
                }
                placeholder="0"
              />
            </label>

            <label>
              カテゴリー
              <select
                value={confirmForm.category}
                onChange={(event) =>
                  setConfirmForm((current) => ({ ...current, category: event.target.value }))
                }
              >
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </label>

            <label className={styles.fullWidth}>
              OCR全文
              <textarea
                value={confirmForm.raw_ocr_text}
                onChange={(event) =>
                  setConfirmForm((current) => ({ ...current, raw_ocr_text: event.target.value }))
                }
                rows={5}
                placeholder="OCRで読み取った全文"
              />
            </label>
          </div>

          <button
            type="button"
            className={styles.saveButton}
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? "保存中..." : "支出として保存"}
          </button>
        </section>
      )}
    </main>
  );
}

function validateConfirmForm(form: ExpenseSavePayload) {
  if (!form.purchased_at) {
    return "購入日を入力してください。";
  }

  if (!Number.isInteger(form.total_amount) || form.total_amount <= 0) {
    return "合計金額は1円以上の半角数字で入力してください。";
  }

  if (!form.category.trim()) {
    return "カテゴリーを選択してください。";
  }

  return "";
}

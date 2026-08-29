import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";

import { classifyCategory, fetchCategories, saveExpense } from "../api/expenses";
import CategorySelect from "../components/CategorySelect";
import { runReceiptOcr, toClientOCRResult } from "../ocr/receiptOcr";
import type { Category, ExpenseSavePayload, ReceiptOCRResult } from "../types";
import { readableError } from "../utils/errors";
import styles from "./ReceiptUploadPage.module.css";

const maxImageSize = 10 * 1024 * 1024;
const lowConfidenceThreshold = 70;
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
  const analysisGenerationRef = useRef(0);
  const analysisControllerRef = useRef<AbortController | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState<ReceiptOCRResult | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [automaticCategory, setAutomaticCategory] = useState("その他");
  const [categoryError, setCategoryError] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [ocrProgress, setOcrProgress] = useState(0);
  const [ocrStatus, setOcrStatus] = useState("");
  const [confirmForm, setConfirmForm] = useState<ExpenseSavePayload>(initialConfirmForm);

  useEffect(() => {
    let active = true;
    fetchCategories()
      .then((categoryList) => {
        if (active) {
          setCategories(categoryList);
          setCategoryError("");
        }
      })
      .catch(() => {
        if (active) {
          setCategoryError("カテゴリー一覧を取得できませんでした。ページを再読み込みしてください。");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl("");
      return;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);

    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  useEffect(() => {
    return () => {
      analysisGenerationRef.current += 1;
      analysisControllerRef.current?.abort();
      analysisControllerRef.current = null;
    };
  }, []);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    analysisGenerationRef.current += 1;
    analysisControllerRef.current?.abort();
    analysisControllerRef.current = null;
    resetAnalysis();

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

    const generation = analysisGenerationRef.current + 1;
    analysisGenerationRef.current = generation;
    analysisControllerRef.current?.abort();
    const controller = new AbortController();
    analysisControllerRef.current = controller;
    setIsAnalyzing(true);
    setError("");
    setMessage("");
    setResult(null);
    setOcrProgress(0);
    setOcrStatus("OCRを準備しています");

    try {
      const analyzedResult = await runReceiptOcr(
        selectedFile,
        ({ status, progress }) => {
          if (generation !== analysisGenerationRef.current) {
            return;
          }
          setOcrStatus(toJapaneseOcrStatus(status));
          setOcrProgress(progress);
        },
        controller.signal,
      );
      if (generation !== analysisGenerationRef.current) {
        return;
      }

      let classifiedCategory = "その他";
      try {
        const category = await classifyCategory(
          analyzedResult.shop_name ?? "",
          analyzedResult.raw_ocr_text,
        );
        classifiedCategory = category.name;
      } catch {
        setCategoryError("自動分類に失敗したため「その他」を設定しました。手動で変更できます。");
      }
      if (generation !== analysisGenerationRef.current) {
        return;
      }

      setResult(analyzedResult);
      setAutomaticCategory(classifiedCategory);
      setConfirmForm({
        shop_name: analyzedResult.shop_name ?? "",
        purchased_at: analyzedResult.purchased_at ?? "",
        total_amount: analyzedResult.total_amount ?? 0,
        category: classifiedCategory,
        raw_ocr_text: analyzedResult.raw_ocr_text,
      });
      setOcrProgress(1);
      setMessage("ブラウザ内のOCR解析が完了しました。内容を確認して保存してください。");
    } catch (requestError) {
      if (controller.signal.aborted) {
        return;
      }
      if (generation === analysisGenerationRef.current) {
        const detail = requestError instanceof Error ? requestError.message : "";
        setError(
          detail
            ? `OCR解析に失敗しました（${detail}）。画像を選び直して、もう一度お試しください。`
            : "OCR解析に失敗しました。画像を選び直して、もう一度お試しください。",
        );
      }
    } finally {
      if (analysisControllerRef.current === controller) {
        analysisControllerRef.current = null;
      }
      if (generation === analysisGenerationRef.current) {
        setIsAnalyzing(false);
      }
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
      const payload = result
        ? {
            ...confirmForm,
            ocr_result: { ...toClientOCRResult(result), category: automaticCategory },
          }
        : confirmForm;
      const savedExpense = await saveExpense(payload, selectedFile);
      navigate("/receipts/complete", { state: { expense: savedExpense } });
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setIsSaving(false);
    }
  }

  function resetAnalysis() {
    setIsAnalyzing(false);
    setResult(null);
    setAutomaticCategory("その他");
    setConfirmForm(initialConfirmForm);
    setOcrProgress(0);
    setOcrStatus("");
    setMessage("");
    setError("");
  }

  function clearSelection() {
    analysisGenerationRef.current += 1;
    analysisControllerRef.current?.abort();
    analysisControllerRef.current = null;
    setSelectedFile(null);
    resetAnalysis();
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
      {categoryError && <p className={styles.error}>{categoryError}</p>}
      {result && result.confidence < lowConfidenceThreshold && (
        <p className={styles.warning}>
          OCRの信頼度が低いため、店名・購入日・合計金額をレシート画像と照合してください。
        </p>
      )}

      <section className={styles.uploadPanel} aria-label="レシート画像アップロード">
        <label className={styles.dropArea}>
          <span className={styles.dropIcon} aria-hidden="true">
            +
          </span>
          <strong>{hasSelection ? selectedFile.name : "レシート画像を選択"}</strong>
          <small>画像はサーバーへ送信せず、このブラウザ内だけでOCR解析します。</small>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
            disabled={isAnalyzing}
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
          disabled={!hasSelection || isBusy}
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
          <strong>{ocrStatus}</strong>
          <progress value={ocrProgress} max={1} aria-label="OCR解析の進捗" />
          <small>{Math.round(ocrProgress * 100)}%</small>
        </section>
      )}

      {result && (
        <section className={styles.resultPanel} aria-labelledby="receipt-result-title">
          <div className={styles.resultHeading}>
            <div>
              <p className={styles.eyebrow}>確認・修正</p>
              <h2 id="receipt-result-title">支出として保存</h2>
            </div>
            <span>
              {selectedFile?.name ?? "-"}・信頼度 {Math.round(result.confidence)}%
            </span>
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
              <CategorySelect
                categories={categories}
                value={confirmForm.category}
                onChange={(category) =>
                  setConfirmForm((current) => ({ ...current, category }))
                }
              />
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

function toJapaneseOcrStatus(status: string) {
  const labels: Record<string, string> = {
    "loading tesseract core": "OCRエンジンを読み込んでいます",
    "initializing tesseract": "OCRエンジンを初期化しています",
    "loading language traineddata": "日本語・英語モデルを読み込んでいます",
    "initializing api": "文字認識を準備しています",
    "recognizing text": "レシートの文字を読み取っています",
  };
  return labels[status] ?? "OCRを準備しています";
}

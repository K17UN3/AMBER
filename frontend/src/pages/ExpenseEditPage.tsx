import { useEffect, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { fetchCategories, fetchExpenseDetail, updateExpense } from "../api/expenses";
import CategorySelect from "../components/CategorySelect";
import type { Category, ExpenseSavePayload, SavedExpense } from "../types";
import { readableError } from "../utils/errors";
import styles from "./ExpenseEditPage.module.css";

const maxImageSize = 10 * 1024 * 1024;
const initialForm: ExpenseSavePayload = {
  shop_name: "",
  purchased_at: "",
  total_amount: 0,
  category: "その他",
  raw_ocr_text: "",
};

type ExpenseEditPageProps = {
  onLogout: () => Promise<void>;
  isSubmitting: boolean;
};

export default function ExpenseEditPage({ onLogout, isSubmitting }: ExpenseEditPageProps) {
  const navigate = useNavigate();
  const { expenseId } = useParams();
  const [expense, setExpense] = useState<SavedExpense | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState<ExpenseSavePayload>(initialForm);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadExpense() {
      try {
        const id = Number(expenseId);
        if (!Number.isInteger(id)) {
          throw new Error("invalid id");
        }
        const [data, categoryList] = await Promise.all([
          fetchExpenseDetail(id),
          fetchCategories(),
        ]);
        setExpense(data);
        setCategories(categoryList);
        setForm({
          shop_name: data.shop_name,
          purchased_at: data.purchased_at,
          total_amount: data.total_amount,
          category: data.category,
          raw_ocr_text: data.raw_ocr_text,
        });
      } catch (requestError) {
        setError(readableError(requestError));
      } finally {
        setLoading(false);
      }
    }

    void loadExpense();
  }, [expenseId]);

  useEffect(() => {
    if (!selectedImage) {
      setPreviewUrl("");
      return;
    }

    const objectUrl = URL.createObjectURL(selectedImage);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedImage]);

  function handleImageChange(event: ChangeEvent<HTMLInputElement>) {
    const image = event.target.files?.[0] ?? null;
    setError("");
    if (!image) {
      setSelectedImage(null);
      return;
    }
    if (!image.type.startsWith("image/")) {
      event.target.value = "";
      setError("画像ファイルを選択してください。");
      return;
    }
    if (image.size > maxImageSize) {
      event.target.value = "";
      setError("画像サイズは10MB以下にしてください。");
      return;
    }
    setSelectedImage(image);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateExpenseForm(form);
    if (validationError || !expense) {
      setError(validationError || "支出データを読み込めませんでした。");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const updated = await updateExpense(expense.id, form, selectedImage);
      navigate(`/expenses/${updated.id}`, {
        replace: true,
        state: { toast: "支出を更新しました。" },
      });
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setSaving(false);
    }
  }

  const isBusy = isSubmitting || saving;
  const displayedImage = previewUrl || expense?.image;

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>支出編集</p>
          <h1>{expense?.shop_name || "支出を編集"}</h1>
        </div>
        <button type="button" className={styles.secondaryButton} onClick={onLogout} disabled={isBusy}>
          ログアウト
        </button>
      </header>

      {error ? <p className={styles.error}>{error}</p> : null}

      {loading ? (
        <p className={styles.loading}>読み込み中...</p>
      ) : expense ? (
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.formGrid}>
            <label>
              店名
              <input
                type="text"
                value={form.shop_name}
                onChange={(event) => setForm((current) => ({ ...current, shop_name: event.target.value }))}
              />
            </label>
            <label>
              購入日
              <input
                type="date"
                required
                value={form.purchased_at}
                onChange={(event) => setForm((current) => ({ ...current, purchased_at: event.target.value }))}
              />
            </label>
            <label>
              合計金額
              <input
                type="number"
                min="1"
                required
                inputMode="numeric"
                value={form.total_amount || ""}
                onChange={(event) =>
                  setForm((current) => ({ ...current, total_amount: Number(event.target.value) }))
                }
              />
            </label>
            <label>
              カテゴリー
              <CategorySelect
                categories={categories}
                value={form.category}
                onChange={(category) => setForm((current) => ({ ...current, category }))}
              />
            </label>
            <label className={styles.fullWidth}>
              OCR全文
              <textarea
                rows={6}
                value={form.raw_ocr_text}
                onChange={(event) => setForm((current) => ({ ...current, raw_ocr_text: event.target.value }))}
              />
            </label>
          </div>

          <section className={styles.imageSection} aria-labelledby="receipt-image-title">
            <div>
              <h2 id="receipt-image-title">レシート画像</h2>
              <label className={styles.fileButton}>
                画像を選択
                <input type="file" accept="image/*" onChange={handleImageChange} />
              </label>
              <p>{selectedImage ? selectedImage.name : "新しい画像を選ばない場合は現在の画像を維持します。"}</p>
            </div>
            <div className={styles.preview}>
              {displayedImage ? <img src={displayedImage} alt="レシート画像のプレビュー" /> : <span>画像なし</span>}
            </div>
          </section>

          <div className={styles.actions}>
            <button type="submit" className={styles.saveButton} disabled={isBusy}>
              {saving ? "保存中..." : "変更を保存"}
            </button>
            <button type="button" className={styles.secondaryButton} onClick={() => navigate(`/expenses/${expense.id}`)} disabled={isBusy}>
              キャンセル
            </button>
          </div>
        </form>
      ) : null}
    </main>
  );
}

function validateExpenseForm(form: ExpenseSavePayload) {
  if (!form.purchased_at) return "購入日を入力してください。";
  if (!Number.isInteger(form.total_amount) || form.total_amount <= 0) {
    return "合計金額は1円以上の半角数字で入力してください。";
  }
  if (!form.category.trim()) return "カテゴリーを選択してください。";
  return "";
}

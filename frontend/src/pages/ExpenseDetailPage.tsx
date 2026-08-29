import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { deleteExpense, fetchExpenseDetail } from "../api/expenses";
import Toast from "../components/Toast";
import type { SavedExpense } from "../types";
import { readableError } from "../utils/errors";
import { formatCurrency } from "../utils/format";
import styles from "./ExpenseDetailPage.module.css";

type ExpenseDetailPageProps = {
  onLogout: () => Promise<void>;
  isSubmitting: boolean;
};

type NavigationState = { toast?: string };

export default function ExpenseDetailPage({ onLogout, isSubmitting }: ExpenseDetailPageProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { expenseId } = useParams();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [expense, setExpense] = useState<SavedExpense | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(() => (location.state as NavigationState | null)?.toast ?? "");

  useEffect(() => {
    if ((location.state as NavigationState | null)?.toast) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.pathname, location.state, navigate]);

  useEffect(() => {
    async function loadExpense() {
      setExpense(null);
      setError("");
      try {
        const id = Number(expenseId);
        if (!Number.isInteger(id)) throw new Error("invalid id");
        setExpense(await fetchExpenseDetail(id));
      } catch (requestError) {
        setError(readableError(requestError));
      } finally {
        setLoading(false);
      }
    }

    void loadExpense();
  }, [expenseId]);

  const closeDialog = useCallback(() => {
    dialogRef.current?.close();
  }, []);

  async function handleDelete() {
    if (!expense) return;
    setDeleting(true);
    setError("");
    try {
      await deleteExpense(expense.id);
      closeDialog();
      navigate("/expenses", { replace: true, state: { toast: "支出を削除しました。" } });
    } catch (requestError) {
      closeDialog();
      setError(readableError(requestError));
      setDeleting(false);
    }
  }

  return (
    <main className={styles.shell}>
      <Toast message={toast} onDismiss={() => setToast("")} />
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>支出詳細</p>
          <h1>{expense?.shop_name || "支出詳細"}</h1>
        </div>
        <button type="button" className={styles.secondaryButton} onClick={onLogout} disabled={isSubmitting || deleting}>
          ログアウト
        </button>
      </header>

      {error ? <p className={styles.error}>{error}</p> : null}

      {loading ? (
        <p className={styles.loading}>読み込み中...</p>
      ) : expense ? (
        <>
          <section className={styles.detailPanel}>
            <dl className={styles.detailList}>
              <div><dt>店名</dt><dd>{expense.shop_name || "未入力"}</dd></div>
              <div><dt>購入日</dt><dd>{expense.purchased_at}</dd></div>
              <div><dt>金額</dt><dd>{formatCurrency(expense.total_amount)}</dd></div>
              <div><dt>カテゴリー</dt><dd>{expense.category}</dd></div>
              {expense.image ? (
                <div className={styles.fullWidth}>
                  <dt>画像</dt>
                  <dd><img src={expense.image} alt="レシート画像" /></dd>
                </div>
              ) : null}
              {expense.raw_ocr_text ? (
                <div className={styles.fullWidth}>
                  <dt>OCR全文</dt>
                  <dd className={styles.ocrText}>{expense.raw_ocr_text}</dd>
                </div>
              ) : null}
            </dl>
          </section>

          <div className={styles.actions}>
            <button type="button" className={styles.editButton} onClick={() => navigate(`/expenses/${expense.id}/edit`)}>
              編集
            </button>
            <button type="button" className={styles.deleteButton} onClick={() => dialogRef.current?.showModal()}>
              削除
            </button>
            <button type="button" className={styles.secondaryButton} onClick={() => navigate("/expenses")}>
              一覧へ戻る
            </button>
          </div>
        </>
      ) : null}

      <dialog ref={dialogRef} className={styles.dialog} onCancel={closeDialog}>
        <h2>支出を削除しますか？</h2>
        <p>この操作は取り消せません。支出データと保存済み画像を削除します。</p>
        <div className={styles.dialogActions}>
          <button type="button" className={styles.deleteButton} onClick={handleDelete} disabled={deleting}>
            {deleting ? "削除中..." : "削除する"}
          </button>
          <button type="button" className={styles.secondaryButton} onClick={closeDialog} disabled={deleting}>
            キャンセル
          </button>
        </div>
      </dialog>
    </main>
  );
}

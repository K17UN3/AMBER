import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { fetchExpenseDetail } from "../api/expenses";
import type { SavedExpense } from "../types";
import { formatCurrency } from "../utils/format";
import styles from "./ComingSoonPage.module.css";

type ExpenseDetailPageProps = {
  onLogout: () => Promise<void>;
  isSubmitting: boolean;
};

export default function ExpenseDetailPage({ onLogout, isSubmitting }: ExpenseDetailPageProps) {
  const navigate = useNavigate();
  const { expenseId } = useParams();
  const [expense, setExpense] = useState<SavedExpense | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadExpense() {
      try {
        const id = Number(expenseId);
        if (!Number.isInteger(id)) {
          throw new Error("invalid id");
        }
        const data = await fetchExpenseDetail(id);
        setExpense(data);
      } catch {
        setError("支出詳細の読み込みに失敗しました。ログイン状態を確認してください。");
      } finally {
        setLoading(false);
      }
    }

    void loadExpense();
  }, [expenseId]);

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>支出詳細</p>
          <h1>{expense?.shop_name || "支出詳細"}</h1>
        </div>
        <button type="button" className={styles.buttonSecondary} onClick={onLogout} disabled={isSubmitting}>
          ログアウト
        </button>
      </header>

      {error && <p className={styles.error}>{error}</p>}

      {loading ? (
        <p className={styles.description}>読み込み中...</p>
      ) : expense ? (
        <section className={styles.panel}>
          <dl style={{ display: "grid", gap: "12px", margin: 0 }}>
            <div>
              <dt style={{ fontSize: "0.85rem", color: "#6b7280" }}>店名</dt>
              <dd style={{ margin: "4px 0 0" }}>{expense.shop_name || "未入力"}</dd>
            </div>
            <div>
              <dt style={{ fontSize: "0.85rem", color: "#6b7280" }}>購入日</dt>
              <dd style={{ margin: "4px 0 0" }}>{expense.purchased_at}</dd>
            </div>
            <div>
              <dt style={{ fontSize: "0.85rem", color: "#6b7280" }}>金額</dt>
              <dd style={{ margin: "4px 0 0" }}>{formatCurrency(expense.total_amount)}</dd>
            </div>
            <div>
              <dt style={{ fontSize: "0.85rem", color: "#6b7280" }}>カテゴリー</dt>
              <dd style={{ margin: "4px 0 0" }}>{expense.category}</dd>
            </div>
            {expense.image ? (
              <div>
                <dt style={{ fontSize: "0.85rem", color: "#6b7280" }}>画像</dt>
                <dd style={{ margin: "4px 0 0" }}>
                  <img src={expense.image} alt="レシート画像" style={{ maxWidth: "100%", borderRadius: "8px" }} />
                </dd>
              </div>
            ) : null}
            {expense.raw_ocr_text ? (
              <div>
                <dt style={{ fontSize: "0.85rem", color: "#6b7280" }}>OCR全文</dt>
                <dd style={{ margin: "4px 0 0", whiteSpace: "pre-wrap" }}>{expense.raw_ocr_text}</dd>
              </div>
            ) : null}
          </dl>
        </section>
      ) : null}

      <button type="button" className={styles.buttonSecondary} onClick={() => navigate("/expenses")}>
        一覧へ戻る
      </button>
    </main>
  );
}

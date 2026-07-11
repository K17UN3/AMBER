import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchExpenses } from "../api/expenses";
import type { SavedExpense } from "../types";
import { formatCurrency } from "../utils/format";
import styles from "./ComingSoonPage.module.css";

type ExpenseListPageProps = {
  onLogout: () => Promise<void>;
  isSubmitting: boolean;
};

export default function ExpenseListPage({ onLogout, isSubmitting }: ExpenseListPageProps) {
  const navigate = useNavigate();
  const [expenses, setExpenses] = useState<SavedExpense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadExpenses() {
      try {
        const data = await fetchExpenses();
        setExpenses(data);
      } catch (requestError) {
        setError("支出一覧の読み込みに失敗しました。ログイン状態を確認してください。");
      } finally {
        setLoading(false);
      }
    }

    void loadExpenses();
  }, []);

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>支出一覧</p>
          <h1>保存済みの支出</h1>
        </div>
        <button type="button" className={styles.buttonSecondary} onClick={onLogout} disabled={isSubmitting}>
          ログアウト
        </button>
      </header>

      {error && <p className={styles.error}>{error}</p>}

      {loading ? (
        <p className={styles.description}>読み込み中...</p>
      ) : expenses.length === 0 ? (
        <section className={styles.panel}>
          <p className={styles.description}>まだ支出がありません。レシートから保存してください。</p>
        </section>
      ) : (
        <section className={styles.panel} aria-label="支出一覧">
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: "12px" }}>
            {expenses.map((expense) => (
              <li
                key={expense.id}
                onClick={() => navigate(`/expenses/${expense.id}`)}
                style={{
                  border: "1px solid #e5e7eb",
                  borderRadius: "12px",
                  padding: "16px",
                  background: "#fff",
                  cursor: "pointer",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                  <div>
                    <strong>{expense.shop_name || "未入力"}</strong>
                    <div style={{ color: "#6b7280", marginTop: "4px" }}>
                      {expense.purchased_at} / {expense.category}
                    </div>
                  </div>
                  <b>{formatCurrency(expense.total_amount)}</b>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <button type="button" className={styles.buttonSecondary} onClick={() => navigate("/home")}>
        ホームへ戻る
      </button>
    </main>
  );
}

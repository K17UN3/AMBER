import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchExpenses, fetchMonthlySummary } from "../api/expenses";
import type { DashboardSummary, User } from "../types";
import { formatCurrency } from "../utils/format";
import styles from "./HomePage.module.css";

type HomePageProps = {
  user: User;
  message: string;
  error: string;
  isSubmitting: boolean;
  onLogout: () => Promise<void>;
};

export default function HomePage({ user, message, error, isSubmitting, onLogout }: HomePageProps) {
  const navigate = useNavigate();
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary>({
    totalAmount: 0,
    receiptCount: 0,
    recentExpenses: [],
  });
  const [dashboardError, setDashboardError] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      setDashboardError("");

      const today = new Date();
      const currentMonth = today.getMonth() + 1;
      const currentYear = today.getFullYear();

      try {
        const summary = await fetchMonthlySummary(currentYear, currentMonth);
        const totalAmount = summary.grand_total;

        try {
          const expenses = await fetchExpenses();
          const monthKey = `${currentYear}-${String(currentMonth).padStart(2, "0")}`;
          const monthlyExpenses = expenses.filter(
            (expense) => expense.purchased_at.slice(0, 7) === monthKey,
          );

          const recentExpenses = [...monthlyExpenses]
            .sort((left, right) => Date.parse(right.purchased_at) - Date.parse(left.purchased_at))
            .slice(0, 5)
            .map((expense) => ({
              id: expense.id,
              shopName: expense.shop_name,
              purchasedAt: expense.purchased_at,
              category: expense.category,
              totalAmount: expense.total_amount,
            }));

          setDashboardSummary({
            totalAmount,
            receiptCount: monthlyExpenses.length,
            recentExpenses,
          });
        } catch {
          setDashboardSummary({
            totalAmount,
            receiptCount: 0,
            recentExpenses: [],
          });
          setDashboardError(
            "最近の支出の読み込みに失敗しました。集計データは表示されますが、最新の支出は取得できませんでした。",
          );
        }
      } catch {
        setDashboardSummary({ totalAmount: 0, receiptCount: 0, recentExpenses: [] });
        setDashboardError("集計情報の取得に失敗しました。通信環境やログイン状態を確認してください。");
      }
    }

    void loadDashboard();
  }, []);

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>ためるん</p>
          <h1>{user.username}さんのホーム</h1>
        </div>
        <button
          type="button"
          className={`${styles.buttonSecondary} ${styles.buttonCompact}`}
          onClick={onLogout}
          disabled={isSubmitting}
        >
          ログアウト
        </button>
      </header>

      {message ? <p className={styles.notice}>{message}</p> : null}
      {error ? <p className={styles.error}>{error}</p> : null}
      {dashboardError ? <p className={styles.error}>{dashboardError}</p> : null}

      <section className={styles.summaryPanel} aria-labelledby="monthly-total-title">
        <div>
          <p className={styles.eyebrow}>今月の支出</p>
          <h2 id="monthly-total-title">{formatCurrency(dashboardSummary.totalAmount)}</h2>
          <p className={styles.summaryNote}>登録された支出が月次合計に反映されます。</p>
        </div>
        <div className={styles.receiptCount}>
          <span>{dashboardSummary.receiptCount}</span>
          <small>件</small>
        </div>
      </section>

      <section className={styles.primaryActions} aria-label="主な操作">
        <button
          type="button"
          className={styles.scanButton}
          onClick={() => navigate("/receipts/new")}
        >
          <span className={styles.buttonIcon} aria-hidden="true">
            +
          </span>
          レシートを登録
        </button>
        <button
          type="button"
          className={styles.buttonSecondary}
          onClick={() => navigate("/expenses")}
        >
          支出一覧
        </button>
        <button
          type="button"
          className={styles.buttonSecondary}
          onClick={() => navigate("/summary")}
        >
          月次集計
        </button>
      </section>

      <section className={styles.contentGrid}>
        <div className={styles.sectionBlock}>
          <div className={styles.sectionHeading}>
            <h2>最近の支出</h2>
            <button
              type="button"
              className={styles.textButton}
              onClick={() => navigate("/expenses")}
            >
              すべて見る
            </button>
          </div>

          {dashboardSummary.recentExpenses.length > 0 ? (
            <ul className={styles.expenseList}>
              {dashboardSummary.recentExpenses.map((expense) => (
                <li key={expense.id} className={styles.expenseItem}>
                  <div>
                    <strong>{expense.shopName}</strong>
                    <span>
                      {expense.purchasedAt} / {expense.category}
                    </span>
                  </div>
                  <b>{formatCurrency(expense.totalAmount)}</b>
                </li>
              ))}
            </ul>
          ) : (
            <div className={styles.emptyState}>
              <strong>まだ支出がありません</strong>
              <p>レシート登録ができるようになると、ここに直近の支出が表示されます。</p>
            </div>
          )}
        </div>

        <div className={`${styles.sectionBlock} ${styles.profileBlock}`}>
          <h2>アカウント</h2>
          <dl className={styles.definitionList}>
            <dt>ID</dt>
            <dd>{user.id}</dd>
            <dt>ユーザー名</dt>
            <dd>{user.username}</dd>
            <dt>メール</dt>
            <dd>{user.email || "-"}</dd>
          </dl>
        </div>
      </section>
    </main>
  );
}

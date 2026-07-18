import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchMonthlySummary } from "../api/expenses";
import type { MonthlyCategorySummary, MonthlySummaryResponse } from "../types";
import { formatCurrency } from "../utils/format";
import styles from "./ComingSoonPage.module.css";

type MonthlySummaryPageProps = {
  onLogout: () => Promise<void>;
  isSubmitting: boolean;
};

const monthLabels = [
  "1月",
  "2月",
  "3月",
  "4月",
  "5月",
  "6月",
  "7月",
  "8月",
  "9月",
  "10月",
  "11月",
  "12月",
];

export default function MonthlySummaryPage({ onLogout, isSubmitting }: MonthlySummaryPageProps) {
  const navigate = useNavigate();
  const today = new Date();
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(today.getMonth() + 1);
  const [summary, setSummary] = useState<MonthlySummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSummary() {
      setIsLoading(true);
      setError("");
      setSummary(null);

      try {
        const data = await fetchMonthlySummary(currentYear, currentMonth);
        setSummary(data);
      } catch {
        setError("通信環境を確認して、もう一度お試しください。");
        setSummary(null);
      } finally {
        setIsLoading(false);
      }
    }

    void loadSummary();
  }, [currentYear, currentMonth]);

  const categoryRows = useMemo(() => {
    if (!summary) {
      return [] as Array<MonthlyCategorySummary & { percentage: number }>;
    }

    const total = summary.grand_total || 0;
    return summary.categories.map((category) => ({
      ...category,
      percentage: total > 0 ? Math.round((category.total / total) * 1000) / 10 : 0,
    }));
  }, [summary]);

  function shiftMonth(offset: number) {
    const baseDate = new Date(currentYear, currentMonth - 1 + offset, 1);
    setCurrentYear(baseDate.getFullYear());
    setCurrentMonth(baseDate.getMonth() + 1);
  }

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>集計</p>
          <h1>{currentYear}年 {currentMonth}月</h1>
        </div>
        <button type="button" className={styles.buttonSecondary} onClick={onLogout} disabled={isSubmitting}>
          ログアウト
        </button>
      </header>

      <section className={styles.sectionBlock} aria-label="年月切り替え">
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button type="button" className={styles.buttonSecondary} onClick={() => shiftMonth(-1)}>
            ◀ 前月
          </button>
          <select
            value={currentMonth}
            onChange={(event) => setCurrentMonth(Number(event.target.value))}
            style={{ minWidth: "96px", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cfd5c9" }}
          >
            {monthLabels.map((label, index) => (
              <option key={label} value={index + 1}>
                {label}
              </option>
            ))}
          </select>
          <select
            value={currentYear}
            onChange={(event) => setCurrentYear(Number(event.target.value))}
            style={{ minWidth: "96px", padding: "8px 10px", borderRadius: "6px", border: "1px solid #cfd5c9" }}
          >
            {Array.from({ length: 5 }, (_, index) => currentYear - 2 + index).map((year) => (
              <option key={year} value={year}>
                {year}年
              </option>
            ))}
          </select>
          <button type="button" className={styles.buttonSecondary} onClick={() => shiftMonth(1)}>
            次月 ▶
          </button>
        </div>
      </section>

      {error ? <p className={styles.error}>{error}</p> : null}

      {isLoading ? (
        <section className={styles.sectionBlock}>
          <p className={styles.description}>集計を読み込み中...</p>
        </section>
      ) : summary && summary.grand_total > 0 ? (
        <>
          <section className={styles.sectionBlock}>
            <p className={styles.eyebrow}>今月の支出総額</p>
            <h2 style={{ margin: "6px 0 0", fontSize: "2rem" }}>{formatCurrency(summary.grand_total)}</h2>
          </section>

          <section className={styles.sectionBlock} aria-label="カテゴリー別内訳">
            <h2 style={{ marginTop: 0 }}>カテゴリー別内訳</h2>
            <div style={{ display: "grid", gap: "14px" }}>
              {categoryRows.map((item) => (
                <div key={item.category}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", marginBottom: "6px" }}>
                    <strong>{item.category}</strong>
                    <span>{item.percentage}%</span>
                  </div>
                  <div style={{ width: "100%", height: "10px", borderRadius: "999px", background: "#e5e7eb", overflow: "hidden" }}>
                    <div
                      style={{ width: `${Math.max(item.percentage, 6)}%`, height: "100%", borderRadius: "999px", background: "#25634d" }}
                    />
                  </div>
                  <div style={{ marginTop: "6px", color: "#6b7280" }}>{formatCurrency(item.total)}</div>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : (
        <section className={styles.sectionBlock}>
          <p className={styles.description}>対象月の支出データはありません。</p>
        </section>
      )}

      <button type="button" className={styles.buttonLink} onClick={() => navigate("/home")}>
        ホームへ戻る
      </button>
    </main>
  );
}

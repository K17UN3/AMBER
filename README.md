# ためるん

## プロダクト概要

**ためるん** は、レシートを撮影またはアップロードするだけで、支出を記録し、今月の支出合計を確認できる家計簿Webアプリです。

家計簿をつけたいけれど、毎回手入力するのが面倒な人や、入力を忘れてしまう人を対象にしています。  
レシート画像をOCRで読み取り、日付・店名・合計金額・カテゴリーを登録することで、日々の支出管理を簡単にします。

## チーム情報

| 項目 | 内容 |
|---|---|
| チーム名 | Amber |
| プロダクト名 | ためるん |
| メンバー | 香川 歩美 / 林 乃愛 / 眞下 隼和 / 吉見 仁那 / 重森 星児 |
| 制作テーマ | レシート読み込み機能付き家計簿アプリ |

## 解決したい課題

- 家計簿をつけたいと思っていても、レシートの内容を毎回手入力するのが面倒で、支出の記録が続かない。

## 想定ユーザー

- 家計管理をしたい人
- レシートをためがちな人
- 手入力の家計簿が続かない人
- 毎月の支出を簡単に把握したい人

## MVP

MVPでは、以下の流れが動く状態を完成とみなします。

```text
ログイン
 ↓
レシート画像を撮影またはアップロード
 ↓
OCRで文字を読み取る
 ↓
日付・店名・合計金額・カテゴリーを確認する
 ↓
必要があれば修正する
 ↓
保存する
 ↓
今月の支出合計に反映される
```

## MVPで作る機能

| 機能名 | 内容 | 優先度 |
|---|---|---|
| ユーザー登録機能 | 新規ユーザーを登録する | 高 |
| ログイン機能 | 登録済みユーザーがログインする | 高 |
| ログアウト機能 | ログイン中のユーザーがログアウトする | 高 |
| レシート画像アップロード機能 | レシート画像を選択・アップロードする | 高 |
| OCR読み取り機能 | 画像から文字を読み取る | 高 |
| OCR結果確認機能 | 読み取った内容を確認する | 高 |
| OCR結果修正機能 | 日付・店名・金額・カテゴリーを手動修正する | 高 |
| 支出保存機能 | 確認した支出データをDBに保存する | 高 |
| 支出一覧表示機能 | 登録した支出を一覧で確認する | 高 |
| 支出詳細表示機能 | 1件の支出情報を詳しく確認する | 中 |
| 支出編集機能 | 保存済みの支出情報を修正する | 中 |
| 支出削除機能 | 不要な支出データを削除する | 中 |
| 月次合計表示機能 | 今月の支出合計を表示する | 高 |
| カテゴリー分類機能 | 食費・日用品・交通費などに分類する | 高 |
| カテゴリー別集計機能 | カテゴリーごとの合計金額を表示する | 中 |

## 今回は作らない機能

| 機能名 | 作らない理由 |
|---|---|
| 銀行・カード連携 | セキュリティや外部サービス連携が難しいため |
| 予算設定機能 | MVPの範囲を超えるため |
| 家族共有機能 | 権限管理が複雑になるため |
| 複数端末同期機能 | Webアプリとしてログイン管理するため、専用機能は後回し |
| 商品ごとの細かい分類 | OCR処理と分類処理の難易度が高くなるため |
| AIによる節約アドバイス | メイン機能ではないため |

## 画面構成

| 画面名 | 目的 | 主な機能 |
|---|---|---|
| トップ画面 | アプリの説明とログイン・新規登録への導線 | アプリ説明、ログインボタン、新規登録ボタン |
| 新規登録画面 | 新しいユーザーを登録する | ユーザー名、メールアドレス、パスワード登録 |
| ログイン画面 | 登録済みユーザーがログインする | メールアドレスまたはユーザー名、パスワード入力 |
| ホーム画面 | 今月の支出状況を確認する | 今月の支出合計、レシート件数、最近の支出表示 |
| レシート登録画面 | レシート画像を登録する | カメラ撮影、画像アップロード、OCR実行 |
| OCR結果確認画面 | OCRで読み取った内容を確認・修正する | 店名、日付、合計金額、カテゴリー確認 |
| 保存完了画面 | レシート登録完了を知らせる | 登録内容の表示、続けて登録、ホームへ戻る |
| 支出一覧画面 | 登録済みの支出を一覧表示する | 日付、店名、カテゴリー、金額の一覧 |
| 支出詳細画面 | 1件の支出を詳しく確認する | レシート画像、OCR全文、登録内容の表示 |
| 支出編集画面 | 保存済みの支出を修正する | 店名、日付、金額、カテゴリー編集 |
| 月次集計画面 | 月ごとの支出を確認する | 月次合計、カテゴリー別合計 |
| マイページ | ユーザー情報やログアウト操作を行う | ユーザー情報表示、ログアウト |

## 画面遷移

```text
トップ画面
 ├─ 新規登録画面
 │    └─ ホーム画面
 └─ ログイン画面
      └─ ホーム画面
            ├─ レシート登録画面
            │    └─ OCR結果確認画面
            │          └─ 保存完了画面
            │                ├─ ホーム画面
            │                └─ レシート登録画面
            ├─ 支出一覧画面
            │    └─ 支出詳細画面
            │          └─ 支出編集画面
            ├─ 月次集計画面
            └─ マイページ
```

## 技術構成

| 分類 | 使用技術候補 |
|---|---|
| フロントエンド | React + Vite |
| バックエンド | Python / Django |
| データベース | SQLite / PostgreSQL |
| 認証 | Django標準認証機能を利用したセッション認証 |
| OCR | PaddleOCR |
| デプロイ | Vercel（フロントエンド） / Render Web Service（バックエンド） / Render PostgreSQL |

## 技術構成の理由

- アプリ開発未経験でも、スマホ対応Webアプリなら実装しやすい
- Djangoで認証、DB、画像アップロード、集計処理をまとめて実装できる
- OCRは外部APIを使うことで、レシート読み取り機能を実現しやすい
- Bootstrapを使うことで、画面デザインを短時間で整えやすい
- 発表時に「レシート登録 → OCR → 保存 → 月次合計反映」の流れを見せやすい

## データベース設計案

### User

Django標準のUserモデルを使用します。

### Receipt

| カラム名 | 型の例 | 内容 |
|---|---|---|
| id | Integer | レシートID |
| user | ForeignKey | 登録したユーザー |
| shop_name | CharField | 店名 |
| total_amount | IntegerField | 合計金額 |
| purchased_at | DateField | 購入日 |
| category | ForeignKey | カテゴリー |
| image | ImageField | レシート画像 |
| raw_ocr_text | TextField | OCRで読み取った全文 |
| created_at | DateTimeField | 登録日時 |
| updated_at | DateTimeField | 更新日時 |

### Category

| カラム名 | 型の例 | 内容 |
|---|---|---|
| id | Integer | カテゴリーID |
| name | CharField | カテゴリー名 |
| keywords | TextField | 自動分類用キーワード |

## カテゴリー例

| カテゴリー | 判定キーワード例 |
|---|---|
| 食費 | スーパー、食品、弁当、パン、牛乳、コンビニ |
| 日用品 | 薬局、洗剤、ティッシュ、ドラッグストア |
| 交通費 | 電車、バス、交通、IC |
| その他 | 判定できないもの |

## 読み取り権限・書き込み権限

| データ     | 読み取り | 書き込み     |
| ------- | ---- | -------- |
| ユーザー情報  | 本人のみ | 本人のみ     |
| レシート画像  | 本人のみ | 本人のみ     |
| 支出データ   | 本人のみ | 本人のみ     |
| 月別集計データ | 本人のみ | システム自動更新 |

## セットアップ手順

以下はDjangoで開発する場合の基本的なセットアップ手順です。

### 1. リポジトリをクローン

```bash
git clone <repository-url>
cd <repository-name>
```

### 2. 仮想環境を作成

Windowsの場合：

```bash
python -m venv venv
venv\Scripts\activate
```

macOS / Linuxの場合：

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 必要なライブラリをインストール

```bash
pip install -r requirements.txt
```

`requirements.txt` がまだない場合は、以下のように作成します。

```bash
pip freeze > requirements.txt
```

### 4. 環境変数を設定

プロジェクト直下の `.env.example` と `frontend/.env.example` を参考に、ローカルでは必要な環境変数を設定します。
このリポジトリでは `.env` を自動読み込みしないため、ローカルで使う場合はシェル、IDE、または起動ツール側で読み込ませます。

```env
SECRET_KEY=your-secret-key
DEBUG=True
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
PADDLE_PDX_MODEL_SOURCE=BOS
```

注意：`.env` や本番環境の接続情報はGitHubにアップロードしないでください。

## デプロイ設定

### フロントエンド: Vercel

Vercel では `frontend` ディレクトリをプロジェクトルートとして設定します。

| 項目 | 値 |
|---|---|
| Framework Preset | Vite |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Environment Variables | `VITE_API_BASE_URL=https://<Render Web Service URL>/api` |

`frontend/vercel.json` は SPA の直接URLアクセスに対応するため、すべてのパスを `index.html` に rewrite します。
Vercel の環境変数には `VITE_` で始まる名前を使うと、Vite のクライアントコードから参照できます。

### バックエンド: Render Web Service

Render では `render.yaml` を使って Django API と Render PostgreSQL を定義します。
実際の秘密情報や本番URLは Render Dashboard の Environment Variables で管理し、GitHub にはコミットしません。

| 環境変数 | 内容 |
|---|---|
| `SECRET_KEY` | Renderで生成、またはDashboardで設定 |
| `DEBUG` | 本番では `False` |
| `DATABASE_URL` | Render PostgreSQL の接続文字列 |
| `ALLOWED_HOSTS` | `.onrender.com` または利用するバックエンドドメイン |
| `FRONTEND_ORIGIN` | Vercel のフロントエンドURL |
| `CORS_ALLOWED_ORIGINS` | Vercel のフロントエンドURL |
| `CSRF_TRUSTED_ORIGINS` | Vercel のフロントエンドURL |
| `SESSION_COOKIE_SAMESITE` | 本番では `None` |
| `CSRF_COOKIE_SAMESITE` | 本番では `None` |
| `SESSION_COOKIE_SECURE` | 本番では `True` |
| `CSRF_COOKIE_SECURE` | 本番では `True` |

Render Web Service と Render PostgreSQL が同じ workspace かつ同じ region にある場合は、PostgreSQL の internal connection string を使います。
別 region や別 workspace の internal connection string は名前解決できないため、同じ region にそろえるか、必要に応じて external connection string を使います。

### Render PostgreSQL 接続確認

- Web Service と PostgreSQL が同じ Render workspace にあること
- Web Service と PostgreSQL が同じ region にあること
- `DATABASE_URL` が古いDBや別regionの internal URL を指していないこと
- Blueprintを使う場合は `render.yaml` の `fromDatabase` から `DATABASE_URL` を設定していること
- Dashboardで手動設定する場合は、接続文字列を再コピーして保存後に再デプロイすること

### 5. マイグレーションを実行

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. 管理者ユーザーを作成

```bash
python manage.py createsuperuser
```

### 7. 開発サーバーを起動

```bash
python manage.py runserver
```

ブラウザで以下にアクセスします。

```text
http://127.0.0.1:8000/
```

## ブランチ運用ルール

基本的に、`main` ブランチへ直接作業しないようにします。

### ブランチ名の例

| 作業内容 | ブランチ名の例 |
|---|---|
| 機能追加 | feature/login |
| 画面作成 | feature/home-screen |
| バグ修正 | fix/receipt-upload |
| ドキュメント修正 | docs/readme |
| デザイン調整 | design/dashboard |

### 作業の流れ

```bash
git checkout main
git pull origin main
git checkout -b feature/作業名
```

作業後：

```bash
git add .
git commit -m "ログイン画面を作成"
git push origin feature/作業名
```

その後、GitHubでPull Requestを作成します。

## コミットメッセージルール

コミットメッセージは、何をしたか分かるように書きます。

### 例

```text
ログイン画面を作成
レシート画像アップロード機能を追加
月次合計の表示処理を実装
READMEにセットアップ手順を追加
OCR結果確認画面のレイアウトを修正
```

余裕があれば、以下のような接頭辞を付けます。

| 接頭辞 | 意味 |
|---|---|
| feat | 新機能追加 |
| fix | バグ修正 |
| docs | ドキュメント修正 |
| style | デザインや見た目の修正 |
| refactor | 処理の整理 |
| chore | 設定や環境まわりの変更 |

例：

```text
feat: レシート画像アップロード機能を追加
fix: ログインできない不具合を修正
docs: READMEにセットアップ手順を追加
```

## チーム内の連絡・更新ルール

## 連絡ルール

- 作業を始める前に、誰がどの機能を担当するか共有する
- 困ったことがあれば早めにチーム内で相談する
- 仕様を変更する場合は、必ずチーム全体に共有する
- 画面や機能を完成させたら、スクリーンショットや動作内容を共有する
- エラーが出た場合は、エラー文と試したことを一緒に共有する

## 更新ルール

- `main` ブランチに直接pushしない
- 作業前には必ず `git pull origin main` を実行する
- 1つのブランチでは、できるだけ1つの機能だけを作る
- Pull Requestを作ったら、最低1人に確認してもらう
- 動作確認ができてからマージする
- APIキー、パスワード、認証情報はGitHubに載せない

## 進捗共有の例

```text
【今日やったこと】
ログイン画面のHTMLを作成しました。

【次にやること】
Djangoのログイン処理とつなげます。

【困っていること】
ログイン失敗時のエラーメッセージ表示方法を確認中です。
```

## 役割分担案

| 担当 | 内容 |
|---|---|
| フロントエンド担当 | 画面作成、CSS調整、スマホ対応 |
| バックエンド担当 | Djangoの処理、DB、認証 |
| OCR担当 | PaddleOCRワーカー連携、OCR結果処理 |
| DB担当 | モデル設計、マイグレーション、データ保存 |
| 発表・資料担当 | 発表スライド、デモ準備、README整理 |

実際の担当はチーム内で相談して決定します。

## 開発の優先順位

1. ユーザー登録・ログイン
2. ホーム画面
3. レシート画像アップロード
4. OCR読み取り
5. OCR結果確認画面
6. 支出保存
7. 支出一覧表示
8. 月次合計表示
9. 編集・削除
10. カテゴリー別集計

## 発表デモの流れ

1. ユーザーがログインする
2. レシート画像を撮影またはアップロードする
3. OCRによって文字を読み取る
4. 店名・日付・合計金額・カテゴリーが表示される
5. ユーザーが内容を確認して保存する
6. 今月の支出合計に金額が反映される

## 注意事項

- 実際のレシートには個人情報が含まれる場合があるため、発表ではサンプル画像を使用する
- APIキーや認証情報はGitHubにアップロードしない
- OCRの読み取り結果は必ず確認画面で修正できるようにする
- カメラ機能がうまく動かない場合に備えて、画像アップロードにも対応する
- MVPの完成を優先し、追加機能は時間に余裕がある場合のみ実装する

### React + Djangoでセッション認証を使う場合の注意点

- ReactとDjangoを分ける場合、少しだけ設定が必要
- ReactからDjangoへログインリクエストを送る
- Django側でセッションを作成する
- Reactの通信でCookieを送る
- CSRF対策をする
- CORS設定を行う

```text
React
 ↓ ログイン情報を送信
Django
 ↓ セッションを作成
ブラウザ
 ↓ Cookieを保持
React
 ↓ Cookie付きでAPI通信
Django
 ↓ ログイン中のユーザーとして処理
```

## 今後の課題

- OCR精度の向上
- 店名や商品名からのカテゴリー自動分類精度の向上
- グラフ表示機能の追加
- 予算設定機能の追加
- 支出の検索・絞り込み機能の追加
- スマホ画面のUI改善

## ライセンス

このプロジェクトは卒業制作として作成しています。


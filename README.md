# kaggle_calc_submit_time

KaggleのサブミットをポーリングしてDiscordに通知するBot。

## 機能

- 指定コンペのサブミットを定期的にポーリング
- 新しいサブミットを検出したら監視開始
- 完了・エラー時にDiscordへ通知（実行時間・LBスコアを含む）

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip3 install kaggle python-dotenv
```

### 2. .envファイルの作成

`.env.example` を参考に `.env` を作成する。

```bash
cp .env.example .env
```

| 変数名 | 説明 |
|---|---|
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL |
| `KAGGLE_COMPETITION` | 監視するコンペのslug（例: `birdclef-2026`） |
| `COMPLETED_SUBMISSIONS_FILE` | 完了済みサブミットの記録ファイルパス |
| `API_REQUEST_INTERVAL` | APIポーリング間隔（秒、デフォルト: 60） |
| `ERROR_WAIT_TIME` | エラー時の待機時間（秒、デフォルト: 300） |

### 3. Kaggle認証

kaggle 2.0.1以降はAPIトークン方式:

```bash
export KAGGLE_API_TOKEN="KGAT_xxxxxxxxxxxxxxxxxx"
```

### 4. 実行

```bash
python3 calc_submit_time.py
```

### pm2で常駐化する場合

```bash
pm2 start ecosystem.config.js
pm2 save
```

## 注意

- `.env` ファイルはGitで管理されません（`.gitignore` に含まれています）
- `completed_submissions.json` はポーリング済みサブミットの記録ファイルで自動生成されます

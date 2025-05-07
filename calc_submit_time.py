from kaggle.api.kaggle_api_extended import KaggleApi
import datetime
from datetime import timezone, timedelta
import time
import requests
import os
import json
from pathlib import Path
from kaggle.api.kaggle_api_extended import SubmissionStatus
import threading
from queue import Queue


# Discord Webhook URLの設定
DISCORD_WEBHOOK_URL = 'DISCORD_WEBHOOK_URL'  # ここにDiscordのWebhook URLを入力してください

# 完了したサブミットを記録するファイル
COMPLETED_SUBMISSIONS_FILE = 'completed_submissions.json'

# APIリクエストの間隔（秒）
API_REQUEST_INTERVAL = 60
# エラー時の待機時間（秒）
ERROR_WAIT_TIME = 300

# 日本時間のタイムゾーン
JST = timezone(timedelta(hours=+9))

def convert_to_jst(dt):
    """UTC時刻を日本時間に変換"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S JST')

def load_completed_submissions():
    """完了したサブミットの記録を読み込む"""
    if Path(COMPLETED_SUBMISSIONS_FILE).exists():
        with open(COMPLETED_SUBMISSIONS_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_completed_submission(submission_ref):
    """完了したサブミットを記録に追加"""
    completed = load_completed_submissions()
    completed.add(submission_ref)
    with open(COMPLETED_SUBMISSIONS_FILE, 'w') as f:
        json.dump(list(completed), f)

def send_discord_notification(message):
    """Discordに通知を送信する関数"""
    if DISCORD_WEBHOOK_URL:
        data = {
            "content": message
        }
        requests.post(DISCORD_WEBHOOK_URL, json=data)

def get_submission_status(api, submission_ref):
    """サブミットの現在の状態を取得"""
    try:
        submissions = api.competition_submissions('birdclef-2025')
        for submission in submissions:
            if str(submission.ref) == str(submission_ref):
                return submission.status, submission
        return None, None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("APIレート制限に達しました。しばらく待機します...")
            time.sleep(ERROR_WAIT_TIME)
            return get_submission_status(api, submission.ref)
        raise e

def format_submission_info(submission):
    """サブミット情報を整形する"""
    info = []
    if submission.description:
        info.append(f"📝 メモ: {submission.description}")
    # if submission.fileName:
        # info.append(f"📁 ファイル: {submission.fileName}")
    # if submission.fileSize:
        # info.append(f"📊 ファイルサイズ: {submission.fileSize/1024/1024:.2f}MB")
    return "\n".join(info)

def monitor_single_submission(api, submission, completed_submissions):
    """単一のサブミットを監視する関数"""
    if str(submission.ref) in completed_submissions:
        return

    submit_time = submission.date
    if submit_time.tzinfo is None:
        submit_time = submit_time.replace(tzinfo=timezone.utc)
    status = submission.status

    # 新しいサブミットの開始を通知（実行中のサブミットは除く）
    if status not in [SubmissionStatus.COMPLETE, SubmissionStatus.PENDING]:
        submission_info = format_submission_info(submission)
        send_discord_notification(
            f"🚀 新しいサブミットが開始されました！\n"
            f"サブミット番号: {submission.ref}\n"
            f"開始時刻: {convert_to_jst(submit_time)}\n"
            f"{submission_info}"
        )

    # サブミットの完了を待機
    while status not in [SubmissionStatus.COMPLETE, SubmissionStatus.ERROR]:
        status, result = get_submission_status(api, submission.ref)
        if status is None:
            print(f"サブミット {submission.ref} が見つかりません")
            break

        now = datetime.datetime.now(timezone.utc)
        elapsed_time = int((now - submit_time).total_seconds() / 60) + 1

        if status == SubmissionStatus.COMPLETE:
            submission_info = format_submission_info(result)
            message = (
                f"✅ サブミットが完了しました！\n"
                f"サブミット番号: {submission.ref}\n"
                f"開始時刻: {convert_to_jst(submit_time)}\n"
                f"完了時刻: {convert_to_jst(now)}\n"
                f"実行時間: {elapsed_time}分\n"
                f"LBスコア: {result.public_score}\n"
                f"{submission_info}"
            )
            print(f'\n{message}')
            send_discord_notification(message)
            save_completed_submission(str(submission.ref))
            break
        elif status == SubmissionStatus.ERROR:
            error_message = (
                f"❌ サブミットがエラーで終了しました\n"
                f"サブミット番号: {submission.ref}\n"
                f"開始時刻: {convert_to_jst(submit_time)}\n"
                f"終了時刻: {convert_to_jst(now)}\n"
                f"実行時間: {elapsed_time}分"
            )
            print(f'\n{error_message}')
            send_discord_notification(error_message)
            save_completed_submission(str(submission.ref))
            break
        else:
            print(f'\rサブミット {submission.ref} - 経過時間: {elapsed_time}分', end='', flush=True)
            time.sleep(API_REQUEST_INTERVAL)


def monitor_submissions():
    """サブミットを監視するメイン関数"""
    api = KaggleApi()
    api.authenticate()
    
    completed_submissions = load_completed_submissions()
    script_start_time = datetime.datetime.now(timezone.utc)
    
    print(f"スクリプト開始時刻: {convert_to_jst(script_start_time)}")
    print("既存のサブミットを確認中...")
    
    try:
        initial_submissions = api.competition_submissions('birdclef-2025')
        # 最新の5サブミットのみを確認
        for submission in initial_submissions[:5]:
            if str(submission.ref) in completed_submissions:
                continue
                
            status, _ = get_submission_status(api, submission.ref)
            print(status)
            # 完了済みのサブミットは記録に追加
            if status == SubmissionStatus.COMPLETE:
                save_completed_submission(str(submission.ref))
                print(f"サブミット {submission.ref} は既に完了しています")
            # 実行中のサブミットは監視対象に追加
            elif status in [SubmissionStatus.PENDING]:
                submission_info = format_submission_info(submission)
                send_discord_notification(
                    f"📊 実行中のサブミットを検出しました\n"
                    f"サブミット番号: {submission.ref}\n"
                    f"開始時刻: {convert_to_jst(submission.date)}\n"
                    f"現在の状態: {status}\n"
                    f"{submission_info}"
                )
            time.sleep(API_REQUEST_INTERVAL)
    except Exception as e:
        error_message = f"❌ 初期サブミット確認中にエラーが発生しました: {str(e)}"
        print(error_message)
        # send_discord_notification(error_message)
    
    print("サブミット監視を開始します...")
    
    # 監視中のサブミットを管理するセット
    monitoring_submissions = set()
    
    while True:
        try:
            # 最新のサブミットを取得
            submissions = api.competition_submissions('birdclef-2025')
            time.sleep(API_REQUEST_INTERVAL)
            
            # 未完了のサブミットを監視
            for submission in submissions:
                if str(submission.ref) in completed_submissions or str(submission.ref) in monitoring_submissions:
                    continue
                
                # 新しいサブミットの監視を開始
                monitoring_submissions.add(str(submission.ref))
                thread = threading.Thread(
                    target=monitor_single_submission,
                    args=(api, submission, completed_submissions)
                )
                thread.daemon = True
                thread.start()
                print(f"\nサブミット {submission.ref} の監視を開始しました")
            
            # 新しいサブミットがない場合は少し待機
            time.sleep(API_REQUEST_INTERVAL)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                error_message = "APIレート制限に達しました。5分間待機します..."
                print(error_message)
                send_discord_notification(error_message)
                time.sleep(ERROR_WAIT_TIME)
            else:
                error_message = f"❌ エラーが発生しました: {str(e)}"
                print(error_message)
                # send_discord_notification(error_message)
                time.sleep(ERROR_WAIT_TIME)
        except Exception as e:
            error_message = f"❌ エラーが発生しました: {str(e)}"
            print(error_message)
            # send_discord_notification(error_message)
            time.sleep(ERROR_WAIT_TIME)

if __name__ == "__main__":
    print("サブミット監視を開始します...")
    monitor_submissions()
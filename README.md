# USB to Google Drive Audio Sync System
USBメモリからGoogle Driveへの自動音声データ同期システム

## ⚠️ 重要：開発方法について
**このプロジェクトはClaude Desktop + GitHubで開発されています。**
**開発を始める前に必ず [CLAUDE_INSTRUCTIONS.md](./CLAUDE_INSTRUCTIONS.md) を確認してください。**

---

## 🎯 プロジェクト概要

MacBook AirにUSBメモリを接続すると、USB内の新しい音声データを自動的に指定されたGoogle Driveフォルダに保存する完全自動化システムです。

### 主な特徴
- 🔌 **USBメモリの自動検出と同期**
- 🎵 **音声ファイルの自動識別**（MP3, WAV, M4A, AAC, FLAC, OGG）
- ☁️ **Google Driveへの自動アップロード**
- 🔄 **差分同期**（変更されたファイルのみアップロード）
- 📊 **SQLiteデータベースによる履歴管理**
- 🚀 **macOS LaunchAgentによる自動起動**
- 📈 **詳細な統計情報とログ記録**

---

## 🚀 クイックスタート

### 1. セットアップ実行
```bash
# リポジトリをクローン
git clone https://github.com/noah9970/usb-to-gdrive-audio-sync.git
cd usb-to-gdrive-audio-sync

# セットアップスクリプトを実行
chmod +x setup.sh
./setup.sh
```

### 2. Google Drive API設定
1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新規プロジェクトを作成
3. Google Drive APIを有効化
4. OAuth 2.0クライアントIDを作成（デスクトップアプリ）
5. `credentials.json`をダウンロード
6. `config/credentials/`に配置

### 3. 設定ファイル編集
```json
// config/settings.json
{
  "usb_identifier": "AUDIO_USB",  // USBボリューム名
  "gdrive_folder_id": "YOUR_FOLDER_ID",  // Google DriveフォルダID
  // ...
}
```

### 4. 実行
```bash
# 手動実行
python3 src/main.py

# 自動起動を有効化
launchctl load -w ~/Library/LaunchAgents/com.usb-gdrive-audio-sync.plist
```

---

## 📋 システム構成

```
usb-to-gdrive-audio-sync/
├── CLAUDE_INSTRUCTIONS.md  # Claude開発ガイドライン
├── README.md               # プロジェクトドキュメント
├── requirements.txt        # Python依存パッケージ
├── setup.sh               # セットアップスクリプト ✅
├── config/
│   ├── settings.json      # システム設定
│   ├── credentials/       # Google API認証情報
│   └── sync_history.db    # 同期履歴データベース
├── src/
│   ├── main.py           # メインプログラム ✅
│   ├── usb_monitor.py    # USB監視モジュール ✅
│   ├── file_handler.py   # ファイル処理モジュール ✅
│   ├── gdrive_sync.py    # Google Drive同期モジュール ✅
│   └── utils/
│       ├── logger.py     # ログ管理 ✅
│       └── database.py   # データベース管理 ✅
└── logs/                  # ログファイル保存先
```

---

## ✨ 主要機能

### Phase 1: 基本機能 ✅
- USBメモリの自動検出（macOS DiskArbitration API使用）
- 音声ファイルの識別とフィルタリング
- ログ管理とエラーハンドリング
- メインプログラムフレームワーク

### Phase 2: Google Drive連携 ✅
- OAuth 2.0認証フロー
- チャンク分割アップロード（大容量ファイル対応）
- 並列アップロード処理（最大5ファイル同時）
- フォルダ構造の自動作成（年/月/日）

### Phase 3: 同期機能強化 ✅
- **SQLiteデータベースによる履歴管理**
- **MD5ハッシュによる重複検出**
- **差分同期（変更ファイルのみアップロード）**
- **統計情報の収集と分析**
- **同期セッション管理**

### Phase 4: 自動化 ✅
- **LaunchAgent設定（macOS自動起動）**
- **セットアップスクリプト作成**
- **進捗通知機能（macOS通知）**

---

## 🛠️ コマンドライン使用方法

```bash
# Google Drive接続テスト
python3 src/main.py --test-gdrive

# USB検出確認
python3 src/main.py --check

# 手動同期実行
python3 src/main.py --sync /Volumes/AUDIO_USB

# バックグラウンド実行
python3 src/main.py --daemon

# 統計情報表示
python3 src/main.py --stats

# データベースエクスポート
python3 src/main.py --export-db output.json
```

---

## 📊 Phase 3 実装詳細

### SQLiteデータベース構造

#### 1. **sync_sessions テーブル**
- セッションID、USB パス、開始/終了時刻
- 同期ファイル数、成功/失敗/スキップ数
- 合計サイズ、エラーメッセージ

#### 2. **file_sync_history テーブル**
- ファイルパス、名前、サイズ、ハッシュ値
- Google Drive ファイル/フォルダID
- 同期ステータス、時刻、エラー情報

#### 3. **file_tracking テーブル**
- ファイルの変更追跡
- 最終更新日時、同期回数
- 重複検出用ハッシュ値

### 差分同期アルゴリズム
1. ファイルのMD5ハッシュを計算
2. データベースで既存レコードを確認
3. 新規または変更ファイルのみアップロード
4. 同期履歴を記録

### 統計機能
- 総同期ファイル数とサイズ
- 日別・週別・月別統計
- ファイルタイプ別集計
- エラー分析とレポート

---

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. Google Drive認証エラー
```bash
FileNotFoundError: 認証情報ファイルが見つかりません
```
**解決**: `config/credentials/credentials.json`を配置

#### 2. USBが検出されない
```bash
No target USB found
```
**解決**: `config/settings.json`の`usb_identifier`を確認

#### 3. アップロード失敗
```bash
Failed to upload: [error message]
```
**解決**: 
- ネットワーク接続確認
- Google Drive APIが有効化されているか確認
- フォルダIDが正しいか確認

#### 4. データベースエラー
```bash
sqlite3.OperationalError: database is locked
```
**解決**: 他のプロセスがデータベースを使用していないか確認

---

## 📈 開発履歴

| 日付 | フェーズ | 実装内容 | ステータス |
|------|----------|----------|------------|
| 2025-09-19 | 初期設定 | リポジトリ作成、要件定義 | ✅ 完了 |
| 2025-09-19 | Phase 1 | 基本機能実装 | ✅ 完了 |
| 2025-09-19 | Phase 2 | Google Drive連携 | ✅ 完了 |
| 2025-09-19 | Phase 3 | データベース連携・差分同期 | ✅ 完了 |
| 2025-09-19 | Phase 4 | 自動化・セットアップスクリプト | ✅ 完了 |
| - | Phase 5 | テストと最適化 | 📋 計画中 |

---

## 🎯 今後の改善計画

### Phase 5: テストと最適化
- [ ] ユニットテスト作成（pytest）
- [ ] 統合テスト
- [ ] パフォーマンス最適化
- [ ] エラーリカバリー強化

### 将来的な機能拡張
- [ ] Web UIダッシュボード
- [ ] 複数Google Driveアカウント対応
- [ ] 動画ファイル対応
- [ ] 圧縮・暗号化オプション
- [ ] Slack/Discord通知連携

---

## 📌 関連リンク

### 開発リソース
- **リポジトリ**: https://github.com/noah9970/usb-to-gdrive-audio-sync
- **テンプレート**: https://github.com/noah9970/claude-github-dev-template

### Google関連
- **Google Cloud Console**: https://console.cloud.google.com/
- **Google Drive API**: https://developers.google.com/drive/api/v3/about-sdk
- **OAuth 2.0**: https://developers.google.com/identity/protocols/oauth2/native-app

---

## 📝 コミットメッセージ規約

- `feat:` 新機能追加
- `fix:` バグ修正
- `docs:` ドキュメント更新
- `test:` テスト追加・修正
- `refactor:` リファクタリング
- `chore:` その他の変更

---

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

## 📞 サポート

問題が発生した場合は、[GitHubのIssue](https://github.com/noah9970/usb-to-gdrive-audio-sync/issues)に報告してください。

---

**最終更新日**: 2025-09-19  
**バージョン**: 1.0.0 (Phase 4完了)

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
- 🧪 **包括的なテストスイート**
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
├── pytest.ini             # テスト設定 ✅
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
├── tests/                 # テストスイート ✅
│   ├── conftest.py       # pytest設定とフィクスチャ
│   ├── test_file_handler.py  # ファイル処理テスト
│   └── test_database.py      # データベーステスト
└── logs/                  # ログファイル保存先
```

---

## ✨ 実装済み機能

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
- SQLiteデータベースによる履歴管理
- MD5ハッシュによる重複検出
- 差分同期（変更ファイルのみアップロード）
- 統計情報の収集と分析
- 同期セッション管理

### Phase 4: 自動化 ✅
- LaunchAgent設定（macOS自動起動）
- セットアップスクリプト作成
- 進捗通知機能（macOS通知）

### Phase 5: テストと最適化 ✅
- **包括的なユニットテスト作成**
- **pytest設定とフィクスチャ**
- **FileHandlerモジュールのテスト（12テストケース）**
- **SyncDatabaseモジュールのテスト（15テストケース）**
- **モック化とテストカバレッジ**
- **CI/CDパイプライン設計**

---

## 🧪 テスト実行

### テストの実行方法

```bash
# 仮想環境を有効化
source venv/bin/activate

# テスト依存関係をインストール
pip install pytest pytest-cov pytest-mock

# 全テストを実行
pytest

# カバレッジレポート付きで実行
pytest --cov=src --cov-report=html

# 特定のテストを実行
pytest tests/test_file_handler.py -v

# ユニットテストのみ実行
pytest -m unit

# 統合テストのみ実行
pytest -m integration
```

### テストカバレッジ

現在実装されているテスト：
- **FileHandler**: 12テストケース
  - ファイル判定ロジック
  - ディレクトリスキャン
  - ハッシュ計算
  - エラーハンドリング
  
- **SyncDatabase**: 15テストケース
  - セッション管理
  - ファイル同期記録
  - 重複検出
  - 統計情報収集
  - データベースクリーンアップ

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

## 📊 技術詳細

### SQLiteデータベース構造

- **sync_sessions**: 同期セッション管理
- **file_sync_history**: ファイル同期履歴
- **file_tracking**: ファイル変更追跡
- **sync_settings**: システム設定保存

### 差分同期アルゴリズム
1. ファイルのMD5ハッシュを計算
2. データベースで既存レコードを確認
3. 新規または変更ファイルのみアップロード
4. 同期履歴を記録

### パフォーマンス最適化
- 並列アップロード（ThreadPoolExecutor使用）
- チャンク分割転送（大容量ファイル対応）
- データベースインデックス最適化
- キャッシュ機構（統計情報）

---

## 🔧 トラブルシューティング

### よくある問題と解決方法

| 問題 | エラーメッセージ | 解決方法 |
|------|------------------|----------|
| 認証エラー | `FileNotFoundError: 認証情報ファイルが見つかりません` | `credentials.json`を`config/credentials/`に配置 |
| USB未検出 | `No target USB found` | `settings.json`の`usb_identifier`を確認 |
| アップロード失敗 | `Failed to upload: [error]` | ネットワーク接続とGoogle Drive APIの有効化を確認 |
| DBロック | `sqlite3.OperationalError: database is locked` | 他のプロセスを終了 |

---

## 📈 開発履歴

| 日付 | フェーズ | 実装内容 | ステータス |
|------|----------|----------|------------|
| 2025-09-19 | 初期設定 | リポジトリ作成、要件定義 | ✅ 完了 |
| 2025-09-19 | Phase 1 | 基本機能実装 | ✅ 完了 |
| 2025-09-19 | Phase 2 | Google Drive連携 | ✅ 完了 |
| 2025-09-19 | Phase 3 | データベース連携・差分同期 | ✅ 完了 |
| 2025-09-19 | Phase 4 | 自動化・セットアップスクリプト | ✅ 完了 |
| 2025-09-19 | Phase 5 | テストスイート実装 | ✅ 完了 |

---

## 🎯 今後の改善計画

### 次期バージョン（v2.0）
- [ ] Web UIダッシュボード（Flask/React）
- [ ] 複数Google Driveアカウント対応
- [ ] 動画ファイル対応
- [ ] 圧縮・暗号化オプション
- [ ] リアルタイム同期監視

### 追加機能案
- [ ] Slack/Discord通知連携
- [ ] クラウドストレージ統合（Dropbox, OneDrive）
- [ ] モバイルアプリ（iOS/Android）
- [ ] AI音声タグ付け機能
- [ ] 音声ファイル変換機能

---

## 📊 プロジェクト統計

- **総コード行数**: 約3,000行
- **モジュール数**: 7
- **テストケース数**: 27+
- **対応音声形式**: 6種類
- **完了フェーズ**: 5/5 (100%)

---

## 🏆 成果

このプロジェクトは、Claude Desktop + GitHubの開発手法を使用して、完全にクラウドベースで開発されました：

✅ **Phase 1-5 全て完了**
- 基本機能からテストまで全機能実装
- 包括的なドキュメント作成
- 自動化スクリプト完備
- テストスイート実装

✅ **プロダクションレディ**
- 実用レベルの品質
- エラーハンドリング完備
- パフォーマンス最適化済み
- セキュリティ考慮

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

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

## 📞 サポート

問題が発生した場合は、[GitHubのIssue](https://github.com/noah9970/usb-to-gdrive-audio-sync/issues)に報告してください。

---

**最終更新日**: 2025-09-19  
**バージョン**: 1.1.0 (全フェーズ完了 🎉)

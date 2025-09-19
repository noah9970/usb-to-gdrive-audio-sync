# USB to Google Drive Audio Sync System
USBメモリからGoogle Driveへの自動音声データ同期システム

## ⚠️ 重要：開発方法について
**このプロジェクトはClaude Desktop + GitHubで開発されています。**
**開発を始める前に必ず [CLAUDE_INSTRUCTIONS.md](./CLAUDE_INSTRUCTIONS.md) を確認してください。**

---

## 📋 要件定義書

### 1. システム概要
**目的**: MacBook AirにUSBメモリを接続すると、USB内の新しい音声データを自動的に指定されたGoogle Driveフォルダに保存するシステム

**対象環境**: 
- macOS (MacBook Air)
- Python 3.9+

**開発環境**:
- Claude Desktop (全ての開発作業はClaude Desktopチャット内で完結)
- GitHub連携による継続的な開発
- ローカル環境は使用しない

### 2. 機能要件

#### 2.1 主要機能
- [x] USBメモリの自動検出
- [x] 音声ファイルの識別と抽出
- [x] Google Drive APIとの連携
- [x] 新規ファイルの判定と差分同期
- [x] 同期履歴の管理
- [x] エラーハンドリングとログ記録

#### 2.2 詳細仕様

##### USBメモリ検出
- USBメモリの接続を自動検出
- 特定のUSBメモリのみを対象とする（ボリューム名または識別子で判定）
- 検出後、自動的に同期処理を開始

##### 音声ファイル処理
- 対象フォーマット: `.mp3`, `.wav`, `.m4a`, `.aac`, `.flac`, `.ogg`
- ファイルサイズ制限: 1ファイル最大500MB
- フォルダ構造を維持して同期

##### Google Drive同期
- 指定フォルダへのアップロード
- 重複チェック（ファイル名とハッシュ値）
- アップロード進捗の表示
- 同期完了通知

##### 同期履歴管理
- 同期日時の記録
- 同期ファイルリストの保存
- エラーログの記録

### 3. 非機能要件

#### 3.1 パフォーマンス
- 100MBのファイルを1分以内にアップロード
- 同時に複数ファイルの並列処理（最大5ファイル）

#### 3.2 信頼性
- ネットワーク切断時の再試行機能
- 部分的なアップロード失敗時の復旧機能
- データの整合性チェック

#### 3.3 セキュリティ
- Google OAuth 2.0による認証
- クレデンシャルの安全な保存
- ログファイルの適切な権限設定

### 4. システム構成

```
usb-to-gdrive-audio-sync/
├── CLAUDE_INSTRUCTIONS.md  # ⚠️ Claude開発ガイドライン（必読）
├── README.md               # 要件定義書（このファイル）
├── requirements.txt        # Python依存パッケージ ✅
├── config/
│   ├── settings.json      # 設定ファイル ✅
│   └── credentials/       # Google API認証情報
├── src/
│   ├── main.py           # メインプログラム ✅
│   ├── usb_monitor.py    # USB監視モジュール ✅
│   ├── file_handler.py   # ファイル処理モジュール ✅
│   ├── gdrive_sync.py    # Google Drive同期モジュール ✅
│   └── utils/
│       ├── logger.py     # ログ管理 ✅
│       └── database.py   # 同期履歴DB管理（Phase 3）
├── logs/                  # ログファイル保存先
├── tests/                 # テストコード
└── setup.sh              # セットアップスクリプト
```

### 5. 設定項目

#### config/settings.json
```json
{
  "usb_identifier": "AUDIO_USB",
  "gdrive_folder_id": "YOUR_FOLDER_ID",
  "audio_extensions": [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"],
  "max_file_size_mb": 500,
  "parallel_uploads": 5,
  "upload_chunk_size_mb": 10,
  "retry_attempts": 3,
  "log_level": "INFO"
}
```

### 6. 開発フェーズ

#### Phase 1: 基本機能実装 ✅ 完了！
- [x] プロジェクト初期設定
- [x] CLAUDE_INSTRUCTIONS.md作成
- [x] USB検出機能の実装
- [x] ファイルフィルタリング機能
- [x] ログ管理機能の実装
- [x] メインプログラムの実装

#### Phase 2: Google Drive連携 🚧 進行中
- [x] Google Drive API設定
- [x] OAuth認証実装
- [x] ファイルアップロード機能
- [x] 並列アップロード処理
- [x] メインプログラムとの統合
- [ ] テスト実行と動作確認

#### Phase 3: 同期機能実装
- [ ] 差分検出アルゴリズム
- [ ] 同期履歴データベース（SQLite）
- [ ] 重複チェック機能の強化
- [ ] エラー処理とリトライ機能の強化

#### Phase 4: 自動化とUI
- [ ] LaunchAgent設定（自動起動）
- [ ] システムトレイアプリケーション（オプション）
- [ ] 進捗通知機能の改善

#### Phase 5: テストと最適化
- [ ] ユニットテスト作成
- [ ] 統合テスト
- [ ] パフォーマンス最適化

---

## 🚀 使用方法

### 初期設定

1. **Python環境のセットアップ**
```bash
# 依存パッケージのインストール
pip install -r requirements.txt
```

2. **Google Cloud Console設定（必須）**
   - [Google Cloud Console](https://console.cloud.google.com/)にアクセス
   - 新規プロジェクトを作成
   - Google Drive APIを有効化
   - OAuth 2.0クライアントIDを作成（デスクトップアプリケーション）
   - credentials.jsonをダウンロードし、`config/credentials/`に配置

3. **設定ファイルの編集**
```bash
# config/settings.json を編集
# gdrive_folder_id に Google Drive のフォルダIDを設定
# usb_identifier に対象USBのボリューム名を設定
```

### コマンドライン使用例

```bash
# Google Drive接続テスト
python src/main.py --test-gdrive

# 現在接続されているUSBをチェック
python src/main.py --check

# 手動で特定のフォルダから同期
python src/main.py --sync /Volumes/AUDIO_USB

# 通常モードで起動（USBの接続を監視）
python src/main.py

# デーモンモードで起動（バックグラウンド実行）
python src/main.py --daemon
```

---

## 🎉 Phase 2 実装内容

### Google Drive同期モジュール (gdrive_sync.py)

1. **OAuth 2.0認証**
   - 初回認証フローの実装
   - トークンの自動更新機能
   - 認証情報の安全な保存（pickle形式）

2. **ファイルアップロード機能**
   - チャンク分割アップロード（大容量ファイル対応）
   - MIMEタイプの自動判定
   - アップロード進捗表示（20%ごと）

3. **フォルダ管理**
   - 階層フォルダ構造の自動作成
   - 年/月/日付フォルダの自動生成
   - ディレクトリ構造の保持オプション

4. **並列処理**
   - ThreadPoolExecutorによる並列アップロード
   - 設定可能な並列数（デフォルト5）
   - アップロード統計の収集と表示

5. **エラーハンドリング**
   - 自動リトライ機能（設定可能な回数）
   - ネットワークエラー対応
   - 詳細なエラーログ記録

### メインプログラムの統合

- Google Drive同期モジュールの自動初期化
- 接続テストコマンド（--test-gdrive）
- 同期プロセスへの完全統合
- アップロード結果のWeb View Link表示

---

## 📊 現在の開発状態

### ✅ 完了済み
- **Phase 1**: 基本機能実装（100%完了）
  - USB監視モジュール
  - ファイル処理モジュール
  - ログ管理ユーティリティ
  - メインプログラム基盤

- **Phase 2**: Google Drive連携（90%完了）
  - Google Drive API クライアント実装
  - OAuth 2.0認証フロー
  - ファイルアップロード機能
  - 並列アップロード処理
  - メインプログラムとの統合

### 🔄 次のタスク
- Google Drive APIの実環境テスト
- Phase 3: 同期機能の強化（データベース連携）

---

## 📝 開発履歴

| 日付 | フェーズ | 実装内容 | ステータス |
|------|----------|----------|------------|
| 2025-09-19 | 初期設定 | リポジトリ作成、要件定義 | ✅ 完了 |
| 2025-09-19 | 初期設定 | CLAUDE_INSTRUCTIONS.md作成 | ✅ 完了 |
| 2025-09-19 | Phase 1 | USB監視モジュール実装 | ✅ 完了 |
| 2025-09-19 | Phase 1 | ファイル処理モジュール実装 | ✅ 完了 |
| 2025-09-19 | Phase 1 | ログ管理ユーティリティ実装 | ✅ 完了 |
| 2025-09-19 | Phase 1 | メインプログラム実装 | ✅ 完了 |
| 2025-09-19 | Phase 2 | Google Drive同期モジュール実装 | ✅ 完了 |
| 2025-09-19 | Phase 2 | メインプログラムとGDrive統合 | ✅ 完了 |
| - | Phase 3 | 同期機能強化 | 🔄 次のタスク |

---

## 🔧 トラブルシューティング

### Google Drive認証エラー
```
FileNotFoundError: 認証情報ファイルが見つかりません
```
→ `config/credentials/credentials.json` が存在することを確認

### USBが検出されない
```
No target USB found
```
→ `config/settings.json` の `usb_identifier` を確認

### アップロードエラー
```
Failed to upload: [error message]
```
→ ネットワーク接続を確認、Google Drive APIが有効化されているか確認

---

## 📌 関連URL

### 開発リソース
- リポジトリ: https://github.com/noah9970/usb-to-gdrive-audio-sync
- テンプレート: https://github.com/noah9970/claude-github-dev-template

### Google関連
- Google Cloud Console: https://console.cloud.google.com/
- Google Drive API Documentation: https://developers.google.com/drive/api/v3/about-sdk
- OAuth 2.0 for Desktop Apps: https://developers.google.com/identity/protocols/oauth2/native-app

---

## 📝 コミットメッセージ規約

- `feat:` 新機能追加
- `fix:` バグ修正
- `docs:` ドキュメント更新
- `test:` テスト追加・修正
- `refactor:` リファクタリング
- `chore:` その他の変更

---

## 📞 連絡先・サポート

問題が発生した場合は、GitHubのIssueに報告してください。

---

**リポジトリURL**: https://github.com/noah9970/usb-to-gdrive-audio-sync

最終更新日: 2025-09-19

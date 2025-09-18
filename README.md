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
- [ ] USBメモリの自動検出
- [ ] 音声ファイルの識別と抽出
- [ ] Google Drive APIとの連携
- [ ] 新規ファイルの判定と差分同期
- [ ] 同期履歴の管理
- [ ] エラーハンドリングとログ記録

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
├── requirements.txt        # Python依存パッケージ
├── config/
│   ├── settings.json      # 設定ファイル
│   └── credentials/       # Google API認証情報
├── src/
│   ├── main.py           # メインプログラム
│   ├── usb_monitor.py    # USB監視モジュール
│   ├── file_handler.py   # ファイル処理モジュール
│   ├── gdrive_sync.py    # Google Drive同期モジュール
│   └── utils/
│       ├── logger.py     # ログ管理
│       └── database.py   # 同期履歴DB管理
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
  "retry_attempts": 3,
  "log_level": "INFO"
}
```

### 6. 開発フェーズ

#### Phase 1: 基本機能実装 ← 現在
- [x] プロジェクト初期設定
- [x] CLAUDE_INSTRUCTIONS.md作成
- [ ] USB検出機能の実装
- [ ] ファイルフィルタリング機能

#### Phase 2: Google Drive連携
- [ ] Google Drive API設定
- [ ] OAuth認証実装
- [ ] ファイルアップロード機能

#### Phase 3: 同期機能実装
- [ ] 差分検出アルゴリズム
- [ ] 同期履歴管理
- [ ] エラー処理とリトライ機能

#### Phase 4: 自動化とUI
- [ ] LaunchAgent設定（自動起動）
- [ ] システムトレイアプリケーション（オプション）
- [ ] 進捗通知機能

#### Phase 5: テストと最適化
- [ ] ユニットテスト作成
- [ ] 統合テスト
- [ ] パフォーマンス最適化

---

## 🚀 Claude Desktopでの開発手順

### 📢 新しいチャットセッションで開発を続ける際の魔法の言葉：

```
usb-to-gdrive-audio-syncプロジェクトの開発を続けます。
CLAUDE_INSTRUCTIONS.mdとREADME.mdを確認して、
現在のフェーズから開発を進めてください。
```

### Claudeが自動的に行うこと
1. **CLAUDE_INSTRUCTIONS.md**を最初に確認（開発ルール）
2. **README.md**から現在の状態を確認
3. GitHubリポジトリの最新状態を確認
4. 現在の開発フェーズから作業を継続
5. 必要なファイルの作成・更新をGitHub API経由で直接実行

### 開発の特徴
- ✅ 各フェーズの作業はClaude Desktopチャット内で完結
- ✅ コードの作成・修正はGitHub APIで直接リポジトリに反映
- ✅ ローカル環境は不要
- ✅ 全ての記録はGitHubで永続的に管理

---

## 📊 現在の開発状態

### ✅ 完了済み
- リポジトリ作成
- 要件定義書作成（README.md）
- Claude開発ガイドライン作成（CLAUDE_INSTRUCTIONS.md）
- 基本的なプロジェクト構造の設定
- requirements.txt作成
- .gitignore設定
- 設定ファイルサンプル作成

### 🔄 次のタスク (Phase 1)
1. **USB監視モジュール (usb_monitor.py) の実装**
   - macOSのディスク監視機能を使用
   - USBメモリの接続/切断検出
   - 特定のUSBメモリの識別

2. **ファイル処理モジュール (file_handler.py) の実装**
   - 音声ファイルのフィルタリング
   - ファイルサイズチェック
   - ファイルパスの管理

3. **ログ管理ユーティリティ (utils/logger.py) の実装**
   - ログファイルの作成と管理
   - エラーログの記録
   - デバッグ情報の出力

---

## 📝 開発履歴

| 日付 | フェーズ | 実装内容 | ステータス |
|------|----------|----------|------------|
| 2025-09-19 | 初期設定 | リポジトリ作成、要件定義 | ✅ 完了 |
| 2025-09-19 | 初期設定 | CLAUDE_INSTRUCTIONS.md作成 | ✅ 完了 |
| - | Phase 1 | USB検出機能 | 🔄 次のタスク |

---

## 🔧 Google Drive API設定（ユーザー側で必要な作業）

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新規プロジェクトを作成
3. Google Drive APIを有効化
4. OAuth 2.0クライアントIDを作成
5. credentials.jsonをダウンロード
6. ダウンロードしたファイルを`config/credentials/`フォルダに配置

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

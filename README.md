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
- [ ] Google Drive APIとの連携
- [ ] 新規ファイルの判定と差分同期
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
├── requirements.txt        # Python依存パッケージ
├── config/
│   ├── settings.json      # 設定ファイル
│   └── credentials/       # Google API認証情報
├── src/
│   ├── main.py           # メインプログラム ✅
│   ├── usb_monitor.py    # USB監視モジュール ✅
│   ├── file_handler.py   # ファイル処理モジュール ✅
│   ├── gdrive_sync.py    # Google Drive同期モジュール（Phase 2）
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

#### Phase 2: Google Drive連携 ← 次のフェーズ
- [ ] Google Drive API設定
- [ ] OAuth認証実装
- [ ] ファイルアップロード機能
- [ ] 並列アップロード処理

#### Phase 3: 同期機能実装
- [ ] 差分検出アルゴリズム
- [ ] 同期履歴データベース（SQLite）
- [ ] 重複チェック機能
- [ ] エラー処理とリトライ機能

#### Phase 4: 自動化とUI
- [ ] LaunchAgent設定（自動起動）
- [ ] システムトレイアプリケーション（オプション）
- [ ] 進捗通知機能の改善

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

### ✅ 完了済み (Phase 1)
- リポジトリ作成
- 要件定義書作成（README.md）
- Claude開発ガイドライン作成（CLAUDE_INSTRUCTIONS.md）
- 基本的なプロジェクト構造の設定
- requirements.txt作成
- .gitignore設定
- 設定ファイルサンプル作成
- **USB監視モジュール (usb_monitor.py)**
- **ファイル処理モジュール (file_handler.py)**
- **ログ管理ユーティリティ (utils/logger.py)**
- **メインプログラム (main.py)**

### 🔄 次のタスク (Phase 2: Google Drive連携)
1. **Google Drive API クライアント (gdrive_sync.py) の実装**
   - OAuth 2.0認証フロー
   - ファイルアップロード機能
   - フォルダ作成・管理

2. **認証管理機能**
   - credentials.jsonの読み込み
   - トークンの保存と更新
   - 認証エラーハンドリング

3. **アップロード機能の統合**
   - main.pyとの統合
   - 並列アップロード処理
   - 進捗表示の改善

---

## 🎉 Phase 1 完了内容

### 実装済みモジュール

1. **usb_monitor.py**
   - macOS固有のAPIを使用したUSB検出
   - フォールバック機能（ポーリング）
   - カスタマイズ可能なUSB識別子

2. **file_handler.py**
   - 音声ファイルの再帰的スキャン
   - 拡張子によるフィルタリング
   - ファイルサイズチェック
   - SHA-256ハッシュ計算

3. **utils/logger.py**
   - ローテーティングログファイル
   - 同期セッション記録
   - 統計情報の収集と表示

4. **main.py**
   - 全モジュールの統合
   - コマンドラインインターフェース
   - デーモンモード対応
   - macOS通知機能

---

## 📝 開発履歴

| 日付 | フェーズ | 実装内容 | ステータス |
|------|----------|----------|------------|
| 2025-09-19 | 初期設定 | リポジトリ作成、要件定義 | ✅ 完了 |
| 2025-09-19 | 初期設定 | CLAUDE_INSTRUCTIONS.md作成 | ✅ 完了 |
| 2025-09-19 | 初期設定 | URL管理ルール追加 | ✅ 完了 |
| 2025-09-19 | Phase 1 | USB監視モジュール実装 | ✅ 完了 |
| 2025-09-19 | Phase 1 | ファイル処理モジュール実装 | ✅ 完了 |
| 2025-09-19 | Phase 1 | ログ管理ユーティリティ実装 | ✅ 完了 |
| 2025-09-19 | Phase 1 | メインプログラム実装 | ✅ 完了 |
| - | Phase 2 | Google Drive API連携 | 🔄 次のタスク |

---

## 🔧 Google Drive API設定（ユーザー側で必要な作業）

### Phase 2開始前に必要な準備：

1. **[Google Cloud Console](https://console.cloud.google.com/)にアクセス**
2. **新規プロジェクトを作成**
3. **Google Drive APIを有効化**
   - APIとサービス → ライブラリ
   - 「Google Drive API」を検索して有効化
4. **OAuth 2.0クライアントIDを作成**
   - APIとサービス → 認証情報
   - 「認証情報を作成」→「OAuth クライアント ID」
   - アプリケーションの種類: デスクトップ
5. **credentials.jsonをダウンロード**
6. **ダウンロードしたファイルを`config/credentials/`フォルダに配置**

---

## 📌 関連URL

### 開発リソース
- リポジトリ: https://github.com/noah9970/usb-to-gdrive-audio-sync
- テンプレート: https://github.com/noah9970/claude-github-dev-template

### Google関連（Phase 2で使用予定）
- Google Cloud Console: https://console.cloud.google.com/
- Google Drive API Documentation: https://developers.google.com/drive/api/v3/about-sdk

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

# USB to Google Drive Audio Sync System
USBメモリからGoogle Driveへの自動音声データ同期システム

## 📋 要件定義書

### 1. システム概要
**目的**: MacBook AirにUSBメモリを接続すると、USB内の新しい音声データを自動的に指定されたGoogle Driveフォルダに保存するシステム

**対象環境**: 
- macOS (MacBook Air)
- Python 3.9+

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

#### Phase 1: 基本機能実装
- [ ] プロジェクト初期設定
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

### 7. 必要な準備

1. **Google Cloud Console設定**
   - Google Drive APIの有効化
   - OAuth 2.0クライアントIDの作成
   - credentials.jsonのダウンロード

2. **Python環境**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **システム権限**
   - ディスクアクセス権限の付与
   - 自動起動の設定（LaunchAgent）

### 8. 使用方法

```bash
# 初回セットアップ
./setup.sh

# 手動実行
python src/main.py

# デーモンとして実行
launchctl load ~/Library/LaunchAgents/com.user.usb-gdrive-sync.plist
```

### 9. トラブルシューティング

- **USBが検出されない**: システム環境設定でディスクアクセス権限を確認
- **Google Drive認証エラー**: credentials.jsonの再取得と再認証
- **同期が遅い**: 並列アップロード数の調整（settings.json）

### 10. 今後の拡張予定

- [ ] 複数のUSBメモリ対応
- [ ] 双方向同期機能
- [ ] Web UIダッシュボード
- [ ] スマートフォン通知連携
- [ ] 音声ファイルの自動変換機能

---

## 🚀 開発開始時の確認事項

新しいチャットセッションで開発を始める際は、必ず以下を確認してください：

1. **このREADMEの要件定義を読み込む**
2. **現在の開発フェーズを確認**
3. **最新のコード状態を確認**
4. **未解決のIssueを確認**

```bash
# 開発開始時のコマンド
git pull origin main
cat README.md  # 要件確認
git status     # 現在の状態確認
```

## 📝 コミットメッセージ規約

- `feat:` 新機能追加
- `fix:` バグ修正
- `docs:` ドキュメント更新
- `test:` テスト追加・修正
- `refactor:` リファクタリング
- `chore:` その他の変更

## 📞 連絡先・サポート

問題が発生した場合は、GitHubのIssueに報告してください。

---

最終更新日: 2025-09-15

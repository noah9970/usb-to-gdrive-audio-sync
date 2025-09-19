#!/bin/bash
# USB to Google Drive Audio Sync System セットアップスクリプト

set -e  # エラーが発生したら即座に終了

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ヘッダー表示
echo -e "${GREEN}"
echo "================================================"
echo "  USB to Google Drive Audio Sync System"
echo "  セットアップスクリプト v2.0"
echo "================================================"
echo -e "${NC}"

# 動作環境チェック
echo -e "${YELLOW}[1/7] 動作環境をチェック中...${NC}"

# macOSチェック
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}エラー: このシステムはmacOS専用です${NC}"
    exit 1
fi

# Python3チェック
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}エラー: Python3がインストールされていません${NC}"
    echo "Homebrewを使用してインストールしてください: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION を検出${NC}"

# プロジェクトディレクトリの設定
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo -e "${GREEN}✓ プロジェクトディレクトリ: $PROJECT_DIR${NC}"

# 仮想環境の作成
echo -e "${YELLOW}[2/7] Python仮想環境をセットアップ中...${NC}"
if [ ! -d "$PROJECT_DIR/venv" ]; then
    python3 -m venv "$PROJECT_DIR/venv"
    echo -e "${GREEN}✓ 仮想環境を作成しました${NC}"
else
    echo -e "${GREEN}✓ 仮想環境は既に存在します${NC}"
fi

# 仮想環境の有効化
source "$PROJECT_DIR/venv/bin/activate"

# pip のアップグレード
pip install --upgrade pip -q

# 依存パッケージのインストール
echo -e "${YELLOW}[3/7] 依存パッケージをインストール中...${NC}"
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    pip install -r "$PROJECT_DIR/requirements.txt" -q
    echo -e "${GREEN}✓ 依存パッケージをインストールしました${NC}"
else
    echo -e "${RED}警告: requirements.txt が見つかりません${NC}"
fi

# 設定ディレクトリの作成
echo -e "${YELLOW}[4/7] 設定ディレクトリを作成中...${NC}"
mkdir -p "$PROJECT_DIR/config/credentials"
mkdir -p "$PROJECT_DIR/logs"
echo -e "${GREEN}✓ 必要なディレクトリを作成しました${NC}"

# 設定ファイルのチェック
echo -e "${YELLOW}[5/7] 設定ファイルをチェック中...${NC}"

# settings.jsonの確認
if [ ! -f "$PROJECT_DIR/config/settings.json" ]; then
    echo -e "${YELLOW}settings.json を作成しています...${NC}"
    cat > "$PROJECT_DIR/config/settings.json" << 'EOF'
{
  "usb_identifier": "AUDIO_USB",
  "gdrive_folder_id": "YOUR_GOOGLE_DRIVE_FOLDER_ID",
  "audio_extensions": [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"],
  "max_file_size_mb": 500,
  "parallel_uploads": 5,
  "upload_chunk_size_mb": 10,
  "retry_attempts": 3,
  "retry_delay_seconds": 10,
  "log_level": "INFO",
  "exclude_folders": [
    ".Spotlight-V100",
    ".Trashes",
    "System Volume Information",
    "$RECYCLE.BIN"
  ],
  "preserve_folder_structure": true,
  "skip_duplicates": true,
  "use_database": true,
  "notification_enabled": true
}
EOF
    echo -e "${GREEN}✓ デフォルトの settings.json を作成しました${NC}"
    echo -e "${RED}重要: config/settings.json を編集して設定を完了してください${NC}"
else
    echo -e "${GREEN}✓ settings.json は既に存在します${NC}"
fi

# credentials.jsonのチェック
if [ ! -f "$PROJECT_DIR/config/credentials/credentials.json" ]; then
    echo -e "${RED}警告: credentials.json が見つかりません${NC}"
    echo -e "${YELLOW}Google Cloud Console から認証情報をダウンロードして、"
    echo -e "$PROJECT_DIR/config/credentials/credentials.json に配置してください${NC}"
    echo ""
    echo "手順:"
    echo "1. https://console.cloud.google.com/ にアクセス"
    echo "2. 新規プロジェクトを作成（または既存プロジェクトを選択）"
    echo "3. APIとサービス → ライブラリ → Google Drive API を有効化"
    echo "4. APIとサービス → 認証情報 → OAuth 2.0クライアントIDを作成"
    echo "5. アプリケーションの種類: デスクトップ を選択"
    echo "6. credentials.json をダウンロード"
    echo "7. $PROJECT_DIR/config/credentials/ に配置"
else
    echo -e "${GREEN}✓ credentials.json を検出しました${NC}"
fi

# LaunchAgent設定
echo -e "${YELLOW}[6/7] LaunchAgent設定を作成中...${NC}"

LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
LAUNCH_AGENT_PLIST="com.usb-gdrive-audio-sync.plist"
LAUNCH_AGENT_PATH="$LAUNCH_AGENT_DIR/$LAUNCH_AGENT_PLIST"

mkdir -p "$LAUNCH_AGENT_DIR"

# LaunchAgentファイルの作成
cat > "$LAUNCH_AGENT_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.usb-gdrive-audio-sync</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/venv/bin/python3</string>
        <string>$PROJECT_DIR/src/main.py</string>
        <string>--daemon</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/stderr.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONPATH</key>
        <string>$PROJECT_DIR</string>
    </dict>
</dict>
</plist>
EOF

echo -e "${GREEN}✓ LaunchAgent設定を作成しました${NC}"

# 実行権限の設定
chmod +x "$PROJECT_DIR/src/main.py" 2>/dev/null || true
chmod +x "$PROJECT_DIR/setup.sh"

# テスト実行
echo -e "${YELLOW}[7/7] システムテストを実行中...${NC}"

# Google Drive接続テスト（credentials.jsonが存在する場合のみ）
if [ -f "$PROJECT_DIR/config/credentials/credentials.json" ]; then
    echo -e "${YELLOW}Google Drive接続をテストしています...${NC}"
    if python3 "$PROJECT_DIR/src/main.py" --test-gdrive 2>/dev/null; then
        echo -e "${GREEN}✓ Google Drive接続テスト成功${NC}"
    else
        echo -e "${RED}✗ Google Drive接続テスト失敗${NC}"
        echo -e "${YELLOW}settings.json の gdrive_folder_id を確認してください${NC}"
    fi
else
    echo -e "${YELLOW}Google Drive接続テストをスキップ（credentials.json未設置）${NC}"
fi

# USB検出テスト
echo -e "${YELLOW}USB検出をテストしています...${NC}"
if python3 "$PROJECT_DIR/src/main.py" --check 2>/dev/null; then
    echo -e "${GREEN}✓ USB検出テスト完了${NC}"
else
    echo -e "${YELLOW}対象USBが接続されていません${NC}"
fi

# 統計情報表示
echo ""
echo -e "${YELLOW}[統計情報]${NC}"
echo "データベース位置: $PROJECT_DIR/config/sync_history.db"
echo "ログファイル位置: $PROJECT_DIR/logs/"
echo "LaunchAgent設定: $LAUNCH_AGENT_PATH"

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}セットアップが完了しました！${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${YELLOW}使用方法:${NC}"
echo "1. 手動実行:"
echo "   cd $PROJECT_DIR"
echo "   source venv/bin/activate"
echo "   python3 src/main.py"
echo ""
echo "2. 自動起動を有効化:"
echo "   launchctl load -w $LAUNCH_AGENT_PATH"
echo ""
echo "3. 自動起動を無効化:"
echo "   launchctl unload -w $LAUNCH_AGENT_PATH"
echo ""
echo "4. ログの確認:"
echo "   tail -f $PROJECT_DIR/logs/sync_*.log"
echo ""
echo "5. データベース統計の確認:"
echo "   python3 src/main.py --stats"
echo ""
echo -e "${YELLOW}重要な設定:${NC}"
echo "1. config/settings.json を編集:"
echo "   - usb_identifier: 対象USBのボリューム名"
echo "   - gdrive_folder_id: Google DriveのフォルダID"
echo ""
echo "2. Google API認証情報を配置:"
echo "   config/credentials/credentials.json"
echo ""
echo -e "${GREEN}Phase 3 機能:${NC}"
echo "✅ SQLiteデータベースによる同期履歴管理"
echo "✅ ハッシュ値による重複検出"
echo "✅ 差分同期（変更されたファイルのみアップロード）"
echo "✅ 統計情報の収集と表示"
echo ""
echo -e "${GREEN}セットアップ完了！${NC}"

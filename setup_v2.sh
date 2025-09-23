#!/bin/bash

# USB音声ファイル自動処理・同期システム v2.0
# セットアップスクリプト

echo "======================================"
echo "USB Audio Sync Pipeline v2.0 Setup"
echo "======================================"

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# エラーハンドリング
set -e
trap 'echo -e "${RED}エラーが発生しました。セットアップを中断します。${NC}"' ERR

# 1. Python環境チェック
echo -e "\n${GREEN}[1/7] Python環境をチェック中...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3が見つかりません。インストールしてください。${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python $PYTHON_VERSION を検出"

# 2. FFmpegのインストール確認
echo -e "\n${GREEN}[2/7] FFmpegをチェック中...${NC}"
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}FFmpegがインストールされていません。${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Homebrewを使用してインストールします..."
        if ! command -v brew &> /dev/null; then
            echo -e "${RED}Homebrewがインストールされていません。${NC}"
            echo "以下のコマンドでHomebrewをインストールしてください:"
            echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            exit 1
        fi
        brew install ffmpeg
    else
        echo -e "${RED}FFmpegを手動でインストールしてください。${NC}"
        echo "Ubuntu/Debian: sudo apt-get install ffmpeg"
        echo "CentOS/RHEL: sudo yum install ffmpeg"
        exit 1
    fi
else
    echo "FFmpegがインストール済み"
fi

# 3. 仮想環境の作成
echo -e "\n${GREEN}[3/7] Python仮想環境を作成中...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "仮想環境を作成しました"
else
    echo "仮想環境は既に存在します"
fi

# 仮想環境を有効化
source venv/bin/activate

# 4. 依存パッケージのインストール
echo -e "\n${GREEN}[4/7] 依存パッケージをインストール中...${NC}"
pip install --upgrade pip

# v2.0の新しい依存パッケージをインストール
if [ -f "requirements_v2.txt" ]; then
    pip install -r requirements_v2.txt
else
    # 基本パッケージをインストール
    pip install -r requirements.txt
    # 音声処理パッケージを追加インストール
    pip install librosa soundfile pydub ffmpeg-python numpy scipy
fi

# 5. ディレクトリ構造の作成
echo -e "\n${GREEN}[5/7] ディレクトリ構造を作成中...${NC}"
mkdir -p config/credentials
mkdir -p logs
mkdir -p ~/AudioBackup/{raw,processed,archive}
mkdir -p /tmp/audio_processing

# 6. 設定ファイルの作成
echo -e "\n${GREEN}[6/7] 設定ファイルを準備中...${NC}"
if [ ! -f "config/settings.json" ]; then
    if [ -f "config/settings_v2_template.json" ]; then
        cp config/settings_v2_template.json config/settings.json
    else
        # デフォルト設定を作成
        cat > config/settings.json << 'EOF'
{
    "usb_identifier": "AUDIO_USB",
    "gdrive_folder_id": "YOUR_GOOGLE_DRIVE_FOLDER_ID",
    "pipeline": {
        "auto_process": true,
        "parallel_processing": false,
        "max_parallel_jobs": 2
    },
    "local_storage": {
        "base_dir": "~/AudioBackup",
        "max_storage_gb": 100,
        "retention_days": 30,
        "auto_cleanup": true,
        "verify_copy": true,
        "temp_dir": "/tmp/audio_processing",
        "processed_dir": "~/AudioBackup/processed"
    },
    "audio_processing": {
        "silence_threshold": -40,
        "min_silence_duration": 2000,
        "chunk_size": 600,
        "target_sample_rate": 16000,
        "target_bitrate": "64k",
        "voice_activity_threshold": 5.0,
        "enable_noise_reduction": false
    },
    "google_drive": {
        "chunk_size_mb": 10,
        "max_retries": 3,
        "parallel_uploads": 5,
        "organize_by_date": true
    },
    "monitoring": {
        "enable_notifications": true,
        "webhook_url": "",
        "log_level": "INFO"
    },
    "database": {
        "path": "config/sync_history.db",
        "backup_enabled": true,
        "backup_interval_days": 7
    }
}
EOF
    fi
    echo -e "${YELLOW}設定ファイルを作成しました: config/settings.json${NC}"
    echo -e "${YELLOW}Google Drive Folder IDを設定してください。${NC}"
else
    echo "設定ファイルは既に存在します"
fi

# 7. LaunchAgent設定（macOSの場合）
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "\n${GREEN}[7/7] LaunchAgentを設定中...${NC}"
    
    PLIST_FILE="$HOME/Library/LaunchAgents/com.usb-gdrive-audio-sync-v2.plist"
    CURRENT_DIR=$(pwd)
    
    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.usb-gdrive-audio-sync-v2</string>
    <key>ProgramArguments</key>
    <array>
        <string>$CURRENT_DIR/venv/bin/python3</string>
        <string>$CURRENT_DIR/src/main_v2.py</string>
        <string>--monitor</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$CURRENT_DIR</string>
    <key>StandardOutPath</key>
    <string>$CURRENT_DIR/logs/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$CURRENT_DIR/logs/launchd_stderr.log</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF
    
    echo "LaunchAgent設定を作成しました"
    echo -e "${YELLOW}自動起動を有効にするには以下を実行してください:${NC}"
    echo "launchctl load -w $PLIST_FILE"
else
    echo -e "\n${GREEN}[7/7] Linux環境のため、LaunchAgent設定をスキップ${NC}"
fi

# 完了メッセージ
echo -e "\n${GREEN}======================================"
echo "セットアップが完了しました！"
echo "======================================${NC}"
echo ""
echo "次のステップ:"
echo "1. Google Cloud Consoleでプロジェクトを作成"
echo "2. Google Drive APIを有効化"
echo "3. OAuth 2.0認証情報をダウンロード"
echo "4. credentials.jsonをconfig/credentials/に配置"
echo "5. config/settings.jsonを編集"
echo "6. 実行: python3 src/main_v2.py"
echo ""
echo "コマンド例:"
echo "  手動実行: python3 src/main_v2.py --usb-path /Volumes/AUDIO_USB"
echo "  モニターモード: python3 src/main_v2.py --monitor"
echo "  ステータス確認: python3 src/main_v2.py --status"
echo "  音声処理のみ: python3 src/main_v2.py --process-only"
echo "  アップロードのみ: python3 src/main_v2.py --upload-only"

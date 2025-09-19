#!/usr/bin/env python3
"""
Main Program
USBメモリからGoogle Driveへの音声ファイル自動同期システムのメインプログラム
"""

import os
import sys
import time
import signal
import json
from pathlib import Path
from typing import Optional
import argparse

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.usb_monitor import USBMonitor
from src.file_handler import FileHandler
from src.utils.logger import LogManager, SyncStats


class AudioSyncSystem:
    """音声ファイル同期システムのメインクラス"""
    
    def __init__(self, config_path: str = "config/settings.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        # ログマネージャーの初期化
        self.log_manager = LogManager(config_path)
        self.logger = LogManager.get_logger(__name__)
        
        # 設定の読み込み
        self.config = self._load_config(config_path)
        
        # 各モジュールの初期化
        self.usb_monitor = USBMonitor(config_path)
        self.file_handler = FileHandler(config_path)
        
        # Google Drive同期モジュール（Phase 2で実装予定）
        self.gdrive_sync = None
        
        # 統計情報
        self.stats = None
        
        # シャットダウンフラグ
        self.shutdown = False
        
        self.logger.info("Audio Sync System initialized")
    
    def _load_config(self, config_path: str) -> dict:
        """設定ファイルを読み込む"""
        config_file = Path(config_path)
        if not config_file.exists():
            self.logger.error(f"Config file not found: {config_path}")
            self.logger.info("Creating default config file...")
            self._create_default_config(config_path)
            
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _create_default_config(self, config_path: str):
        """デフォルトの設定ファイルを作成"""
        default_config = {
            "usb_identifier": "AUDIO_USB",
            "gdrive_folder_id": "YOUR_GOOGLE_DRIVE_FOLDER_ID",
            "audio_extensions": [
                ".mp3", ".wav", ".m4a", 
                ".aac", ".flac", ".ogg"
            ],
            "max_file_size_mb": 500,
            "parallel_uploads": 5,
            "retry_attempts": 3,
            "retry_delay_seconds": 10,
            "log_level": "INFO",
            "exclude_folders": [
                ".Spotlight-V100",
                ".Trashes",
                "System Volume Information",
                "$RECYCLE.BIN"
            ],
            "preserve_folder_structure": True,
            "skip_duplicates": True,
            "notification_enabled": True
        }
        
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
    
    def sync_files(self, usb_path: str):
        """
        USBメモリ内の音声ファイルを同期
        
        Args:
            usb_path: USBメモリのマウントパス
        """
        try:
            self.logger.info(f"Starting sync process for: {usb_path}")
            
            # 統計情報の初期化
            self.stats = SyncStats()
            self.stats.start()
            
            # 音声ファイルをスキャン
            audio_files = self.file_handler.scan_audio_files(usb_path)
            
            if not audio_files:
                self.logger.info("No audio files found to sync")
                return
            
            # 統計情報を設定
            self.stats.total_files = len(audio_files)
            total_size = sum(file['size'] for file in audio_files)
            self.stats.total_size = total_size
            
            # ログセッションを開始
            session_file = self.log_manager.log_sync_start(usb_path, len(audio_files))
            
            self.logger.info(f"Found {len(audio_files)} audio files "
                           f"(Total size: {LogManager.format_file_size(total_size)})")
            
            # 各ファイルを処理
            for i, audio_file in enumerate(audio_files, 1):
                if self.shutdown:
                    self.logger.info("Sync interrupted by user")
                    break
                
                file_path = audio_file['path']
                file_name = audio_file['name']
                file_size = audio_file['size']
                
                self.logger.info(f"Processing ({i}/{len(audio_files)}): {file_name}")
                
                # ファイルの重複チェック
                if self.config.get('skip_duplicates', True):
                    file_hash = self.file_handler.calculate_hash(file_path)
                    # TODO: Google Drive上の重複チェック（Phase 2で実装）
                    # if self.gdrive_sync and self.gdrive_sync.file_exists(file_hash):
                    #     self.logger.info(f"Skipped (already exists): {file_name}")
                    #     self.stats.add_skip(file_name, "Already exists")
                    #     self.log_manager.log_sync_progress(
                    #         session_file, file_name, "SKIPPED", "Already exists"
                    #     )
                    #     continue
                
                # ファイルをアップロード（Phase 2で実装）
                # TODO: Google Driveへのアップロード実装
                # try:
                #     if self.gdrive_sync:
                #         self.gdrive_sync.upload_file(file_path, audio_file['relative_path'])
                #     self.stats.add_success(file_name, file_size)
                #     self.log_manager.log_sync_progress(session_file, file_name, "SUCCESS")
                # except Exception as e:
                #     self.logger.error(f"Failed to upload {file_name}: {e}")
                #     self.stats.add_failure(file_name, str(e))
                #     self.log_manager.log_sync_progress(
                #         session_file, file_name, "FAILED", str(e)
                #     )
                
                # 仮の処理（実際のアップロードは Phase 2 で実装）
                self.logger.info(f"Would upload: {file_name} ({LogManager.format_file_size(file_size)})")
                self.stats.add_success(file_name, file_size)
                self.log_manager.log_sync_progress(session_file, file_name, "SUCCESS")
                
                # 進捗表示
                progress = self.stats.progress_percentage
                self.logger.info(f"Progress: {progress:.1f}%")
            
            # 統計情報を終了
            self.stats.end()
            
            # ログセッションを完了
            self.log_manager.log_sync_complete(
                session_file,
                self.stats.success_count,
                self.stats.failed_count,
                self.stats.skipped_count,
                self.stats.duration
            )
            
            # サマリーを表示
            self._show_summary()
            
            # 通知を送信（設定が有効な場合）
            if self.config.get('notification_enabled', True):
                self._send_notification()
            
        except Exception as e:
            self.logger.error(f"Sync process failed: {e}", exc_info=True)
            self.log_manager.log_error(e, "sync_files")
    
    def _show_summary(self):
        """同期サマリーを表示"""
        if not self.stats:
            return
        
        summary = self.stats.get_summary()
        
        self.logger.info("=" * 50)
        self.logger.info("Sync Summary:")
        self.logger.info(f"  Duration: {summary['duration']:.2f} seconds")
        self.logger.info(f"  Total files: {summary['total_files']}")
        self.logger.info(f"  Success: {summary['success_count']}")
        self.logger.info(f"  Failed: {summary['failed_count']}")
        self.logger.info(f"  Skipped: {summary['skipped_count']}")
        self.logger.info(f"  Total size: {LogManager.format_file_size(summary['total_size'])}")
        self.logger.info(f"  Uploaded: {LogManager.format_file_size(summary['uploaded_size'])}")
        
        if summary['failed_files']:
            self.logger.warning("Failed files:")
            for failed in summary['failed_files']:
                self.logger.warning(f"  - {failed['file']}: {failed['error']}")
        
        self.logger.info("=" * 50)
    
    def _send_notification(self):
        """macOS通知を送信"""
        try:
            if not self.stats:
                return
            
            title = "USB Audio Sync Complete"
            message = (f"Synced {self.stats.success_count} files successfully. "
                      f"Failed: {self.stats.failed_count}, "
                      f"Skipped: {self.stats.skipped_count}")
            
            # macOS通知コマンド
            os.system(f"""
                osascript -e 'display notification "{message}" with title "{title}"'
            """)
            
        except Exception as e:
            self.logger.warning(f"Could not send notification: {e}")
    
    def on_usb_mounted(self, usb_path: str):
        """
        USBがマウントされた時の処理
        
        Args:
            usb_path: USBメモリのマウントパス
        """
        self.logger.info(f"Target USB detected: {usb_path}")
        
        # 少し待機（マウント処理の完了を待つ）
        time.sleep(2)
        
        # 同期処理を開始
        self.sync_files(usb_path)
    
    def on_usb_unmounted(self, usb_path: str):
        """
        USBがアンマウントされた時の処理
        
        Args:
            usb_path: USBメモリのマウントパス
        """
        self.logger.info(f"USB unmounted: {usb_path}")
    
    def start(self, daemon_mode: bool = False):
        """
        システムを開始
        
        Args:
            daemon_mode: デーモンモードで実行するかどうか
        """
        self.logger.info("Starting Audio Sync System...")
        
        # コールバックを設定
        self.usb_monitor.on_mount(self.on_usb_mounted)
        self.usb_monitor.on_unmount(self.on_usb_unmounted)
        
        # 現在接続されているUSBをチェック
        current_usb = self.usb_monitor.check_current_usb()
        if current_usb:
            self.logger.info(f"Found connected USB: {current_usb}")
            if not daemon_mode:
                # 対話モードの場合、確認を求める
                response = input("Do you want to sync now? (y/n): ")
                if response.lower() == 'y':
                    self.sync_files(current_usb)
        
        # USB監視を開始
        self.usb_monitor.start_monitoring()
        self.logger.info("USB monitoring started. Waiting for USB connection...")
        
        if daemon_mode:
            self.logger.info("Running in daemon mode...")
        else:
            self.logger.info("Press Ctrl+C to stop")
        
        try:
            while not self.shutdown:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """システムを停止"""
        self.logger.info("Stopping Audio Sync System...")
        self.shutdown = True
        self.usb_monitor.stop_monitoring()
        
        # 古いログをクリーンアップ
        self.log_manager.clean_old_logs(30)
        
        self.logger.info("System stopped")
    
    def signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        self.logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="USB to Google Drive Audio Sync System"
    )
    parser.add_argument(
        '-d', '--daemon',
        action='store_true',
        help='Run in daemon mode'
    )
    parser.add_argument(
        '-c', '--config',
        default='config/settings.json',
        help='Path to config file'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check current USB and exit'
    )
    parser.add_argument(
        '--sync',
        metavar='PATH',
        help='Manually sync files from specified path'
    )
    
    args = parser.parse_args()
    
    # システムを初期化
    system = AudioSyncSystem(args.config)
    
    # シグナルハンドラーを設定
    signal.signal(signal.SIGINT, system.signal_handler)
    signal.signal(signal.SIGTERM, system.signal_handler)
    
    try:
        if args.check:
            # 現在のUSBをチェックして終了
            monitor = USBMonitor(args.config)
            current_usb = monitor.check_current_usb()
            if current_usb:
                print(f"Target USB found: {current_usb}")
            else:
                print("No target USB found")
                
        elif args.sync:
            # 指定されたパスから手動同期
            system.sync_files(args.sync)
            
        else:
            # 通常モードまたはデーモンモードで実行
            system.start(daemon_mode=args.daemon)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

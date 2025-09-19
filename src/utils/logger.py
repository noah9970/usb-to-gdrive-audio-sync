#!/usr/bin/env python3
"""
Logger Module
ログ管理とエラー処理を担当するモジュール
"""

import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional
import json


class LogManager:
    """ログ管理クラス"""
    
    def __init__(self, config_path: str = "config/settings.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config = self._load_config(config_path)
        self.log_dir = Path("logs")
        self.log_level = self.config.get("log_level", "INFO")
        self.max_log_size = self.config.get("max_log_size_mb", 10) * 1024 * 1024
        self.backup_count = self.config.get("log_backup_count", 5)
        
        # ログディレクトリを作成
        self.log_dir.mkdir(exist_ok=True)
        
        # ロガーのセットアップ
        self.setup_loggers()
    
    def _load_config(self, config_path: str) -> dict:
        """設定ファイルを読み込む"""
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {}
    
    def setup_loggers(self):
        """ロガーをセットアップ"""
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level))
        
        # 既存のハンドラをクリア
        root_logger.handlers.clear()
        
        # フォーマッターの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # コンソールハンドラ
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # ファイルハンドラ（通常ログ）
        app_log_file = self.log_dir / "app.log"
        app_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        app_handler.setLevel(logging.DEBUG)
        app_handler.setFormatter(formatter)
        root_logger.addHandler(app_handler)
        
        # エラーログ専用ハンドラ
        error_log_file = self.log_dir / "error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
        
        # 同期ログ専用ハンドラ
        sync_logger = logging.getLogger('sync')
        sync_log_file = self.log_dir / "sync.log"
        sync_handler = logging.handlers.RotatingFileHandler(
            sync_log_file,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        sync_handler.setLevel(logging.INFO)
        sync_handler.setFormatter(formatter)
        sync_logger.addHandler(sync_handler)
        sync_logger.propagate = False  # 親ロガーに伝播しない
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        指定された名前のロガーを取得
        
        Args:
            name: ロガー名
            
        Returns:
            Logger インスタンス
        """
        return logging.getLogger(name)
    
    def log_sync_start(self, usb_path: str, file_count: int):
        """
        同期開始をログに記録
        
        Args:
            usb_path: USBのパス
            file_count: 同期対象ファイル数
        """
        sync_logger = logging.getLogger('sync')
        sync_logger.info(f"Sync started - USB: {usb_path}, Files: {file_count}")
        
        # 同期セッションファイルを作成
        session_file = self.log_dir / f"sync_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(session_file, 'w', encoding='utf-8') as f:
            f.write(f"Sync Session Started\n")
            f.write(f"Time: {datetime.now().isoformat()}\n")
            f.write(f"USB Path: {usb_path}\n")
            f.write(f"Total Files: {file_count}\n")
            f.write("-" * 50 + "\n")
        
        return session_file
    
    def log_sync_progress(self, session_file: Path, file_name: str, 
                          status: str, message: Optional[str] = None):
        """
        同期進捗をログに記録
        
        Args:
            session_file: セッションログファイル
            file_name: ファイル名
            status: ステータス（SUCCESS/FAILED/SKIPPED）
            message: 追加メッセージ
        """
        sync_logger = logging.getLogger('sync')
        log_message = f"{status}: {file_name}"
        if message:
            log_message += f" - {message}"
        
        sync_logger.info(log_message)
        
        # セッションファイルにも記録
        if session_file and session_file.exists():
            with open(session_file, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().strftime('%H:%M:%S')} - {log_message}\n")
    
    def log_sync_complete(self, session_file: Path, success_count: int, 
                         failed_count: int, skipped_count: int, duration: float):
        """
        同期完了をログに記録
        
        Args:
            session_file: セッションログファイル
            success_count: 成功数
            failed_count: 失敗数
            skipped_count: スキップ数
            duration: 処理時間（秒）
        """
        sync_logger = logging.getLogger('sync')
        summary = (f"Sync completed - Success: {success_count}, "
                  f"Failed: {failed_count}, Skipped: {skipped_count}, "
                  f"Duration: {duration:.2f}s")
        sync_logger.info(summary)
        
        # セッションファイルに記録
        if session_file and session_file.exists():
            with open(session_file, 'a', encoding='utf-8') as f:
                f.write("-" * 50 + "\n")
                f.write(f"Sync Session Completed\n")
                f.write(f"Time: {datetime.now().isoformat()}\n")
                f.write(f"Success: {success_count}\n")
                f.write(f"Failed: {failed_count}\n")
                f.write(f"Skipped: {skipped_count}\n")
                f.write(f"Duration: {duration:.2f} seconds\n")
    
    def log_error(self, error: Exception, context: Optional[str] = None):
        """
        エラーをログに記録
        
        Args:
            error: 例外オブジェクト
            context: エラーコンテキスト
        """
        logger = logging.getLogger(__name__)
        error_msg = f"Error in {context}: {str(error)}" if context else str(error)
        logger.error(error_msg, exc_info=True)
    
    def clean_old_logs(self, days_to_keep: int = 30):
        """
        古いログファイルを削除
        
        Args:
            days_to_keep: 保持する日数
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_file in self.log_dir.glob("sync_session_*.log"):
            try:
                # ファイル名から日付を取得
                file_date_str = log_file.stem.replace("sync_session_", "")
                file_date = datetime.strptime(file_date_str, "%Y%m%d_%H%M%S")
                
                if file_date < cutoff_date:
                    log_file.unlink()
                    logging.info(f"Deleted old log file: {log_file.name}")
            except Exception as e:
                logging.warning(f"Could not process log file {log_file.name}: {e}")
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        ファイルサイズを人間が読みやすい形式に変換
        
        Args:
            size_bytes: バイト単位のサイズ
            
        Returns:
            フォーマットされたサイズ文字列
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


class SyncStats:
    """同期統計を管理するクラス"""
    
    def __init__(self):
        """初期化"""
        self.start_time = None
        self.end_time = None
        self.total_files = 0
        self.processed_files = 0
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.total_size = 0
        self.uploaded_size = 0
        self.failed_files = []
    
    def start(self):
        """統計収集を開始"""
        self.start_time = datetime.now()
    
    def end(self):
        """統計収集を終了"""
        self.end_time = datetime.now()
    
    @property
    def duration(self) -> float:
        """処理時間（秒）を取得"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0
    
    @property
    def progress_percentage(self) -> float:
        """進捗率を取得"""
        if self.total_files > 0:
            return (self.processed_files / self.total_files) * 100
        return 0
    
    def add_success(self, file_name: str, file_size: int):
        """成功を記録"""
        self.processed_files += 1
        self.success_count += 1
        self.uploaded_size += file_size
    
    def add_failure(self, file_name: str, error: str):
        """失敗を記録"""
        self.processed_files += 1
        self.failed_count += 1
        self.failed_files.append({'file': file_name, 'error': error})
    
    def add_skip(self, file_name: str, reason: str):
        """スキップを記録"""
        self.processed_files += 1
        self.skipped_count += 1
    
    def get_summary(self) -> dict:
        """統計サマリーを取得"""
        return {
            'duration': self.duration,
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'total_size': self.total_size,
            'uploaded_size': self.uploaded_size,
            'progress_percentage': self.progress_percentage,
            'failed_files': self.failed_files
        }


def main():
    """テスト用のメイン関数"""
    # ログマネージャーの初期化
    log_manager = LogManager()
    
    # 各種ロガーのテスト
    logger = LogManager.get_logger(__name__)
    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # 同期ログのテスト
    session_file = log_manager.log_sync_start("/Volumes/AUDIO_USB", 10)
    log_manager.log_sync_progress(session_file, "test.mp3", "SUCCESS")
    log_manager.log_sync_progress(session_file, "test2.wav", "FAILED", "Upload error")
    log_manager.log_sync_complete(session_file, 8, 1, 1, 45.5)
    
    # 統計のテスト
    stats = SyncStats()
    stats.start()
    stats.total_files = 10
    stats.add_success("file1.mp3", 5000000)
    stats.add_failure("file2.wav", "Network error")
    stats.add_skip("file3.mp3", "Already exists")
    stats.end()
    
    print("Statistics Summary:")
    for key, value in stats.get_summary().items():
        print(f"  {key}: {value}")
    
    # 古いログのクリーンアップテスト
    log_manager.clean_old_logs(30)
    
    print("Log manager test completed successfully!")


if __name__ == "__main__":
    main()

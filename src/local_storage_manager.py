#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ローカルストレージ管理モジュール
USBからローカルストレージへのコピーと管理を行う
"""

import os
import json
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import threading
import queue

from utils.logger import Logger
from utils.database import SyncDatabase

class LocalStorageManager:
    """ローカルストレージ管理クラス"""
    
    def __init__(self, config_path: str = "config/settings.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.logger = Logger("LocalStorageManager")
        self.config = self._load_config(config_path)
        self.db = SyncDatabase()
        
        # ローカルストレージ設定
        self.local_base_dir = Path(self.config.get('local_storage', {}).get('base_dir', '~/AudioBackup')).expanduser()
        self.raw_audio_dir = self.local_base_dir / 'raw'
        self.processed_audio_dir = self.local_base_dir / 'processed'
        self.archive_dir = self.local_base_dir / 'archive'
        
        # ディレクトリ作成
        self._create_directories()
        
        # ストレージ管理設定
        self.max_storage_gb = self.config.get('local_storage', {}).get('max_storage_gb', 100)
        self.retention_days = self.config.get('local_storage', {}).get('retention_days', 30)
        self.auto_cleanup = self.config.get('local_storage', {}).get('auto_cleanup', True)
        
        # コピー設定
        self.buffer_size = 1024 * 1024  # 1MB
        self.verify_copy = self.config.get('local_storage', {}).get('verify_copy', True)
        
        self.logger.info(f"ローカルストレージマネージャー初期化完了: {self.local_base_dir}")
    
    def _load_config(self, config_path: str) -> Dict:
        """設定ファイルを読み込む"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"設定ファイル読み込みエラー: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """デフォルト設定を返す"""
        return {
            'local_storage': {
                'base_dir': '~/AudioBackup',
                'max_storage_gb': 100,
                'retention_days': 30,
                'auto_cleanup': True,
                'verify_copy': True
            }
        }
    
    def _create_directories(self):
        """必要なディレクトリを作成"""
        for dir_path in [self.local_base_dir, self.raw_audio_dir, 
                        self.processed_audio_dir, self.archive_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"ディレクトリ確認: {dir_path}")
    
    def copy_from_usb(self, usb_path: str, file_patterns: List[str] = None) -> List[str]:
        """
        USBから音声ファイルをローカルストレージにコピー
        
        Args:
            usb_path: USBのマウントパス
            file_patterns: コピーするファイルパターン（省略時は全音声ファイル）
        
        Returns:
            コピーされたファイルのローカルパスリスト
        """
        if file_patterns is None:
            file_patterns = ['*.mp3', '*.wav', '*.m4a', '*.aac', '*.flac', '*.ogg']
        
        usb_path = Path(usb_path)
        if not usb_path.exists():
            self.logger.error(f"USBパスが存在しません: {usb_path}")
            return []
        
        copied_files = []
        
        # 今日の日付でサブディレクトリを作成
        today = datetime.now().strftime("%Y%m%d")
        daily_dir = self.raw_audio_dir / today
        daily_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # USBから音声ファイルを検索
            audio_files = []
            for pattern in file_patterns:
                audio_files.extend(usb_path.rglob(pattern))
            
            total_files = len(audio_files)
            self.logger.info(f"USBから {total_files} 個の音声ファイルを検出")
            
            for i, src_file in enumerate(audio_files, 1):
                try:
                    # 相対パスを保持してコピー
                    relative_path = src_file.relative_to(usb_path)
                    dest_file = daily_dir / relative_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # ファイルが既に存在し、同じサイズの場合はスキップ
                    if dest_file.exists():
                        if dest_file.stat().st_size == src_file.stat().st_size:
                            self.logger.debug(f"スキップ（既存）: {relative_path}")
                            copied_files.append(str(dest_file))
                            continue
                    
                    # プログレス表示
                    self.logger.info(f"コピー中 [{i}/{total_files}]: {src_file.name}")
                    
                    # 高速コピー（バッファサイズ指定）
                    self._copy_with_progress(src_file, dest_file)
                    
                    # コピー検証（オプション）
                    if self.verify_copy:
                        if not self._verify_file_copy(src_file, dest_file):
                            self.logger.error(f"検証失敗: {relative_path}")
                            dest_file.unlink()  # 失敗したファイルを削除
                            continue
                    
                    copied_files.append(str(dest_file))
                    
                    # データベースに記録
                    self._record_file_copy(src_file, dest_file)
                    
                except Exception as e:
                    self.logger.error(f"ファイルコピーエラー: {src_file.name} - {e}")
                    continue
            
            self.logger.info(f"コピー完了: {len(copied_files)}/{total_files} ファイル")
            
            # 自動クリーンアップ
            if self.auto_cleanup:
                self.cleanup_old_files()
            
            return copied_files
            
        except Exception as e:
            self.logger.error(f"USBコピーエラー: {e}", exc_info=True)
            return copied_files
    
    def _copy_with_progress(self, src: Path, dest: Path):
        """
        プログレス表示付きファイルコピー
        
        Args:
            src: コピー元ファイル
            dest: コピー先ファイル
        """
        file_size = src.stat().st_size
        copied = 0
        
        with open(src, 'rb') as fsrc:
            with open(dest, 'wb') as fdest:
                while True:
                    buffer = fsrc.read(self.buffer_size)
                    if not buffer:
                        break
                    
                    fdest.write(buffer)
                    copied += len(buffer)
                    
                    # プログレス計算（10%刻みでログ出力）
                    progress = int((copied / file_size) * 10) * 10
                    if progress > 0 and copied % (file_size // 10) < self.buffer_size:
                        self.logger.debug(f"  {progress}% コピー済み")
    
    def _verify_file_copy(self, src: Path, dest: Path) -> bool:
        """
        ファイルコピーの検証（MD5ハッシュ比較）
        
        Args:
            src: コピー元ファイル
            dest: コピー先ファイル
        
        Returns:
            検証成功かどうか
        """
        try:
            src_hash = self._calculate_file_hash(src)
            dest_hash = self._calculate_file_hash(dest)
            return src_hash == dest_hash
        except Exception as e:
            self.logger.error(f"ファイル検証エラー: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """ファイルのMD5ハッシュを計算"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _record_file_copy(self, src: Path, dest: Path):
        """
        ファイルコピーをデータベースに記録
        
        Args:
            src: コピー元ファイル
            dest: コピー先ファイル
        """
        try:
            file_info = {
                'source_path': str(src),
                'local_path': str(dest),
                'file_size': dest.stat().st_size,
                'copy_date': datetime.now().isoformat(),
                'file_hash': self._calculate_file_hash(dest),
                'status': 'raw'  # raw, processed, uploaded, archived
            }
            
            # データベースに保存（実装はSyncDatabaseに依存）
            # self.db.record_local_file(file_info)
            
        except Exception as e:
            self.logger.error(f"データベース記録エラー: {e}")
    
    def get_unprocessed_files(self) -> List[str]:
        """
        処理されていない音声ファイルのリストを取得
        
        Returns:
            未処理ファイルのパスリスト
        """
        unprocessed = []
        
        try:
            # rawディレクトリ内の全ファイルを取得
            for audio_file in self.raw_audio_dir.rglob("*"):
                if audio_file.is_file() and audio_file.suffix.lower() in ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']:
                    # 処理済みディレクトリに同名ファイルが存在しない場合
                    processed_path = self.processed_audio_dir / audio_file.relative_to(self.raw_audio_dir)
                    if not processed_path.exists():
                        unprocessed.append(str(audio_file))
            
            self.logger.info(f"未処理ファイル: {len(unprocessed)} 個")
            return unprocessed
            
        except Exception as e:
            self.logger.error(f"未処理ファイル取得エラー: {e}")
            return []
    
    def move_to_processed(self, raw_file: str, processed_file: str) -> bool:
        """
        処理済みファイルを処理済みディレクトリに移動
        
        Args:
            raw_file: 元のファイルパス
            processed_file: 処理済みファイルパス
        
        Returns:
            成功かどうか
        """
        try:
            raw_path = Path(raw_file)
            processed_path = Path(processed_file)
            
            # 処理済みディレクトリ内の適切な場所に移動
            relative_path = raw_path.relative_to(self.raw_audio_dir)
            final_path = self.processed_audio_dir / relative_path.with_suffix('.mp3')
            final_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイル移動
            shutil.move(str(processed_path), str(final_path))
            
            # 元のファイルをアーカイブ
            archive_path = self.archive_dir / relative_path
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(raw_path), str(archive_path))
            
            self.logger.info(f"処理済みファイル移動: {final_path.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル移動エラー: {e}")
            return False
    
    def get_storage_info(self) -> Dict:
        """
        ストレージ使用状況を取得
        
        Returns:
            ストレージ情報
        """
        try:
            # 各ディレクトリのサイズを計算
            raw_size = sum(f.stat().st_size for f in self.raw_audio_dir.rglob("*") if f.is_file())
            processed_size = sum(f.stat().st_size for f in self.processed_audio_dir.rglob("*") if f.is_file())
            archive_size = sum(f.stat().st_size for f in self.archive_dir.rglob("*") if f.is_file())
            
            total_size = raw_size + processed_size + archive_size
            
            # ディスク使用状況
            stat = shutil.disk_usage(self.local_base_dir)
            
            return {
                'raw_size_gb': raw_size / (1024**3),
                'processed_size_gb': processed_size / (1024**3),
                'archive_size_gb': archive_size / (1024**3),
                'total_size_gb': total_size / (1024**3),
                'max_size_gb': self.max_storage_gb,
                'usage_percent': (total_size / (1024**3) / self.max_storage_gb * 100) if self.max_storage_gb > 0 else 0,
                'disk_free_gb': stat.free / (1024**3),
                'disk_total_gb': stat.total / (1024**3)
            }
            
        except Exception as e:
            self.logger.error(f"ストレージ情報取得エラー: {e}")
            return {}
    
    def cleanup_old_files(self):
        """古いファイルをクリーンアップ"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            cleaned_count = 0
            cleaned_size = 0
            
            # アーカイブディレクトリのみクリーンアップ
            for file_path in self.archive_dir.rglob("*"):
                if file_path.is_file():
                    # ファイルの変更日時をチェック
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_date:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        cleaned_count += 1
                        cleaned_size += file_size
                        self.logger.debug(f"古いファイル削除: {file_path.name}")
            
            if cleaned_count > 0:
                self.logger.info(f"クリーンアップ完了: {cleaned_count} ファイル, {cleaned_size / (1024**2):.2f} MB")
            
        except Exception as e:
            self.logger.error(f"クリーンアップエラー: {e}")
    
    def get_pending_uploads(self) -> List[str]:
        """
        アップロード待ちの処理済みファイルを取得
        
        Returns:
            アップロード待ちファイルのパスリスト
        """
        pending = []
        
        try:
            for processed_file in self.processed_audio_dir.rglob("*.mp3"):
                if processed_file.is_file():
                    # TODO: データベースでアップロード状態を確認
                    pending.append(str(processed_file))
            
            return pending
            
        except Exception as e:
            self.logger.error(f"アップロード待ちファイル取得エラー: {e}")
            return []


if __name__ == "__main__":
    # テスト実行
    manager = LocalStorageManager()
    
    # ストレージ情報表示
    info = manager.get_storage_info()
    print(f"ストレージ情報: {json.dumps(info, indent=2)}")
    
    # テスト用USBパス（実際のパスに置き換えてください）
    usb_path = "/Volumes/AUDIO_USB"
    
    if os.path.exists(usb_path):
        # USBからコピー
        copied = manager.copy_from_usb(usb_path)
        print(f"コピーされたファイル: {len(copied)}")
        
        # 未処理ファイル取得
        unprocessed = manager.get_unprocessed_files()
        print(f"未処理ファイル: {len(unprocessed)}")

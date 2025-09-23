#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USB音声ファイル自動処理・同期システム v2.0
新パイプライン：USB → ローカル → 音声処理 → Google Drive
"""

import os
import sys
import json
import time
import argparse
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# プロジェクトモジュール
from usb_monitor import USBMonitor
from local_storage_manager import LocalStorageManager
from audio_processor import AudioProcessor
from gdrive_sync import GoogleDriveSync
from utils.logger import Logger
from utils.database import SyncDatabase

class AudioSyncPipeline:
    """音声同期パイプライン統合クラス"""
    
    def __init__(self, config_path: str = "config/settings.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.logger = Logger("AudioSyncPipeline")
        self.config = self._load_config(config_path)
        
        # 各モジュールの初期化
        self.usb_monitor = USBMonitor()
        self.storage_manager = LocalStorageManager(config_path)
        self.audio_processor = AudioProcessor(config_path)
        self.gdrive_sync = GoogleDriveSync(config_path)
        self.db = SyncDatabase()
        
        # パイプライン設定
        self.auto_process = self.config.get('pipeline', {}).get('auto_process', True)
        self.parallel_processing = self.config.get('pipeline', {}).get('parallel_processing', False)
        self.max_parallel_jobs = self.config.get('pipeline', {}).get('max_parallel_jobs', 2)
        
        # 処理キュー
        self.processing_queue = []
        self.upload_queue = []
        
        # ステータス
        self.is_running = False
        self.current_session = None
        
        self.logger.info("音声同期パイプライン v2.0 初期化完了")
    
    def _load_config(self, config_path: str) -> Dict:
        """設定ファイルを読み込む"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                # 新しいパイプライン設定のデフォルト値を追加
                if 'pipeline' not in config:
                    config['pipeline'] = {
                        'auto_process': True,
                        'parallel_processing': False,
                        'max_parallel_jobs': 2
                    }
                
                if 'local_storage' not in config:
                    config['local_storage'] = {
                        'base_dir': '~/AudioBackup',
                        'max_storage_gb': 100,
                        'retention_days': 30,
                        'auto_cleanup': True,
                        'verify_copy': True,
                        'temp_dir': '/tmp/audio_processing',
                        'processed_dir': 'processed_audio'
                    }
                
                if 'audio_processing' not in config:
                    config['audio_processing'] = {
                        'silence_threshold': -40,
                        'min_silence_duration': 2000,
                        'chunk_size': 600,
                        'target_sample_rate': 16000,
                        'target_bitrate': '64k'
                    }
                
                return config
                
        except Exception as e:
            self.logger.warning(f"設定ファイル読み込みエラー: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """デフォルト設定を返す"""
        return {
            'usb_identifier': 'AUDIO_USB',
            'gdrive_folder_id': '',
            'pipeline': {
                'auto_process': True,
                'parallel_processing': False,
                'max_parallel_jobs': 2
            },
            'local_storage': {
                'base_dir': '~/AudioBackup',
                'max_storage_gb': 100,
                'retention_days': 30,
                'auto_cleanup': True,
                'verify_copy': True,
                'temp_dir': '/tmp/audio_processing',
                'processed_dir': 'processed_audio'
            },
            'audio_processing': {
                'silence_threshold': -40,
                'min_silence_duration': 2000,
                'chunk_size': 600,
                'target_sample_rate': 16000,
                'target_bitrate': '64k'
            }
        }
    
    def run_pipeline(self, usb_path: Optional[str] = None):
        """
        メインパイプラインを実行
        
        Args:
            usb_path: USBパス（省略時は自動検出）
        """
        try:
            self.is_running = True
            
            # セッション開始
            self.current_session = self.db.start_session("pipeline_v2")
            self.logger.info("=" * 60)
            self.logger.info("パイプライン実行開始 v2.0")
            self.logger.info("=" * 60)
            
            # ステップ1: USB検出
            if not usb_path:
                self.logger.info("ステップ1: USB検出中...")
                usb_path = self.usb_monitor.find_target_usb()
                if not usb_path:
                    self.logger.warning("対象のUSBが見つかりません")
                    return
            
            self.logger.info(f"USB検出: {usb_path}")
            
            # ステップ2: USBからローカルにコピー
            self.logger.info("ステップ2: USBからローカルストレージにコピー中...")
            copied_files = self.storage_manager.copy_from_usb(usb_path)
            
            if not copied_files:
                self.logger.info("新しいファイルはありません")
                return
            
            self.logger.info(f"コピー完了: {len(copied_files)} ファイル")
            
            # ステップ3: 音声処理
            if self.auto_process:
                self.logger.info("ステップ3: 音声処理中...")
                processed_files = self._process_audio_files(copied_files)
                self.logger.info(f"処理完了: {len(processed_files)} ファイル")
            else:
                # 処理をスキップして、既存の処理済みファイルを使用
                processed_files = self.storage_manager.get_pending_uploads()
            
            # ステップ4: Google Driveにアップロード
            if processed_files:
                self.logger.info("ステップ4: Google Driveにアップロード中...")
                upload_results = self._upload_to_gdrive(processed_files)
                
                # 結果サマリー
                successful = sum(1 for r in upload_results if r['success'])
                self.logger.info(f"アップロード完了: {successful}/{len(upload_results)} ファイル成功")
            
            # セッション終了
            self.db.end_session(self.current_session)
            self.logger.info("=" * 60)
            self.logger.info("パイプライン実行完了")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"パイプライン実行エラー: {e}", exc_info=True)
            if self.current_session:
                self.db.end_session(self.current_session, f"エラー: {e}")
        finally:
            self.is_running = False
            self.current_session = None
    
    def _process_audio_files(self, file_paths: List[str]) -> List[str]:
        """
        音声ファイルを処理
        
        Args:
            file_paths: 処理するファイルのパスリスト
        
        Returns:
            処理済みファイルのパスリスト
        """
        processed_files = []
        
        if self.parallel_processing:
            # 並列処理
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel_jobs) as executor:
                futures = []
                
                for file_path in file_paths:
                    future = executor.submit(self._process_single_file, file_path)
                    futures.append(future)
                
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        processed_files.append(result)
        else:
            # 逐次処理
            for file_path in file_paths:
                result = self._process_single_file(file_path)
                if result:
                    processed_files.append(result)
        
        return processed_files
    
    def _process_single_file(self, file_path: str) -> Optional[str]:
        """
        単一ファイルを処理
        
        Args:
            file_path: 処理するファイルのパス
        
        Returns:
            処理済みファイルのパス
        """
        try:
            self.logger.info(f"処理中: {Path(file_path).name}")
            
            # VAD分析（オプション）
            stats = self.audio_processor.extract_voice_activity(file_path)
            if stats:
                voice_ratio = stats['voice_ratio']
                self.logger.info(f"  音声検出率: {voice_ratio:.1f}%")
                
                # 音声が少なすぎる場合はスキップ
                if voice_ratio < 5:
                    self.logger.warning(f"  音声が少なすぎるためスキップ")
                    return None
            
            # 音声処理（無音除去・圧縮）
            processed_path = self.audio_processor.process_audio_file(file_path)
            
            if processed_path:
                # 処理済みディレクトリに移動
                self.storage_manager.move_to_processed(file_path, processed_path)
                
                # データベースに記録
                self._record_processing(file_path, processed_path, stats)
                
                return processed_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"ファイル処理エラー: {file_path} - {e}")
            return None
    
    def _upload_to_gdrive(self, file_paths: List[str]) -> List[Dict]:
        """
        Google Driveにアップロード
        
        Args:
            file_paths: アップロードするファイルのパスリスト
        
        Returns:
            アップロード結果のリスト
        """
        results = []
        
        # Google Drive接続確認
        if not self.gdrive_sync.authenticate():
            self.logger.error("Google Drive認証失敗")
            return results
        
        # 並列アップロード（既存の機能を使用）
        for file_path in file_paths:
            try:
                file_id = self.gdrive_sync.upload_file(file_path)
                if file_id:
                    results.append({
                        'file': file_path,
                        'success': True,
                        'file_id': file_id
                    })
                    self.logger.info(f"  アップロード成功: {Path(file_path).name}")
                else:
                    results.append({
                        'file': file_path,
                        'success': False,
                        'error': 'Upload failed'
                    })
                    
            except Exception as e:
                results.append({
                    'file': file_path,
                    'success': False,
                    'error': str(e)
                })
                self.logger.error(f"  アップロード失敗: {Path(file_path).name} - {e}")
        
        return results
    
    def _record_processing(self, original_path: str, processed_path: str, stats: Optional[Dict]):
        """処理結果をデータベースに記録"""
        try:
            # TODO: データベースに処理結果を記録
            pass
        except Exception as e:
            self.logger.error(f"記録エラー: {e}")
    
    def monitor_mode(self):
        """
        USBモニターモード（USB接続を監視して自動実行）
        """
        self.logger.info("USBモニターモード開始")
        self.logger.info("USBが接続されるのを待機中... (Ctrl+Cで終了)")
        
        def on_usb_connected(usb_path: str):
            self.logger.info(f"USB接続検出: {usb_path}")
            time.sleep(2)  # USBマウント完了待機
            self.run_pipeline(usb_path)
        
        self.usb_monitor.monitor(callback=on_usb_connected)
    
    def show_status(self):
        """現在のステータスを表示"""
        print("\n" + "=" * 60)
        print("音声同期パイプライン v2.0 ステータス")
        print("=" * 60)
        
        # ストレージ情報
        storage_info = self.storage_manager.get_storage_info()
        print("\n【ローカルストレージ】")
        print(f"  生データ: {storage_info.get('raw_size_gb', 0):.2f} GB")
        print(f"  処理済み: {storage_info.get('processed_size_gb', 0):.2f} GB")
        print(f"  アーカイブ: {storage_info.get('archive_size_gb', 0):.2f} GB")
        print(f"  合計使用量: {storage_info.get('total_size_gb', 0):.2f} / {storage_info.get('max_size_gb', 0):.0f} GB "
              f"({storage_info.get('usage_percent', 0):.1f}%)")
        
        # 未処理ファイル
        unprocessed = self.storage_manager.get_unprocessed_files()
        print(f"\n【処理待ちファイル】: {len(unprocessed)} 個")
        
        # アップロード待ち
        pending_uploads = self.storage_manager.get_pending_uploads()
        print(f"【アップロード待ちファイル】: {len(pending_uploads)} 個")
        
        # データベース統計
        stats = self.db.get_statistics()
        if stats:
            print("\n【同期統計】")
            print(f"  総ファイル数: {stats.get('total_files', 0)}")
            print(f"  総データ量: {stats.get('total_size_gb', 0):.2f} GB")
            print(f"  最終同期: {stats.get('last_sync', 'N/A')}")
        
        print("=" * 60 + "\n")


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(description="USB音声ファイル自動処理・同期システム v2.0")
    
    parser.add_argument('--config', default='config/settings.json',
                       help='設定ファイルのパス')
    parser.add_argument('--usb-path', help='USBのパスを指定（自動検出をスキップ）')
    parser.add_argument('--monitor', action='store_true',
                       help='USBモニターモードで起動')
    parser.add_argument('--status', action='store_true',
                       help='現在のステータスを表示')
    parser.add_argument('--process-only', action='store_true',
                       help='音声処理のみ実行（アップロードなし）')
    parser.add_argument('--upload-only', action='store_true',
                       help='アップロードのみ実行（処理なし）')
    parser.add_argument('--cleanup', action='store_true',
                       help='古いファイルをクリーンアップ')
    
    args = parser.parse_args()
    
    # パイプライン初期化
    pipeline = AudioSyncPipeline(args.config)
    
    try:
        if args.status:
            # ステータス表示
            pipeline.show_status()
            
        elif args.cleanup:
            # クリーンアップ実行
            pipeline.storage_manager.cleanup_old_files()
            print("クリーンアップ完了")
            
        elif args.process_only:
            # 音声処理のみ
            unprocessed = pipeline.storage_manager.get_unprocessed_files()
            if unprocessed:
                print(f"{len(unprocessed)} 個のファイルを処理中...")
                processed = pipeline._process_audio_files(unprocessed)
                print(f"処理完了: {len(processed)} ファイル")
            else:
                print("処理するファイルがありません")
                
        elif args.upload_only:
            # アップロードのみ
            pending = pipeline.storage_manager.get_pending_uploads()
            if pending:
                print(f"{len(pending)} 個のファイルをアップロード中...")
                results = pipeline._upload_to_gdrive(pending)
                successful = sum(1 for r in results if r['success'])
                print(f"アップロード完了: {successful}/{len(results)} ファイル成功")
            else:
                print("アップロードするファイルがありません")
                
        elif args.monitor:
            # USBモニターモード
            pipeline.monitor_mode()
            
        else:
            # 通常実行
            pipeline.run_pipeline(args.usb_path)
            
    except KeyboardInterrupt:
        print("\n\n処理を中断しました")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
